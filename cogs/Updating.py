import discord
from discord.ext import commands

import mmrTables
import API.post, API.get

import dateutil.parser

from constants import (get_table_embed, place_MMRs, place_scores, channels, getRank, ranks, placementRoleID, 
nameChangeLog, nameRequestLog, player_role_ID, strike_log_channel, is_player_in_table, name_request_channel)

from custom_checks import check_staff_roles, command_check_reporter_roles, command_check_staff_roles, check_name_restricted_roles, check_valid_name

from typing import Union

import asyncio
import traceback

def findmember(ctx, name, roleid):
    members = ctx.guild.members
    role = ctx.guild.get_role(roleid)
    def pred(m):
        if m.nick is not None:
            if m.nick.lower() == name.lower():
                return True
            return False
        if m.name.lower() != name.lower():
            return False
        if role not in m.roles:
            return False
        return True
    return discord.utils.find(pred, members)

def parseMultipliers(args):
    multArgs = args.split(",")
    multipliers = {}
    for mult in multArgs:
        splitMult = mult.split()
        if len(splitMult) >= 2:
            playerName = " ".join(splitMult[0:len(splitMult)-1]).strip()
            playerMult = splitMult[len(splitMult)-1].strip()
            try:
                if float(playerMult) < 0.0 or float(playerMult) > 2.0:
                    errMsg = "%s is not a valid multiplier!" % playerMult
                    return False, errMsg
                multipliers[playerName] = float(playerMult)
            except Exception as e:
                errMsg = "%s is not a valid multiplier!" % playerMult
                return False, errMsg
    return True, multipliers

def parseScores(args):
    playerScores = args.split(",")
    scores = {}
    for score in playerScores:
        splitScore = score.split()
        if len(splitScore) >= 2:
            playerName = " ".join(splitScore[0:len(splitScore)-1]).strip()
            playerScore = splitScore[len(splitScore)-1].strip()
            try:
                if int(playerScore) < 12 or int(playerScore) > 180:
                    errMsg = "%s is not a valid score!" % playerScore
                    return False, errMsg
                scores[playerName] = int(playerScore)
            except Exception as e:
                errMsg = "%s is not a valid score!" % playerScore
                return False, errMsg
    return True, scores

class Updating(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def updateRoles(self, ctx, name, oldMMR:int, newMMR:int):
        oldRank = getRank(oldMMR)
        newRank = getRank(newMMR)
        rankChanges = ""
        if oldRank != newRank:
            member = findmember(ctx, name, ranks[oldRank]["roleid"])
            if member is not None:
                memName = member.mention
            else:
                memName = name
            rankChanges = ("%s -> %s\n"
                            % (memName, ranks[newRank]["emoji"]))
            oldRole = ctx.guild.get_role(ranks[oldRank]["roleid"])
            newRole = ctx.guild.get_role(ranks[newRank]["roleid"])
            if member is not None and oldRole is not None and newRole is not None:
                if oldRole in member.roles:
                    await member.remove_roles(oldRole)
                if newRole not in member.roles:
                    await member.add_roles(newRole)
        return rankChanges

    async def givePlacementRole(self, ctx, player, placeMMR):
        oldRoleID = placementRoleID
        newRoleID = ranks[getRank(placeMMR)]["roleid"]
        oldRole = ctx.guild.get_role(oldRoleID)
        newRole = ctx.guild.get_role(newRoleID)
        #member = findmember(ctx, name, oldRole)
        if 'discordId' not in player.keys():
            await ctx.send("Player does not have a discord ID on the site, please give them one to give them placement roles")
            return
        member = ctx.guild.get_member(int(player['discordId']))
        if member is None:
            await ctx.send(f"Couldn't find member {player['name']}, please give them roles manually")
            return
        if oldRole in member.roles:
            await member.remove_roles(oldRole)
        if newRole not in member.roles:
            await member.add_roles(newRole)
        await ctx.send(f"Managed to find member {member.display_name} and edit their roles")
            
        

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['add'])
    async def addPlayer(self, ctx, mkcid:int, member:discord.Member, *, name):
        if len(name) > 16 or len(name) < 2:
            await ctx.send("Names must be between 2-16 characters! Please tell the player to choose a different name")
            return
        if name.startswith("_") or name.endswith("_"):
            await ctx.send("Nicknames cannot start or end with `_` (underscore)")
            return
        content = "Please confirm the player details within 30 seconds"
        e = discord.Embed(title="New Player")
        e.add_field(name="Name", value=name)
        e.add_field(name="MKC ID", value=mkcid)
        e.add_field(name="Discord", value=member.mention)
        embedded = await ctx.send(content=content, embed=e)
        CHECK_BOX = "\U00002611"
        X_MARK = "\U0000274C"
        await embedded.add_reaction(CHECK_BOX)
        await embedded.add_reaction(X_MARK)

        def check(reaction, user):
            if user != ctx.author:
                return False
            if reaction.message != embedded:
                return False
            if str(reaction.emoji) == X_MARK:
                return True
            if str(reaction.emoji) == CHECK_BOX:
                return True
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except:
            await embedded.delete()
            return
        if str(reaction.emoji) == X_MARK:
            await embedded.delete()
            return
        
        success, player = await API.post.createNewPlayer(mkcid, name, member.id)
        await embedded.delete()
        if success is False:
            await ctx.send("An error occurred while trying to add the player: %s"
                           % player)
            return
        url = ctx.bot.site_creds["website_url"] + "/PlayerDetails/%d" % int(player["id"])
        placementRole = ctx.guild.get_role(placementRoleID)
        player_role = ctx.guild.get_role(player_role_ID)
        roleGiven = ""
        try:
            await member.add_roles(*[placementRole, player_role])
            if member.display_name != name:
                await member.edit(nick=name)
            roleGiven += f"\nAlso gave {member.mention} placement role"
        except Exception as e:
            roleGiven += f"\nCould not give placement role to the player due to the following: {e}"
            pass
        await ctx.send(f"Successfully added the new player: {url}{roleGiven}")

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['apl'])
    async def addAndPlace(self, ctx, mkcid:int, mmr:int, member:discord.Member, *, name):
        if len(name) > 16:
            await ctx.send("Names can only be up to 16 characters! Please tell the player to choose a different name")
            return
        if name.startswith("_") or name.endswith("_"):
            await ctx.send("Nicknames cannot start or end with `_` (underscore)")
            return
        content = "Please confirm the player details within 30 seconds"
        e = discord.Embed(title="New Player")
        e.add_field(name="Name", value=name)
        e.add_field(name="MKC ID", value=mkcid)
        e.add_field(name="Placement MMR", value=mmr)
        e.add_field(name="Discord", value=member.mention)
        embedded = await ctx.send(content=content, embed=e)
        CHECK_BOX = "\U00002611"
        X_MARK = "\U0000274C"
        await embedded.add_reaction(CHECK_BOX)
        await embedded.add_reaction(X_MARK)

        def check(reaction, user):
            if user != ctx.author:
                return False
            if reaction.message != embedded:
                return False
            if str(reaction.emoji) == X_MARK:
                return True
            if str(reaction.emoji) == CHECK_BOX:
                return True
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except:
            await embedded.delete()
            return
        if str(reaction.emoji) == X_MARK:
            await embedded.delete()
            return
        
        success, player = await API.post.createPlayerWithMMR(mkcid, mmr, name, member.id)
        rank = getRank(mmr)
        rank_role_id = ranks[rank]["roleid"]
        rank_role = ctx.guild.get_role(rank_role_id)
        player_role = ctx.guild.get_role(player_role_ID)
        roleGiven = ""
        try:
            await member.add_roles(*[rank_role, player_role])
            if member.display_name != name:
                await member.edit(nick=name)
            roleGiven += f"\nAlso gave {member.mention} {rank} role"
        except Exception as e:
            roleGiven += f"\nCould not give {rank} role to the player due to the following: {e}"
            pass
        await embedded.delete()
        if success is False:
            await ctx.send("An error occurred while trying to add the player: %s"
                           % player)
            return
        url = ctx.bot.site_creds["website_url"] + "/PlayerDetails/%d" % int(player["id"])
        await ctx.send(f"Successfully added the new player: {url}{roleGiven}")

    @commands.command(aliases=['rn'])
    @commands.guild_only()
    async def requestName(self, ctx, *, name):
        if check_name_restricted_roles(ctx, ctx.author):
            await ctx.send("You are nickname restricted and cannot use this command")
            return
        if ctx.channel.id != name_request_channel:
            await ctx.send(f"You may only use this command in <#{name_request_channel}>")
            return
        if not await check_valid_name(ctx, name):
            return
        player = await API.get.getPlayerFromDiscord(ctx.author.id)
        if player is None:
            await ctx.send("Your Discord ID is not linked to a Lounge profile, please make a support ticket for help.")
            return
        content = "Please confirm the name change within 30 seconds to make a name change request"
        e = discord.Embed(title="Name Change")
        e.add_field(name="Current Name", value=player['name'], inline=False)
        e.add_field(name="New Name", value=name, inline=False)
        embedded = await ctx.send(content=content, embed=e)
        CHECK_BOX = "\U00002611"
        X_MARK = "\U0000274C"
        await embedded.add_reaction(CHECK_BOX)
        await embedded.add_reaction(X_MARK)

        def check(reaction, user):
            if user != ctx.author:
                return False
            if reaction.message != embedded:
                return False
            if str(reaction.emoji) == X_MARK:
                return True
            if str(reaction.emoji) == CHECK_BOX:
                return True
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except:
            await embedded.delete()
            return
        if str(reaction.emoji) == X_MARK:
            await embedded.delete()
            return
        success, request = await API.post.requestNameChange(player['name'], name)
        await embedded.delete()
        if success is False:
            await ctx.send(request)
            return
        await ctx.send("Your name change request has been sent to staff for approval. Please wait, you will receive a DM when this request is accepted or denied (if you have server member DMs enabled).")
        log_channel = ctx.guild.get_channel(nameRequestLog)
        e = discord.Embed(title="New Name Change Request")
        e.add_field(name="Current Name", value=player['name'], inline=False)
        e.add_field(name="New Name", value=name, inline=False)
        log_msg = await log_channel.send(embed=e)
        await API.post.setNameChangeMessageId(player['name'], log_msg.id)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['an'])
    async def approveName(self, ctx, *, old_name):
        success, name_request = await API.post.acceptNameChange(old_name)
        if success is False:
            await ctx.send(name_request)
            return
        await ctx.send(f"Approved the name change: {name_request['name']} -> {name_request['newName']}")
        e = discord.Embed(title="Name change request approved")
        e.add_field(name="Current Name", value=name_request['name'])
        e.add_field(name="New Name", value=name_request["newName"], inline=False)
        e.add_field(name="Approved by", value=ctx.author.mention, inline=False)
        name_change_log = ctx.guild.get_channel(nameChangeLog)
        await name_change_log.send(embed=e)
        name_request_log = ctx.guild.get_channel(nameRequestLog)
        react_msg = await name_request_log.fetch_message(name_request['messageId'])
        if react_msg is not None:
            CHECK_BOX = "\U00002611"
            await react_msg.add_reaction(CHECK_BOX)
        member = await ctx.guild.fetch_member(name_request['discordId'])
        if member is None:
            await ctx.send(f"Couldn't find member in server, please change their nickname manually")
            return
        if member is not None:
            try:
                await member.send(f"Your name change request from {name_request['name']} to {name_request['newName']} has been approved.")
            except Exception as e:
                pass
            try:
                await member.edit(nick=name_request['newName'])
            except Exception as e:
                pass

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['pn'])
    async def pendingNames(self, ctx):
        changes = await API.get.getPendingNameChanges()
        if changes is False:
            await ctx.send("An error occurred when getting the name changes. Please try again later.")
            return
        if len(changes['players']) == 0:
            await ctx.send("There are no pending name changes")
            return
        msg = "**Pending name changes**\n```"
        for change in changes["players"]:
            msg += f"{change['name']} -> {change['newName']}\n"
        msg += "```"
        await ctx.send(msg)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['ana'])
    async def approveNamesAll(self, ctx):
        changes = await API.get.getPendingNameChanges()
        if changes is False:
            await ctx.send("An error occurred when getting the name changes. Please try again later.")
            return
        if len(changes['players']) == 0:
            await ctx.send("There are no pending name changes")
            return
        for change in changes['players']:
            await self.approveName(ctx, old_name=change['name'])
        await ctx.send("Approved all name changes")


    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['rjn'])
    async def rejectName(self, ctx, *, args):
        splitArgs = args.split(";")
        name = splitArgs[0].strip()
        reason = ""
        if len(splitArgs) > 1:
            reason = ";".join(splitArgs[1:]).strip()
        success, name_request = await API.post.rejectNameChange(name)
        if success is False:
            await ctx.send(name_request)
            return
        await ctx.send("Rejected the name change")
        name_request_log = ctx.guild.get_channel(nameRequestLog)
        react_msg = await name_request_log.fetch_message(name_request['messageId'])
        if react_msg is not None:
            X_MARK = "\U0000274C"
            await react_msg.add_reaction(X_MARK)
        e = discord.Embed(title="Name change request denied")
        e.add_field(name="Current Name", value=name_request['name'], inline=False)
        e.add_field(name="Requested Name", value=name_request['newName'], inline=False)
        e.add_field(name="Denied by", value=ctx.author.mention)
        if len(reason) > 0:
            e.add_field(name="Reason", value=reason, inline=False)
        await name_request_log.send(embed=e)
        member = await ctx.guild.fetch_member(name_request['discordId'])
        if member is None:
            return
        if member is not None:
            try:
                await member.send(f"Your name change request from {name_request['name']} to {name_request['newName']} has been denied. Reason: {reason}")
            except Exception as e:
                pass

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['un'])
    async def updateName(self, ctx, *, args):
        names = args.split(",")
        if len(names) != 2:
            await ctx.send("Please send 2 names separated by commas: ex. `!updateName Old Name, New Name`")
            return
        oldName = names[0].strip()
        newName = names[1].strip()
        if len(newName) > 16:
            await ctx.send("Names can only be up to 16 characters! Please tell the player to choose a different name")
            return
        if newName.startswith("_") or newName.endswith("_"):
            await ctx.send("Nicknames cannot start or end with `_` (underscore)")
            return

        player = await API.get.getPlayer(oldName)
        if player is None:
            await ctx.send("Player with old name can't be found")
            return
        if 'discordId' in player.keys():
            try:
                member = await ctx.guild.fetch_member(player['discordId'])
            except Exception as e:
                member = None
            if member is not None:
                is_name_restricted = check_name_restricted_roles(ctx, member)
                if is_name_restricted:
                    await ctx.send("This player is name restricted, so they can't change their name.")
                    return
            

        content = "Please confirm the name change within 30 seconds to change the name"
        e = discord.Embed(title="Name Change")
        e.add_field(name="Current Name", value=oldName, inline=False)
        e.add_field(name="New Name", value=newName, inline=False)
        embedded = await ctx.send(content=content, embed=e)
        CHECK_BOX = "\U00002611"
        X_MARK = "\U0000274C"
        await embedded.add_reaction(CHECK_BOX)
        await embedded.add_reaction(X_MARK)

        def check(reaction, user):
            if user != ctx.author:
                return False
            if reaction.message != embedded:
                return False
            if str(reaction.emoji) == X_MARK:
                return True
            if str(reaction.emoji) == CHECK_BOX:
                return True
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except:
            await embedded.delete()
            return

        if str(reaction.emoji) == X_MARK:
            await embedded.delete()
            return

        success = await API.post.updatePlayerName(oldName, newName)
        await embedded.delete()
        if success is not True:
            await ctx.send("An error occurred trying to change the name:\n%s" % success)
            return
        await ctx.send("Name change successful: %s -> %s" % (oldName, newName))
        channel = ctx.guild.get_channel(nameChangeLog)
        await channel.send(f"{oldName} -> {newName}")
        
        if 'discordId' not in player.keys():
            await ctx.send("Player does not have a discord ID on the site, please update their nickname manually")
            return
        member = ctx.guild.get_member(int(player['discordId']))
        if member is None:
            await ctx.send(f"Couldn't find member {player['name']}, please change their nickname manually")
            return
        await member.edit(nick=newName)
        await ctx.send("Successfully changed their nickname in server")
        
    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['um'])
    async def updateMKC(self, ctx, newID:int, *, name):
        content = "Please confirm the MKC ID change within 30 seconds"
        e = discord.Embed(title="MKC ID Change")
        e.add_field(name="Name", value=name)
        e.add_field(name="New MKC ID", value=newID)
        embedded = await ctx.send(content=content, embed=e)
        CHECK_BOX = "\U00002611"
        X_MARK = "\U0000274C"
        await embedded.add_reaction(CHECK_BOX)
        await embedded.add_reaction(X_MARK)

        def check(reaction, user):
            if user != ctx.author:
                return False
            if reaction.message != embedded:
                return False
            if str(reaction.emoji) == X_MARK:
                return True
            if str(reaction.emoji) == CHECK_BOX:
                return True
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except:
            await embedded.delete()
            return
        if str(reaction.emoji) == X_MARK:
            await embedded.delete()
            return

        success = await API.post.updateMKCid(name, newID)
        await embedded.delete()
        if success is not True:
            await ctx.send("An error occurred trying to change the MKC ID:\n%s" % success)
            return
        await ctx.send("MKC ID change successful")

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['ud'])
    async def updateDiscord(self, ctx, member:Union[discord.Member, int], *, name):
        if isinstance(member, discord.Member):
            member = member.id
        success, response = await API.post.updateDiscord(name, member)
        if success is False:
            await ctx.send(f"An error occurred: {response}")
            return
        #print(response)
        await ctx.send("Discord ID change successful")
        
    @commands.check(command_check_staff_roles)
    @commands.command()
    async def place(self, ctx, rank, *, name):
        if rank.lower() not in place_MMRs.keys():
            await ctx.send("Please enter one of the following ranks: %s"
                           % (", ".join(place_MMRs.keys())))
            return False
        placeMMR = place_MMRs[rank.lower()]
        #newRole = ranks[getRank(placeMMR)]["roleid"]
        success, player = await API.post.placePlayer(placeMMR, name)
        if success is False:
            await ctx.send("An error occurred while trying to place the player: %s"
                           % player)
            return False
        await self.givePlacementRole(ctx, player, placeMMR)
        await ctx.send("Successfully placed %s in %s with %d MMR"
                       % (player["name"], rank.lower(), placeMMR))
        return True

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def placeMMR(self, ctx, mmr:int, *, name):
        success, p = await API.post.placePlayer(mmr, name)
        if success is False:
            await ctx.send("An error occurred while trying to place the player: %s"
                           % player)
            return False
        player = await API.get.getPlayer(name)
        await self.givePlacementRole(ctx, p, mmr)
        await ctx.send("Successfully placed %s with %d MMR"
                       % (player["name"], mmr))
        return True

    async def auto_place(self, ctx, name, score:int):
        #rank = "iron"
        if score >= 130:
            mmr = 4500
        elif score >= 115:
            mmr = 3500
        elif score >= 100:
            mmr = 2500
        else:
            mmr = 1500
        #for p_score in sorted(place_scores.keys(), reverse=True):
        #    if score >= p_score:
        #        rank = place_scores[p_score]
        result = await self.placeMMR(ctx, mmr, name=name)
        return result

    async def check_placements(self, ctx, table):
        for team in table["teams"]:
            for p in team["scores"]:
                if "prevMmr" not in p.keys():
                    await self.auto_place(ctx, p["playerName"], p["score"])

    #@commands.check(command_check_staff_roles)
    @commands.has_any_role("Administrator")
    @commands.command()
    async def forcePlace(self, ctx, mmr:int, *, name):
        success, p = await API.post.forcePlace(mmr, name)
        if success is False:
            await ctx.send("An error occurred while trying to place the player: %s"
                           % p)
            return
        player = await API.get.getPlayer(name)
        await self.givePlacementRole(ctx, player, mmr)
        await ctx.send("Successfully placed %s with %d MMR"
                       % (player["name"], mmr))

    @commands.command(aliases=['mkc'])
    async def mkcPlayer(self, ctx, mkcid:int):
        player = await API.get.getPlayerFromMKC(mkcid)
        if player is None:
            await ctx.send("The player couldn't be found!")
            return
        #print(player)
        playerURL = ctx.bot.site_creds['website_url'] + '/PlayerDetails/%d' % player['id']
        mkcURL = "https://www.mariokartcentral.com/forums/index.php?members/%d/" % player['mkcId']
        mkcField = "[%d](%s)" % (player['mkcId'], mkcURL)
        e = discord.Embed(title="Player Data", url=playerURL, description=player['name'])
        e.add_field(name="MKC ID", value=mkcField)
        await ctx.send(embed=e)

    @commands.command(aliases=['discord'])
    async def discordPlayer(self, ctx, member:Union[discord.Member, int]):
        if isinstance(member, discord.Member):
            member = member.id
        player = await API.get.getPlayerFromDiscord(member)
        if player is None:
            await ctx.send("The player couldn't be found!")
            return
        playerURL = ctx.bot.site_creds['website_url'] + '/PlayerDetails/%d' % player['id']
        mkcURL = "https://www.mariokartcentral.com/forums/index.php?members/%d/" % player['mkcId']
        mkcField = "[%d](%s)" % (player['mkcId'], mkcURL)
        e = discord.Embed(title="Player Data", url=playerURL, description=player['name'])
        e.add_field(name="MKC ID", value=mkcField)
        await ctx.send(embed=e)

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def addAllDiscords(self, ctx):
        players = await API.get.getPlayerList()
        for player in players['players']:
            if "discordId" not in player.keys():
                if 'mmr' not in player.keys():
                    continue
                rank = getRank(player['mmr'])
                role = ranks[rank]['roleid']
                member = findmember(ctx, player['name'], role)
                if member is None:
                    print(f"could not find member with name {player['name']} and rank {rank}")
                    continue
                success, txt = await API.post.updateDiscord(player['name'], member.id)
                if success is True:
                    print(f"Added discord id for {player['name']}: {member.id}")

    async def pen_channel(self, ctx, name, tier, reason, amount, channel, is_anonymous, is_strike):
        success, pen = await API.post.createPenalty(name, abs(amount), is_strike)
        if success is False:
            await ctx.send(f"An error occurred while penalizing {name}:\n{pen}")
            return
        #print(pen)
        penaltyID = pen["id"]
        embed_title = "Penalty added"
        if is_strike:
            embed_title = "Penalty + strike added"
        e = discord.Embed(title=embed_title)
        e.add_field(name="Player", value=pen["playerName"], inline=False)
        e.add_field(name="Amount", value="-%d" % abs(amount))
        e.add_field(name="ID", value=penaltyID)
        e.add_field(name="Tier", value=tier.upper())
        if is_anonymous is False:
            e.add_field(name="Given by", value=ctx.author.mention)
        if reason != "":
            e.add_field(name="Reason", value=reason, inline=False)
        if is_strike:
            recentStrikes = await API.get.getStrikes(name)
            if recentStrikes is not False:
                last3 = recentStrikes[::-1][0:3]
                strikeStr = ""
                if len(last3) > 0:
                    for pen in last3:
                        strikeDate = dateutil.parser.isoparse(pen["awardedOn"]).strftime('%m/%d/%Y')
                        strikeStr += f"{strikeDate}\n"
                    e.add_field(name="Strikes", value=strikeStr, inline=False)
        rankChange = await self.updateRoles(ctx, pen["playerName"], pen["prevMmr"], pen["newMmr"])
        pen_msg = await channel.send(embed=e, content=rankChange)
        rank = getRank(pen["newMmr"])
        member = findmember(ctx, pen["playerName"], ranks[rank]["roleid"])
        if member is not None:
            try:
                if is_anonymous is False:
                    # change from mention to name because we are in DMs
                    e.set_field_at(4, name='Given by', value=ctx.author.display_name)
                if is_strike:
                    dm_content = "You received a strike in 150cc Lounge:"
                else:
                    dm_content = "You received a penalty in 150cc Lounge:"
                await member.send(embed=e, content=dm_content)
            except Exception as ex:
                pass
        strike_log = ctx.guild.get_channel(strike_log_channel)
        if strike_log is not None:
            if is_anonymous is True:
                e.add_field(name="Given by", value=ctx.author.mention)
            else:
                e.set_field_at(4, name='Given by', value=ctx.author.mention)
            await strike_log.send(embed=e, content=rankChange)
        if ctx.channel.id == channel.id:
            await ctx.message.delete()
        else:
            await ctx.send(f"Added -{abs(amount)} penalty to {pen['playerName']} in {pen_msg.jump_url}")

    async def add_penalty(self, ctx, amount:int, tier, args, is_anonymous=False, is_strike=False):
        splitArgs = args.split(";")
        names = [s.strip() for s in splitArgs[0].split(",")]
        if len(set(names)) < len(names):
            await ctx.send("There is at least one duplicate name in your input, try again")
            return
        reason = ""
        if len(splitArgs) > 1:
            reason = splitArgs[1].strip()
        if tier.upper() not in channels.keys():
            await ctx.send(f"Your tier is not valid! Valid tiers are: {list(channels.keys())}")
            return
        if abs(amount) > 200:
            await ctx.send("Individual penalties can only be 200 points or lower")
            return
        channel = ctx.guild.get_channel(channels[tier.upper()])
        for name in names:
            if name.isdigit():
                player = await API.get.getPlayerFromDiscord(name)
                if player is None:
                    await ctx.send(f"The following player could not be found: {name}")
                    return
                name = player["name"]
            await self.pen_channel(ctx, name, tier, reason, amount, channel, is_anonymous, is_strike)
        
    # async def add_strike(self, ctx, amount:int, tier, args, is_anonymous=False):
    #     splitArgs = args.split(";")
    #     name = splitArgs[0].strip()
    #     reason = ""
    #     if len(splitArgs) > 1:
    #         reason = splitArgs[1].strip()
    #     if tier.upper() not in channels.keys():
    #         await ctx.send("Your tier is not valid! Valid tiers are: %s"
    #                        % list(channels.keys()))
    #         return
    #     if abs(amount) > 200:
    #         await ctx.send("Individual penalties can only be 200 points or lower")
    #         return
    #     channel = ctx.guild.get_channel(channels[tier.upper()])
    #     success, pen = await API.post.createPenalty(name, abs(amount), True)
    #     if success is False:
    #         await ctx.send("An error occurred while giving the penalty:\n%s"
    #                        % pen)
    #         return
    #     penaltyID = pen["id"]
    #     e = discord.Embed(title="Penalty + strike added")
    #     e.add_field(name="Player", value=pen["playerName"], inline=False)
    #     e.add_field(name="Amount", value="-%d" % abs(amount), inline=False)
    #     e.add_field(name="ID", value=penaltyID)
    #     e.add_field(name="Tier", value=tier.upper())
    #     if is_anonymous is False:
    #         e.add_field(name="Given by", value=ctx.author.mention)
    #     if reason != "":
    #         e.add_field(name="Reason", value=reason, inline=False)
    #     recentStrikes = await API.get.getStrikes(name)
    #     if recentStrikes is not False:
    #         last3 = recentStrikes[::-1][0:3]
    #         strikeStr = ""
    #         if len(last3) > 0:
    #             for pen in last3:
    #                 strikeDate = dateutil.parser.isoparse(pen["awardedOn"]).strftime('%m/%d/%Y')
    #                 strikeStr += "%s\n" % strikeDate
    #             e.add_field(name="Strikes", value=strikeStr, inline=False)
    #     rankChange = await self.updateRoles(ctx, pen["playerName"], pen["prevMmr"], pen["newMmr"])
    #     await channel.send(embed=e, content=rankChange)
    #     rank = getRank(pen["newMmr"])
    #     member = findmember(ctx, pen["playerName"], ranks[rank]["roleid"])
    #     if member is not None:
    #         try:
    #             if is_anonymous is False:
    #                 # change from mention to name because we are in DMs
    #                 e.set_field_at(4, name='Given by', value=ctx.author.display_name)
    #             await member.send(embed=e, content="You received a strike in 150cc Lounge:")
    #         except Exception as e:
    #             pass
    #     strike_log = ctx.guild.get_channel(strike_log_channel)
    #     if strike_log is not None:
    #         if is_anonymous is True:
    #             e.add_field(name="Given by", value=ctx.author.mention)
    #         else:
    #             e.set_field_at(4, name='Given by', value=ctx.author.mention)
    #         await strike_log.send(embed=e, content=rankChange)
    #     if ctx.channel.id == channel.id:
    #         await ctx.message.delete()
    #     else:
    #         await ctx.send("Added -%d penalty to %s in %s"
    #                        % (abs(amount), pen["playerName"], channel.mention))
        

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['pen'])
    async def penalty(self, ctx, amount:int, tier, *, args):
        await self.add_penalty(ctx, amount, tier, args)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['apen', 'apenalty'])
    async def anonymousPenalty(self, ctx, amount:int, tier, *, args):
        await self.add_penalty(ctx, amount, tier, args, is_anonymous=True)

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def deletePenalty(self, ctx, penID:int):
        success = await API.post.deletePenalty(penID)
        if success is True:
            await ctx.send("Successfully deleted penalty ID %d" % penID)
        else:
            await ctx.send(success)
        
    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['str']) 
    async def strike(self, ctx, amount:int, tier, *, args):
        #await self.add_strike(ctx, amount, tier, args)
        await self.add_penalty(ctx, amount, tier, args, is_strike=True)
        
    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['astr', 'astrike']) 
    async def anonymousStrike(self, ctx, amount:int, tier, *, args):
        await self.add_penalty(ctx, amount, tier, args, is_anonymous=True, is_strike=True)

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def bonus(self, ctx, amount:int, *, name):
        absAmount = abs(amount)
        success, addedBonus = await API.post.createBonus(name, absAmount)
        if success is False:
            await ctx.send("An error occurred while giving the bonus:\n%s"
                           % addedBonus)
            return
        rankChange = await self.updateRoles(ctx, addedBonus["playerName"], addedBonus["prevMmr"], addedBonus["newMmr"])
        await ctx.send(f"Successfully added {absAmount} MMR bonus to {name}\n{rankChange}")
        

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def pending(self, ctx):
        tables = await API.get.getPending()
        if len(tables) == 0:
            await ctx.send("There are no pending tables")
            return
        msg = ""
        for tier in channels.keys():
            count = 0
            ids = []
            for table in tables:
                if table["tier"] == tier:
                    ids.append(table["id"])
                    count += 1
            if count > 0:
                tier_msg = f"\n<#{channels[tier]}> - {count} tables\n"
                tier_msg += "\n".join(["\tID %d" % tableid for tableid in ids])
                if len(tier_msg) + len(tier_msg) > 2000:
                    await ctx.send(msg)
                    msg = tier_msg
        if len(msg) > 0:
            await ctx.send(msg)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['ua'])
    async def updateAll(self, ctx):
        tables = await API.get.getPending()
        if tables is False:
            await ctx.send("There are no pending tables")
            return
        for table in tables:
            try:
                success = await self.update(ctx, table["id"])
                if success is False:
                    return
            except Exception as e:
                #print(e)
                traceback.print_exc()
        await ctx.send("Updated all tables")

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['ut'])
    async def updateTier(self, ctx, tier):
        if tier.upper() not in channels.keys():
            await ctx.send("Invalid tier")
            return
        tables = await API.get.getPending()
        if tables is False:
            await ctx.send("There are no pending tables")
            return
        for table in tables:
            try:
                if tier.upper() != table["tier"]:
                    continue
                success = await self.update(ctx, table["id"])
                if success is False:
                    return
            except Exception as e:
                traceback.print_exc()
        await ctx.send(f'Updated all tables in tier {tier.upper()}')

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['uu'])
    async def updateUntil(self, ctx, tid:int):
        tables = await API.get.getPending()
        if tables is False:
            await ctx.send("There are no pending tables")
            return
        for table in tables:
            if table["id"] > tid:
                continue
            try:
                success = await self.update(ctx, table["id"])
                if success is False:
                    return
            except Exception as e:
                traceback.print_exc()
        await ctx.send(f'Updated all tables up to ID {tid}')

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['utu'])
    async def updateTierUntil(self, ctx, tier, tid:int):
        if tier.upper() not in channels.keys():
            await ctx.send("Invalid tier")
            return
        tables = await API.get.getPending()
        if tables is False:
            await ctx.send("There are no pending tables")
            return
        for table in tables:
            if table["id"] > tid:
                continue
            try:
                if tier.upper() != table["tier"]:
                    continue
                success = await self.update(ctx, table["id"])
                if success is False:
                    return
            except Exception as e:
                traceback.print_exc()
        await ctx.send(f'Updated all tables up to ID {tid} in tier {tier.upper()}')

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['setml'])
    async def setMultipliers(self, ctx, tableid:int, *, extraArgs=""):
        table = await API.get.getTable(tableid)
        if table is False:
            await ctx.send("Table couldn't be found")
            return
        workmsg = await ctx.send("Working...")
        success, multipliers = parseMultipliers(extraArgs)
        if success is False:
            await ctx.send(multipliers)
            return False
        if success is True and multipliers != {}:
            updatedMultipliers = await API.post.setMultipliers(tableid, multipliers)
            if updatedMultipliers is not True:
                await ctx.send("Error setting multipliers:\n%s"
                               % updatedMultipliers)
                return False
        await ctx.send("Successfully set multipliers for table")
            
    @commands.check(command_check_staff_roles)
    @commands.command()
    async def hide(self, ctx, *, name):
        success, text = await API.post.hidePlayer(name)
        if success is False:
            await ctx.send(f"An error occurred: {text}")
            return
        await ctx.send("Successfully hid player")
    
    @commands.check(command_check_staff_roles)
    @commands.command()
    async def unhide(self, ctx, *, name):
        success, text = await API.post.unhidePlayer(name)
        if success is False:
            await ctx.send(f"An error occurred: {text}")
            return
        await ctx.send("Successfully unhid player")

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def refresh(self, ctx, *, name):
        if name.isdigit():
            player = await API.get.getPlayerFromDiscord(name)
            if player is None:
                await ctx.send("Player could not be found!")
                return
            name = player["name"]
        success, text = await API.post.refreshPlayerData(name)
        if success is False:
            await ctx.send(f"An error occurred: {text}")
            return
        await ctx.send("Successfully refreshed player data")

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['u'])
    async def update(self, ctx, tableid:int, *, extraArgs=""):
        table = await API.get.getTable(tableid)
        if table is False:
            await ctx.send("Table couldn't be found")
            return
        workmsg = await ctx.send("Working...")
        success, multipliers = parseMultipliers(extraArgs)
        if success is False:
            await ctx.send(multipliers)
            return False
        if success is True and multipliers != {}:
            updatedMultipliers = await API.post.setMultipliers(tableid, multipliers)
            if updatedMultipliers is not True:
                await ctx.send("Error setting multipliers:\n%s"
                               % updatedMultipliers)
                return False
        
        await self.check_placements(ctx, table)
        
        success, table = await API.post.verifyTable(tableid)
        if success is False:
            await ctx.send(table)
            return False
        
        sizes = {'FFA': 1, '2v2': 2, '3v3': 3, '4v4': 4, '6v6': 6}
        size = sizes[table['format']]
        tier = table['tier']
        tid = table['id']
        if 'tableMessageId' in table.keys():
            tableMsg = int(table['tableMessageId'])
        else:
            tableMsg = None
        placements = []
        names = []
        oldMMRs = []
        newMMRs = []
        peakMMRs = []
        scores = []
        discordids = []
        channel = ctx.guild.get_channel(channels[tier.upper()])
        for team in table['teams']:
            placements.append(team['rank'])
            team['scores'].sort(key=lambda p: p['score'], reverse=True)
            for player in team['scores']:
                names.append(player['playerName'])
                oldMMRs.append(player['prevMmr'])
                newMMRs.append(player['newMmr'])
                scores.append(player['score'])
                peakMMRs.append(player['isNewPeakMmr'])
                if 'playerDiscordId' not in player.keys():
                    discordids.append(None)
                else:
                    discordids.append(player['playerDiscordId'])
        mmrTable = mmrTables.createMMRTable(size, tier, placements, names, scores, oldMMRs, newMMRs, tid, peakMMRs)

        rankChanges = ""
        for i in range(len(names)):
            oldRank = getRank(oldMMRs[i])
            newRank = getRank(newMMRs[i])
            if discordids[i] is None:
                member = findmember(ctx, names[i], ranks[oldRank]["roleid"])
                if member is not None:
                    await API.post.updateDiscord(names[i], member.id)
            if oldRank != newRank:
                if discordids[i] is None:
                    member = findmember(ctx, names[i], ranks[oldRank]["roleid"])
                else:
                    member = ctx.guild.get_member(int(discordids[i]))
                if member is not None:
                    memName = member.mention
                else:
                    memName = names[i]
                rankChanges += ("%s -> %s\n"
                                % (memName, ranks[newRank]["emoji"]))
                oldRole = ctx.guild.get_role(ranks[oldRank]["roleid"])
                newRole = ctx.guild.get_role(ranks[newRank]["roleid"])
                if member is not None and oldRole is not None and newRole is not None:
                    if oldRole in member.roles:
                        await member.remove_roles(oldRole)
                    if newRole not in member.roles:
                        await member.add_roles(newRole)
        
                
        f = discord.File(fp=mmrTable, filename='MMRTable.png',
                         description=" ".join(names))
        e = discord.Embed(title="MMR Table")
        idField = str(tid)
        if tableMsg is not None:
            try:
                reactMsg = await channel.fetch_message(tableMsg)
            except:
                reactMsg = None
            if reactMsg is not None:
                idField = "[%d](%s)" % (tid, reactMsg.jump_url)
                CHECK_BOX = "\U00002611"
                await reactMsg.add_reaction(CHECK_BOX)
        else:
            reactMsg = None
        e.add_field(name="ID", value=idField)
        e.add_field(name="Tier", value=tier.upper())
        e.add_field(name="Updated by", value=ctx.author.mention)
        e.set_image(url="attachment://MMRTable.png")
        if reactMsg is not None:
            updateMsg = await reactMsg.reply(content=rankChanges, embed=e, file=f)
        else:
            updateMsg = await channel.send(content=rankChanges, embed=e, file=f)
        await workmsg.delete()
        if ctx.channel.id != channel.id:
            await ctx.send(f"Table ID `{tableid}` updated successfully; check {updateMsg.jump_url} to view")
        else:
            try:
                await ctx.message.delete()
            except Exception as e:
                pass
        await API.post.setUpdateMessageId(tid, updateMsg.id)
        return True

    @commands.check(command_check_reporter_roles)
    @commands.command(aliases=['us'])
    async def updateScores(self, ctx, tableID:int, *, args):
        table = await API.get.getTable(tableID)
        if table is False:
            await ctx.send("Table couldn't be found")
            return
        if not check_staff_roles(ctx):
            if "verifiedOn" in table.keys():
                await ctx.send("This table has been updated already, so you cannot edit the scores as a Reporter.")
                return
            if not is_player_in_table(ctx.author.id, table):
                await ctx.send("You did not play in this event, so you cannot edit the scores for this table")
                return
        success, scores = parseScores(args)
        if success is False:
            await ctx.send(f"An error has occurred setting scores:\n{scores}")
            return
        success = await API.post.setScores(tableID, scores)
        if success is not True:
            await ctx.send("An error occurred setting scores:\n%s"
                           % success)
            return
        if 'tableMessageId' in table.keys():
            channel = ctx.guild.get_channel(channels[table['tier']])
            table_msg = await channel.fetch_message(table['tableMessageId'])
            if table_msg is not None:
                #table_embed = get_table_embed(table, ctx.bot)
                table_embed = table_msg.embeds[0]
                table_embed.add_field(name=f"Edits by {ctx.author.display_name}",
                    value="\n".join([f"{name}: {scores[name]}" for name in scores.keys()]),
                    inline=False)
                await table_msg.edit(embed=table_embed)
        await ctx.send("Successfully edited scores")

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def undo(self, ctx, tableID:int):
        table = await API.get.getTable(tableID)
        if table is False:
            await ctx.send("Table not found")
            return
        tier = table['tier']
        rankChanges = ""
        if 'verifiedOn' in table.keys():
            names = []
            oldMMRs = []
            newMMRs = []
            peakMMRs = []
            discordids = []
            channel = ctx.guild.get_channel(channels[tier.upper()])
            for team in table['teams']:
                team['scores'].sort(key=lambda p: p['score'], reverse=True)
                for player in team['scores']:
                    names.append(player['playerName'])
                    oldMMRs.append(player['newMmr'])
                    newMMRs.append(player['prevMmr'])
                    if 'discordId' not in player.keys():
                        discordids.append(None)
                    else:
                        discordids.append(player['discordId'])
            for i in range(len(names)):
                oldRank = getRank(oldMMRs[i])
                newRank = getRank(newMMRs[i])
                if discordids[i] is None:
                    member = findmember(ctx, names[i], ranks[oldRank]["roleid"])
                    if member is not None:
                        await API.post.updateDiscord(names[i], member.id)
                if oldRank != newRank:
                    if discordids[i] is None:
                        member = findmember(ctx, names[i], ranks[oldRank]["roleid"])
                    else:
                        member = ctx.guild.get_member(int(discordids[i]))
                    # don't want to mention people in ticket threads and add them to it
                    if member is not None and not hasattr(ctx.channel, 'parent_id'):
                        memName = member.mention
                    else:
                        memName = names[i]
                    rankChanges += ("%s -> %s\n"
                                    % (memName, ranks[newRank]["emoji"]))
                    oldRole = ctx.guild.get_role(ranks[oldRank]["roleid"])
                    newRole = ctx.guild.get_role(ranks[newRank]["roleid"])
                    if member is not None and oldRole is not None and newRole is not None:
                        if oldRole in member.roles:
                            await member.remove_roles(oldRole)
                        if newRole not in member.roles:
                            await member.add_roles(newRole)
        channel = ctx.guild.get_channel(channels[tier])
        if 'tableMessageId' in table.keys():
            try:
                deleteMsg = await channel.fetch_message(table['tableMessageId'])
                if deleteMsg is not None:
                    await deleteMsg.delete()
            except:
                pass
        if 'updateMessageId' in table.keys():
            try:
                deleteMsg = await channel.fetch_message(table['updateMessageId'])
                if deleteMsg is not None:
                    await deleteMsg.delete()
            except:
                pass
            
        success = await API.post.deleteTable(tableID)
        if success is True:
            await ctx.send("Successfully deleted table with ID %d\n%s" % (tableID, rankChanges))
        else:
            await ctx.send("Table not found: Error %d" % success)

    @commands.command()
    async def fixRole(self, ctx, member_str=None):
        if (not check_staff_roles(ctx)) and (member_str is not None):
            await ctx.send("You cannot change other people's roles without a staff role")
            return
        converter = commands.MemberConverter()
        if member_str is None:
            member = ctx.author
        else:
            member = await converter.convert(ctx, member_str)
        player = await API.get.getPlayerFromDiscord(member.id)
        if player is None:
            await ctx.send("Player could not be found on lounge site")
            return
        for role in member.roles:
            for rank in ranks.values():
                if role.id == rank['roleid']:
                    await member.remove_roles(role)
            if role.id == placementRoleID:
                await member.remove_roles(role)
        player_role = ctx.guild.get_role(player_role_ID)
        roles_to_add = []
        if player_role not in member.roles:
            roles_to_add.append(player_role)
        if 'mmr' not in player.keys():
            role = member.guild.get_role(placementRoleID)
            #await member.add_roles(role)
            roles_to_add.append(role)
        else:
            rank = getRank(player['mmr'])
            role = member.guild.get_role(ranks[rank]['roleid'])
            #await member.add_roles(role)
            roles_to_add.append(role)
        await member.add_roles(*roles_to_add)
        if member.display_name != player['name']:
            await member.edit(nick=player['name'])
        await ctx.send("Fixed player's roles")
        

    #adds correct roles and nicknames for players when they join server
    @commands.Cog.listener(name='on_member_join')
    async def on_member_join(self, member):
        if member.bot:
            return
        if member.guild.id != self.bot.config['server']:
            return
        player = await API.get.getPlayerFromDiscord(member.id)
        if player is None:
            return
        player_role = member.guild.get_role(player_role_ID)
        if member.display_name != player['name']:
            await member.edit(nick=player['name'])
        if 'mmr' not in player.keys():
            role = member.guild.get_role(placementRoleID)
            roles_to_add = [role, player_role]
            await member.add_roles(*roles_to_add)
            return
        rank = getRank(player['mmr'])
        role = member.guild.get_role(ranks[rank]['roleid'])
        roles_to_add = [role, player_role]
        await member.add_roles(*roles_to_add)
        #await member.add_roles(player_role)
        

    #changes nicknames if someone changes their name to something else
    @commands.Cog.listener(name='on_user_update')
    async def on_user_update(self, before, after):
        if before.bot:
            return
        server = self.bot.get_guild(self.bot.config['server'])
        if server is None:
            return
        member = server.get_member(before.id)
        if member is None:
            return
        if member.nick is not None:
            return
        if before.display_name == after.display_name:
            return
        player = await API.get.getPlayerFromDiscord(before.id)
        if player is None:
            return
        if player['name'] != after.display_name:
            await member.edit(nick=player['name'])
        
        

async def setup(bot):
    await bot.add_cog(Updating(bot))
