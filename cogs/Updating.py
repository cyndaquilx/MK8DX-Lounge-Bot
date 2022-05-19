import discord
from discord.ext import commands

import openpyxl
import mmrTables
import API.post, API.get

from datetime import datetime
import dateutil.parser

from constants import (place_MMRs, place_scores, channels, getRank, ranks, placementRoleID, 
nameChangeLog, player_role_ID, strike_log_channel)
from typing import Union

import asyncio


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
                    errMsg = "%s is not a valid score!" % playerMult
                    return False, errMsg
                scores[playerName] = int(playerScore)
            except Exception as e:
                errMsg = "%s is not a valid score!" % playerMult
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
            
        

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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
        player = await API.get.getPlayer(newName)
        if 'discordId' not in player.keys():
            await ctx.send("Player does not have a discord ID on the site, please update their nickname manually")
            return
        member = ctx.guild.get_member(int(player['discordId']))
        if member is None:
            await ctx.send(f"Couldn't find member {player['name']}, please change their nickname manually")
            return
        await member.edit(nick=newName)
        await ctx.send("Successfully changed their nickname in server")
        

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command()
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

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command()
    async def updateDiscord(self, ctx, member:Union[discord.Member, int], *, name):
        if isinstance(member, discord.Member):
            member = member.id
        success, response = await API.post.updateDiscord(name, member)
        if success is False:
            await ctx.send(f"An error occurred: {response}")
            return
        #print(response)
        await ctx.send("Discord ID change successful")
        
    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command()
    async def placeMMR(self, ctx, mmr:int, *, name):
        success, p = await API.post.placePlayer(mmr, name)
        if success is False:
            await ctx.send("An error occurred while trying to place the player: %s"
                           % player)
            return
        player = await API.get.getPlayer(name)
        await self.givePlacementRole(ctx, name, mmr)
        await ctx.send("Successfully placed %s with %d MMR"
                       % (player["name"], mmr))

    async def auto_place(self, ctx, name, score:int):
        #rank = "iron"
        if score >= 130:
            rank = "silver"
        elif score >= 90:
            rank = "bronze"
        else:
            rank = "iron"
        #for p_score in sorted(place_scores.keys(), reverse=True):
        #    if score >= p_score:
        #        rank = place_scores[p_score]
        result = await self.place(ctx, rank, name=name)
        return result

    async def check_placements(self, ctx, table):
        for team in table["teams"]:
            for p in team["scores"]:
                #player = await API.get.getPlayer(p["playerName"])
                if "prevMmr" not in p.keys():
                    await self.auto_place(ctx, p["playerName"], p["score"])

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command()
    async def forcePlace(self, ctx, mmr:int, *, name):
        success, p = await API.post.forcePlace(mmr, name)
        if success is False:
            await ctx.send("An error occurred while trying to place the player: %s"
                           % p)
            return
        player = await API.get.getPlayer(name)
        await self.givePlacementRole(ctx, name, mmr)
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
##        elif isinstance(member, int) is False:
##            await ctx.send("Please type a valid discord ID or mention a user")
##            return
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

    @commands.has_any_role("Administrator")
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
##                if success is False:
##                    print(txt)
                if success is True:
                    print(f"Added discord id for {player['name']}: {member.id}")
                                     
            
    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command(aliases=['pen'])
    async def penalty(self, ctx, amount:int, tier, *, args):
        splitArgs = args.split(";")
        name = splitArgs[0].strip()
        reason = ""
        if len(splitArgs) > 1:
            reason = splitArgs[1].strip()
        if tier.upper() not in channels.keys():
            await ctx.send("Your tier is not valid! Valid tiers are: %s"
                           % list(channels.keys()))
            return
        if abs(amount) > 200:
            await ctx.send("Individual penalties can only be 200 points or lower")
            return
        channel = ctx.guild.get_channel(channels[tier.upper()])
        success, pen = await API.post.createPenalty(name, abs(amount), False)
        if success is False:
            await ctx.send("An error occurred while giving the penalty:\n%s"
                           % pen)
            return
        #print(pen)
        penaltyID = pen["id"]
        e = discord.Embed(title="Penalty added")
        e.add_field(name="Player", value=name, inline=False)
        e.add_field(name="Amount", value="-%d" % abs(amount))
        e.add_field(name="ID", value=penaltyID)
        e.add_field(name="Tier", value=tier.upper())
        e.add_field(name="Given by", value=ctx.author.mention)
        if reason != "":
            e.add_field(name="Reason", value=reason, inline=False)
        rankChange = await self.updateRoles(ctx, pen["playerName"], pen["prevMmr"], pen["newMmr"])
        await channel.send(embed=e, content=rankChange)
        strike_log = ctx.guild.get_channel(strike_log_channel)
        if strike_log is not None:
            await strike_log.send(embed=e, content=rankChange)
        if ctx.channel.id == channel.id:
            await ctx.message.delete()
        else:
            await ctx.send("Added -%d penalty to %s in %s"
                           % (abs(amount), name, channel.mention))

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command()
    async def deletePenalty(self, ctx, penID:int):
        success = await API.post.deletePenalty(penID)
        if success is True:
            await ctx.send("Successfully deleted penalty ID %d" % penID)
        else:
            await ctx.send(success)
        

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command(aliases=['str']) 
    async def strike(self, ctx, amount:int, tier, *, args):
        splitArgs = args.split(";")
        name = splitArgs[0].strip()
        reason = ""
        if len(splitArgs) > 1:
            reason = splitArgs[1].strip()
        if tier.upper() not in channels.keys():
            await ctx.send("Your tier is not valid! Valid tiers are: %s"
                           % list(channels.keys()))
            return
        if abs(amount) > 200:
            await ctx.send("Individual penalties can only be 200 points or lower")
            return
        channel = ctx.guild.get_channel(channels[tier.upper()])
        success, pen = await API.post.createPenalty(name, abs(amount), True)
        if success is False:
            await ctx.send("An error occurred while giving the penalty:\n%s"
                           % pen)
            return
        penaltyID = pen["id"]
        e = discord.Embed(title="Penalty + strike added")
        e.add_field(name="Player", value=pen["playerName"], inline=False)
        e.add_field(name="Amount", value="-%d" % abs(amount), inline=False)
        e.add_field(name="ID", value=penaltyID)
        e.add_field(name="Tier", value=tier.upper())
        e.add_field(name="Given by", value=ctx.author.mention)
        if reason != "":
            e.add_field(name="Reason", value=reason, inline=False)
        recentStrikes = await API.get.getStrikes(name)
        if recentStrikes is not False:
            last3 = recentStrikes[::-1][0:3]
            strikeStr = ""
            if len(last3) > 0:
                for pen in last3:
                    strikeDate = dateutil.parser.isoparse(pen["awardedOn"]).strftime('%m/%d/%Y')
                    strikeStr += "%s\n" % strikeDate
                e.add_field(name="Strikes", value=strikeStr, inline=False)
        rankChange = await self.updateRoles(ctx, pen["playerName"], pen["prevMmr"], pen["newMmr"])
        await channel.send(embed=e, content=rankChange)
        strike_log = ctx.guild.get_channel(strike_log_channel)
        if strike_log is not None:
            await strike_log.send(embed=e, content=rankChange)
        if ctx.channel.id == channel.id:
            await ctx.message.delete()
        else:
            await ctx.send("Added -%d penalty to %s in %s"
                           % (abs(amount), pen["playerName"], channel.mention))
        

    @commands.has_any_role("Administrator")
    @commands.command()
    async def bonus(self, ctx, amount:int, *, name):
        absAmount = abs(amount)
        success, addedBonus = await API.post.createBonus(name, absAmount)
        if success is False:
            await ctx.send("An error occurred while giving the bonus:\n%s"
                           % addedBonus)
            return
        await ctx.send("Successfully added %d MMR bonus to %s" % (absAmount, name))

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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
                msg += "\nTier %s - %d tables\n" % (tier, count)
                msg += "\n".join(["\tID %d" % tableid for tableid in ids])
        if len(msg) > 0:
            await ctx.send(msg)

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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
                print(e)
        await ctx.send("Updated all tables")

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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
                print(e)
        await ctx.send(f'Updated all tables in tier {tier.upper()}')

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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
                print(e)
        await ctx.send(f'Updated all tables up to ID {tid}')

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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
                print(e)
        await ctx.send(f'Updated all tables up to ID {tid} in tier {tier.upper()}')

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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
            
            
    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command()
    async def hide(self, ctx, *, name):
        success, text = await API.post.hidePlayer(name)
        if success is False:
            await ctx.send(f"An error occurred: {text}")
            return
        await ctx.send("Successfully hid player")
    
    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command()
    async def unhide(self, ctx, *, name):
        success, text = await API.post.unhidePlayer(name)
        if success is False:
            await ctx.send(f"An error occurred: {text}")
            return
        await ctx.send("Successfully unhid player")

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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
        if table["tier"] == "F":
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
                if 'discordId' not in player.keys():
                    discordids.append(None)
                else:
                    discordids.append(player['discordId'])
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
            await ctx.send(f"Table ID `{tableid}` updated successfully; check {channel.mention} to view")
        else:
            try:
                await ctx.message.delete()
            except Exception as e:
                pass
        await API.post.setUpdateMessageId(tid, updateMsg.id)
        return True

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command(aliases=['us'])
    async def updateScores(self, ctx, tableID:int, *, args):
        table = await API.get.getTable(tableID)
        if table is False:
            await ctx.send("Table couldn't be found")
            return
        success, scores = parseScores(args)
        success = await API.post.setScores(tableID, scores)
        if success is not True:
            await ctx.send("An error occurred setting scores:\n%s"
                           % success)
            return
        await ctx.send("Successfully edited scores")


    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
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

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S")
    @commands.command()
    async def fixRole(self, ctx, member:discord.Member):
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
