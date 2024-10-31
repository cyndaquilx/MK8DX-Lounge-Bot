import discord
from discord import app_commands
from discord.ext import commands

import mmrTables
import API.post, API.get
import urllib

import dateutil.parser
from datetime import datetime, timedelta, timezone

from constants import (get_table_embed, place_MMRs, place_scores, channels, getRank, ranks, placementRoleID, 
nameChangeLog, nameRequestLog, player_role_ID, strike_log_channel, is_player_in_table, name_request_channel, findmember, verification_msg,
mute_ban_channel)

from custom_checks import check_staff_roles, command_check_reporter_roles, command_check_staff_roles, check_name_restricted_roles, check_valid_name, command_check_admin_mkc_roles, command_check_all_staff_roles

from typing import Union, Optional
from util import submit_table, delete_table

import asyncio
import traceback
import copy

def parseMultipliers(args):
    multArgs = args.split(",")
    multipliers = {}
    for mult in multArgs:
        splitMult = mult.split()
        if len(splitMult) >= 2:
            playerName = " ".join(splitMult[:-1]).strip()
            playerMult = splitMult[-1].strip()
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
            playerName = " ".join(splitScore[:-1]).strip()
            playerScore = splitScore[-1].strip()
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
        #oldRoleID = placementRoleID
        newRoleID = ranks[getRank(placeMMR)]["roleid"]
        #oldRole = ctx.guild.get_role(oldRoleID)
        newRole = ctx.guild.get_role(newRoleID)
        #member = findmember(ctx, name, oldRole)
        if 'discordId' not in player.keys():
            await ctx.send("Player does not have a discord ID on the site, please give them one to give them placement roles")
            return
        member = ctx.guild.get_member(int(player['discordId']))
        if member is None:
            await ctx.send(f"Couldn't find member {player['name']}, please give them roles manually")
            return
        # if oldRole in member.roles:
        #     await member.remove_roles(oldRole)
        for role in member.roles:
            for rank in ranks.values():
                if role.id == rank['roleid']:
                    await member.remove_roles(role)
            if role.id == placementRoleID:
                await member.remove_roles(role)
        if newRole not in member.roles:
            await member.add_roles(newRole)
        await ctx.send(f"Managed to find member {member.display_name} and edit their roles")
            
    async def add_player(self, ctx, mkcID: int, member: discord.Member, name: str, mmr: int | None):
        name = name.strip()
        if not await check_valid_name(ctx, name):
            return
        content = "Please confirm the player details within 30 seconds"
        e = discord.Embed(title="New Player")
        e.add_field(name="Name", value=name)
        e.add_field(name="MKC ID", value=mkcID)
        if mmr is not None:
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
        
        if mmr is not None:
            success, player = await API.post.createPlayerWithMMR(mkcID, mmr, name, member.id)
        else:
            success, player = await API.post.createNewPlayer(mkcID, name, member.id)
        if success is False:
            await ctx.send("An error occurred while trying to add the player: %s"
                           % player)
            return
        
        
        roleGiven = ""
        roles = []
        player_role = ctx.guild.get_role(player_role_ID)
        if player_role:
            roles.append(player_role)
        if mmr is not None:
            rank = getRank(mmr)
            rank_role_id = ranks[rank]["roleid"]
            rank_role = ctx.guild.get_role(rank_role_id)
            if rank_role:
                roles.append(rank_role)
        else:
            placement_role = ctx.guild.get_role(placementRoleID)
            if placement_role:
                roles.append(placement_role)
        role_names = ", ".join([role.name for role in roles])
        try:
            await member.add_roles(*roles)
            if member.display_name != name:
                await member.edit(nick=name)
            roleGiven += f"\nAlso gave {member.mention} {role_names} role"
        except Exception as e:
            roleGiven += f"\nCould not give {role_names} roles to the player due to the following: {e}"
            pass
        try:
            await member.send(verification_msg)
            roleGiven += f"\nSuccessfully sent verification DM to the player"
        except Exception as e:
            roleGiven += f"\nPlayer does not accept DMs from the bot, so verification DM was not sent"
        await embedded.delete()
        
        url = ctx.bot.site_creds["website_url"] + "/PlayerDetails/%d" % int(player["id"])
        await ctx.send(f"Successfully added the new player: {url}{roleGiven}")
        e = discord.Embed(title="Added new player")
        e.add_field(name="Name", value=name)
        e.add_field(name="MKC ID", value=mkcID)
        e.add_field(name="Discord", value=member.mention)
        if mmr is not None:
            e.add_field(name="MMR", value=mmr)
        e.add_field(name="Added by", value=ctx.author.mention, inline=False)
        strike_log = ctx.guild.get_channel(strike_log_channel)
        if strike_log is not None:
            await strike_log.send(embed=e)

    @commands.check(command_check_admin_mkc_roles)
    @commands.command(name="addPlayer", aliases=["add"])
    async def add_player_command(self, ctx, mkc_id:int, member:discord.Member, *, name):
        await self.add_player(ctx, mkc_id, member, name, None)

    @commands.check(command_check_admin_mkc_roles)
    @commands.command(aliases=['apl'])
    async def addAndPlace(self, ctx, mkcID:int, mmr:int, member:discord.Member, *, name):
        await self.add_player(ctx, mkcID, member, name, mmr)

    @commands.hybrid_group(name="player")
    @app_commands.guilds(445404006177570829)
    async def player_group(self, ctx):
        pass

    @commands.check(command_check_admin_mkc_roles)
    @player_group.command(name="add")
    @app_commands.guilds(445404006177570829)
    async def add_player_hybrid(self, ctx, mkc_id:int, member:discord.Member, name: str, mmr: int | None):
        await self.add_player(ctx, mkc_id, member, name, mmr)

    async def hide_player(self, ctx, name: str):
        success, text = await API.post.hidePlayer(name)
        if success is False:
            await ctx.send(f"An error occurred: {text}")
            return
        await ctx.send("Successfully hid player")

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def hide(self, ctx, *, name):
        await self.hide_player(ctx, name)

    @commands.check(command_check_staff_roles)
    @player_group.command(name="hide")
    @app_commands.guilds(445404006177570829)
    async def hide_hybrid(self, ctx, name:str):
        await self.hide_player(ctx, name)

    async def update_discord(self, ctx, discord_id: int, name: str):
        player = await API.get.getPlayer(name)
        if player is None:
            await ctx.send("The player couldn't be found!")
            return
        success, response = await API.post.updateDiscord(name, discord_id)
        if success is False:
            await ctx.send(f"An error occurred: {response}")
            return
        await ctx.send("Discord ID change successful")
        e = discord.Embed(title="Discord ID changed")
        e.add_field(name="Player", value=player["name"])
        if "discordId" in player.keys():
            e.add_field(name="Old Discord", value=f"<@{player['discordId']}>")
        e.add_field(name="New Discord", value=f"<@{discord_id}>")
        e.add_field(name="Changed by", value=ctx.author.mention, inline=False)
        channel = ctx.guild.get_channel(mute_ban_channel)
        if channel is not None:
            await channel.send(embed=e)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['ud'])
    async def updateDiscord(self, ctx, member:Union[discord.Member, int], *, name):
        if isinstance(member, discord.Member):
            member = member.id
        await self.update_discord(ctx, member, name)
    
    @commands.check(command_check_staff_roles)
    @player_group.command(name="update_discord")
    @app_commands.guilds(445404006177570829)
    async def update_discord_hybrid(self, ctx, member: discord.Member, name: str):
        discord_id = member.id
        await self.update_discord(ctx, discord_id, name)

    async def fix_player_role(self, ctx, member: discord.Member):
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
            roles_to_add.append(role)
        else:
            rank = getRank(player['mmr'])
            role = member.guild.get_role(ranks[rank]['roleid'])
            roles_to_add.append(role)
        await member.add_roles(*roles_to_add)
        if member.display_name != player['name']:
            await member.edit(nick=player['name'])
        await ctx.send("Fixed player's roles")

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
        await self.fix_player_role(ctx, member)

    @commands.check(command_check_staff_roles)
    @player_group.command(name="fixrole")
    @app_commands.guilds(445404006177570829)
    async def fix_role_hybrid(self, ctx, member:discord.Member):
        await self.fix_player_role(ctx, member)

    async def unhide_player(self, ctx, name):
        success, text = await API.post.unhidePlayer(name)
        if success is False:
            await ctx.send(f"An error occurred: {text}")
            return
        await ctx.send("Successfully unhid player")

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def unhide(self, ctx, *, name):
        await self.unhide_player(ctx, name)

    @commands.check(command_check_staff_roles)
    @player_group.command(name="unhide")
    @app_commands.guilds(445404006177570829)
    async def unhide_player_hybrid(self, ctx, name: str):
        await self.unhide_player(ctx, name)

    async def refresh_player(self, ctx, name):
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

    @commands.check(command_check_all_staff_roles)
    @commands.command()
    async def refresh(self, ctx, *, name):
        await self.refresh_player(ctx, name)

    @commands.check(command_check_staff_roles)
    @player_group.command(name="refresh")
    @app_commands.guilds(445404006177570829)
    async def refresh_hybrid(self, ctx, name: str):
        await self.refresh_player(ctx, name)

    async def update_player_mkc(self, ctx, new_mkc_id: int, name: str):
        content = "Please confirm the MKC ID change within 30 seconds"
        e = discord.Embed(title="MKC ID Change")
        e.add_field(name="Name", value=name)
        e.add_field(name="New MKC ID", value=new_mkc_id)
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
        player = await API.get.getPlayer(name)
        if player is None:
            await ctx.send("The player couldn't be found!")
            return
        success = await API.post.updateMKCid(name, new_mkc_id)
        await embedded.delete()
        if success is not True:
            await ctx.send("An error occurred trying to change the MKC ID:\n%s" % success)
            return
        await ctx.send("MKC ID change successful")
        e = discord.Embed(title="MKC ID Changed")
        e.add_field(name="Player", value=player["name"])
        e.add_field(name="Old MKC ID", value=player["mkcId"])
        e.add_field(name="New MKC ID", value=new_mkc_id)
        if "discordId" in player.keys():
            e.add_field(name="Mention", value=f"<@{player['disccordId']}>")
        e.add_field(name="Changed by", value=ctx.author.mention, inline=False)
        strike_log = ctx.guild.get_channel(strike_log_channel)
        if strike_log is not None:
            await strike_log.send(embed=e)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['um'])
    async def updateMKC(self, ctx, newID:int, *, name):
        await self.update_player_mkc(ctx, newID, name)
    
    @commands.check(command_check_staff_roles)
    @player_group.command(name="mkc")
    @app_commands.guilds(445404006177570829)
    async def update_mkc_hybrid(self, ctx, new_mkc_id: int, name: str):
        await self.update_player_mkc(ctx, new_mkc_id, name)

    async def place_player_in_rank(self, ctx, rank, name):
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

    async def place_player_with_mmr(self, ctx, mmr:int, name:str):
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

    @commands.check(command_check_staff_roles)
    @player_group.command(name="place_rank")
    @app_commands.choices(
        rank = [
            app_commands.Choice(name=f"{r} ({place_MMRs[r]})", value=r) for r in place_MMRs
        ]
    )
    @app_commands.guilds(445404006177570829)
    async def place_rank_hybrid(self, ctx, rank, name):
        await self.place_player_in_rank(ctx, rank, name)
  
    @commands.check(command_check_staff_roles)
    @commands.command()
    async def place(self, ctx, rank, *, name):
        await self.place_player_in_rank(ctx, rank, name)

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def placeMMR(self, ctx, mmr:int, *, name):
        await self.place_player_with_mmr(ctx, mmr, name)

    @commands.check(command_check_staff_roles)
    @player_group.command(name="place_mmr")
    @app_commands.guilds(445404006177570829)
    async def place_mmr_hybrid(self, ctx, mmr:app_commands.Range[int, 0], name:str):
        await self.place_player_with_mmr(ctx, mmr, name)

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
        result = await self.place_player_with_mmr(ctx, mmr, name)
        return result

    async def check_placements(self, ctx, table):
        for team in table["teams"]:
            for p in team["scores"]:
                if "prevMmr" not in p.keys():
                    #print(table)
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
        e = discord.Embed(title="Player force placed")
        e.add_field(name="Player", value=player["name"], inline=False)
        e.add_field(name="MMR", value=mmr)
        if 'discordId' in player.keys():
            e.add_field(name="Mention", value=player['discordId'])
        e.add_field(name="Placed by", value=ctx.author.mention, inline=False)
        strike_log = ctx.guild.get_channel(strike_log_channel)
        if strike_log is not None:
            await strike_log.send(embed=e)

    @commands.hybrid_command(aliases=['rn'])
    @app_commands.guilds(445404006177570829)
    @commands.guild_only()
    async def requestname(self, ctx, *, name):
        if check_name_restricted_roles(ctx, ctx.author):
            await ctx.send("You are nickname restricted and cannot use this command")
            return
        if ctx.channel.id != name_request_channel:
            await ctx.send(f"You may only use this command in <#{name_request_channel}>")
            return
        name = name.strip()
        if not await check_valid_name(ctx, name):
            return
        player = await API.get.getPlayerFromDiscord(ctx.author.id)
        if player is None:
            await ctx.send("Your Discord ID is not linked to a Lounge profile, please make a support ticket for help.")
            return
        player_info = await API.get.getPlayerInfo(player["name"])
        last_change = player_info["nameHistory"][0]
        now = datetime.now(timezone.utc)
        last_change_date = dateutil.parser.isoparse(last_change["changedOn"])
        days_since_change = (now - last_change_date).days
        if days_since_change < 60:
            allowed_change_date = (last_change_date + timedelta(days=60)).strftime('%m/%d/%Y')
            await ctx.send(f"You changed your name less than 60 days ago. You can request a new name on {allowed_change_date}.")
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
            await ctx.send(f"An error occurred trying to request a name:\n{request}")
            return
        await ctx.send("Your name change request has been sent to staff for approval. Please wait, you will receive a DM when this request is accepted or denied (if you have server member DMs enabled).")
        log_channel = ctx.guild.get_channel(nameRequestLog)
        e = discord.Embed(title="New Name Change Request")
        e.add_field(name="Current Name", value=player['name'], inline=False)
        e.add_field(name="New Name", value=name, inline=False)
        log_msg = await log_channel.send(embed=e)
        await API.post.setNameChangeMessageId(player['name'], log_msg.id)

    async def approve_name_change(self, ctx, old_name: str):
        success, name_request = await API.post.acceptNameChange(old_name)
        if success is False:
            await ctx.send(f"An error occurred approving name change for {old_name}:\n{name_request}")
            return
        await ctx.send(f"Approved the name change: {name_request['name']} -> {name_request['newName']}")
        e = discord.Embed(title="Name change request approved")
        e.add_field(name="Current Name", value=name_request['name'])
        e.add_field(name="New Name", value=name_request["newName"], inline=False)
        e.add_field(name="Mention", value=f"<@{name_request['discordId']}>")
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
        else:
            try:
                await member.send(f"Your name change request from {name_request['name']} to {name_request['newName']} has been approved.")
            except Exception as e:
                pass
            try:
                await member.edit(nick=name_request['newName'])
            except Exception as e:
                pass

    @commands.check(command_check_staff_roles)
    @commands.hybrid_group(name="name")
    @app_commands.guilds(445404006177570829)
    async def name_group(self, ctx):
        pass

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['an'])
    async def approveName(self, ctx, *, old_name):
        await self.approve_name_change(ctx, old_name)

    @commands.check(command_check_staff_roles)
    @name_group.command(name="approve")
    @app_commands.guilds(445404006177570829)
    async def approve_name_hybrid(self, ctx, old_name:str):
        await self.approve_name_change(ctx, old_name)

    async def get_pending_names(self, ctx):
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
    @commands.command(aliases=['pn'])
    async def pendingNames(self, ctx):
        await self.get_pending_names(ctx)

    @commands.check(command_check_staff_roles)
    @name_group.command(name="pending")
    @app_commands.guilds(445404006177570829)
    async def pending_names_hybrid(self, ctx):
        await self.get_pending_names(ctx)

    async def approve_all_name_changes(self, ctx):
        changes = await API.get.getPendingNameChanges()
        if changes is False:
            await ctx.send("An error occurred when getting the name changes. Please try again later.")
            return
        if len(changes['players']) == 0:
            await ctx.send("There are no pending name changes")
            return
        for change in changes['players']:
            await self.approve_name_change(ctx, change['name'])
        await ctx.send("Approved all name changes")

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['ana'])
    async def approveNamesAll(self, ctx):
        await self.approve_all_name_changes(ctx)

    @commands.check(command_check_staff_roles)
    @name_group.command(name="approve_all")
    @app_commands.guilds(445404006177570829)
    async def approve_all_names_hybrid(self, ctx):
        await self.approve_all_name_changes(ctx)

    async def reject_name_change(self, ctx, old_name: str, reason: str | None):
        success, name_request = await API.post.rejectNameChange(old_name)
        if success is False:
            await ctx.send(f"An error occurred trying to reject name change from {old_name}:\n{name_request}")
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
        if reason:
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
    @commands.command(aliases=['rjn'])
    async def rejectName(self, ctx, *, args):
        splitArgs = args.split(";")
        name = splitArgs[0].strip()
        reason = None
        if len(splitArgs) > 1:
            reason = ";".join(splitArgs[1:]).strip()
        await self.reject_name_change(ctx, name, reason)

    @commands.check(command_check_staff_roles)
    @name_group.command(name="reject")
    @app_commands.guilds(445404006177570829)
    async def reject_name_hybrid(self, ctx, old_name: str, reason: str | None):
        await self.reject_name_change(ctx, old_name, reason)

    async def update_player_name(self, ctx, oldName, newName):
        if not await check_valid_name(ctx, newName):
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
        e = discord.Embed(title="Name changed by staff")
        e.add_field(name="Current Name", value=oldName)
        e.add_field(name="New Name", value=newName, inline=False)
        if 'discordId' in player.keys():
            e.add_field(name="Mention", value=f"<@{player['discordId']}>")
        e.add_field(name="Changed by", value=ctx.author.mention, inline=False)
        await channel.send(embed=e)
        
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
    @commands.command(aliases=['un'])
    async def updateName(self, ctx, *, args):
        names = args.split(",")
        if len(names) != 2:
            await ctx.send("Please send 2 names separated by commas: ex. `!updateName Old Name, New Name`")
            return
        oldName = names[0].strip()
        newName = names[1].strip()
        await self.update_player_name(ctx, oldName, newName)

    @commands.check(command_check_staff_roles)
    @name_group.command(name="update")
    @app_commands.guilds(445404006177570829)
    async def update_name_hybrid(self, ctx, old_name: str, new_name: str):
        await self.update_player_name(ctx, old_name, new_name)
        
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
        if reason:
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

    async def add_penalty(self, ctx, amount:int, tier, names, reason: str | None, is_anonymous=False, is_strike=False):
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

    async def parse_and_add_penalty(self, ctx, amount:int, tier, args, is_anonymous=False, is_strike=False):
        splitArgs = args.split(";")
        names = [s.strip() for s in splitArgs[0].split(",")]
        if len(set(names)) < len(names):
            await ctx.send("There is at least one duplicate name in your input, try again")
            return
        reason = None
        if len(splitArgs) > 1:
            reason = splitArgs[1].strip()
        await self.add_penalty(ctx, amount, tier, names, reason, is_anonymous, is_strike)
        
    @commands.check(command_check_staff_roles)
    @commands.hybrid_group(name="penalty", aliases=['pen'])
    @app_commands.guilds(445404006177570829)
    async def penalty_group(self, ctx, amount:int, tier, *, args):
        await self.parse_and_add_penalty(ctx, amount, tier, args)

    @commands.check(command_check_staff_roles)
    @penalty_group.command(name="new")
    @app_commands.guilds(445404006177570829)
    async def penalty_hybrid(self, ctx, amount:app_commands.Range[int, 1, 200], tier:str, names: str, reason:str | None, strike: bool = False, anonymous: bool = False):
        parsed_names = [n.strip() for n in names.split(",")]
        await self.add_penalty(ctx, amount, tier, parsed_names, reason, anonymous, strike)
    
    @commands.check(command_check_staff_roles)
    @penalty_group.command(name="strike")
    @app_commands.guilds(445404006177570829)
    async def strike_hybrid(self, ctx, amount:app_commands.Range[int, 1, 200], tier:str, names: str, reason:str | None, anonymous: bool = False):
        parsed_names = [n.strip() for n in names.split(",")]
        await self.add_penalty(ctx, amount, tier, parsed_names, reason, anonymous, True)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['apen', 'apenalty'])
    async def anonymousPenalty(self, ctx, amount:int, tier, *, args):
        await self.parse_and_add_penalty(ctx, amount, tier, args, is_anonymous=True)
        
    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['str']) 
    async def strike(self, ctx, amount:int, tier, *, args):
        await self.parse_and_add_penalty(ctx, amount, tier, args, is_strike=True)
        
    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['astr', 'astrike']) 
    async def anonymousStrike(self, ctx, amount:int, tier, *, args):
        await self.parse_and_add_penalty(ctx, amount, tier, args, is_anonymous=True, is_strike=True)

    async def delete_penalty(self, ctx, pen_id: int, reason: str | None):
        success = await API.post.deletePenalty(pen_id)
        if success is True:
            await ctx.send(f"Successfully deleted penalty ID {pen_id}")
        else:
            await ctx.send(success)
            return
        e = discord.Embed(title="Deleted Penalty")
        e.add_field(name="Penalty ID", value=pen_id)
        e.add_field(name="Removed by", value=ctx.author.mention)
        e.add_field(name="Removed in", value=ctx.channel.mention)
        if len(reason):
            e.add_field(name="Reason", value=reason, inline=False)
        strike_log = ctx.guild.get_channel(strike_log_channel)
        if strike_log is not None:
            await strike_log.send(embed=e)

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def deletePenalty(self, ctx, pen_id:int, *, reason=None):
        await self.delete_penalty(ctx, pen_id, reason)

    @commands.check(command_check_staff_roles)
    @penalty_group.command(name="delete")
    @app_commands.guilds(445404006177570829)
    async def delete_penalty_hybrid(self, ctx, pen_id: int, reason=None):
        await self.delete_penalty(ctx, pen_id, reason)

    async def give_bonus(self, ctx, amount:int, name: str, reason: str | None):
        player = await API.get.getPlayer(name)
        if player is None:
            await ctx.send("Player not found!")
            return
        success, addedBonus = await API.post.createBonus(name, amount)
        if success is False:
            await ctx.send("An error occurred while giving the bonus:\n%s"
                           % addedBonus)
            return
        rankChange = await self.updateRoles(ctx, addedBonus["playerName"], addedBonus["prevMmr"], addedBonus["newMmr"])

        embed_title = "Bonus added"
        e = discord.Embed(title=embed_title)
        e.add_field(name="Player", value=addedBonus["playerName"], inline=False)
        e.add_field(name="Amount", value=f"{amount}")
        e.add_field(name="Given by", value=ctx.author.mention)
        if reason:
            e.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(content=f"Successfully added {amount} MMR bonus to {name}\n{rankChange}", embed=e)

        strike_log = ctx.guild.get_channel(strike_log_channel)
        if strike_log is not None:
            await strike_log.send(embed=e, content=rankChange)
        if 'discordId' in player.keys():
            member = ctx.guild.get_member(int(player['discordId']))
            if not member:
                return
            try:
                await member.send(f"You were given a +{amount} MMR bonus in MK8DX 150cc Lounge. Reason: {reason}")
            except Exception as e:
                pass

    @commands.check(command_check_staff_roles)
    @commands.hybrid_group(name="bonus")
    @app_commands.guilds(445404006177570829)
    async def bonus_group(self, ctx, amount:int, *, args):
        splitArgs = args.split(";")
        name = splitArgs[0]
        reason = None
        if len(splitArgs) > 1:
            reason = splitArgs[1].strip()
        
        absAmount = abs(amount)
        await self.give_bonus(ctx, absAmount, name, reason)

    @commands.check(command_check_staff_roles)
    @bonus_group.command(name="new")
    @app_commands.guilds(445404006177570829)
    async def bonus_hybrid(self, ctx, amount:app_commands.Range[int, 1, 200], name:str, reason:str | None):
        await self.give_bonus(ctx, amount, name, reason)

    @commands.check(command_check_staff_roles)
    @commands.hybrid_command()
    @app_commands.guilds(445404006177570829)
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
                curr_line = f"\n<#{channels[tier]}> - {count} tables\n"
                if len(msg) + len(curr_line) > 2000:
                    await ctx.send(msg)
                    msg = ""
                msg += curr_line
                for tableid in ids:
                    curr_line = f"\tID {tableid}\n"
                    if len(msg) + len(curr_line) > 2000:
                        await ctx.send(msg)
                        msg = ""
                    msg += curr_line
        if len(msg) > 0:
            await ctx.send(msg)

    @commands.check(command_check_staff_roles)
    @commands.hybrid_group(name="update", invoke_without_command=True, aliases=['u'])
    @app_commands.guilds(445404006177570829)
    async def update_group(self, ctx, tableid: int, *, extraArgs=""):
        await self.update_table(ctx, tableid, extraArgs=extraArgs)

    @commands.check(command_check_staff_roles)
    @update_group.command(name="table")
    @app_commands.guilds(445404006177570829)
    async def update_table_hybrid(self, ctx, tableid: int, *, multipliers=""):
        await self.update_table(ctx, tableid, extraArgs=multipliers)

    async def update_all_tables(self, ctx):
        tables = await API.get.getPending()
        if tables is False:
            await ctx.send("There are no pending tables")
            return
        for table in tables:
            try:
                success = await self.update_table(ctx, table["id"])
                if success is False:
                    return
            except Exception as e:
                #print(e)
                traceback.print_exc()
        await ctx.send("Updated all tables")

    @commands.check(command_check_staff_roles)
    @update_group.command(name="all", aliases=['a'])
    @app_commands.guilds(445404006177570829)
    async def update_all_hybrid(self, ctx):
        await self.update_all_tables(ctx)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['ua'])
    async def updateAll(self, ctx):
        await self.update_all_tables(ctx)

    async def update_tier(self, ctx, tier):
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
                success = await self.update_table(ctx, table["id"])
                if success is False:
                    return
            except Exception as e:
                traceback.print_exc()
        await ctx.send(f'Updated all tables in tier {tier.upper()}')

    @commands.check(command_check_staff_roles)
    @update_group.command(name="tier", aliases=['t'])
    @app_commands.guilds(445404006177570829)
    async def update_tier_hybrid(self, ctx, tier):
        await self.update_tier(ctx, tier)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['ut'])
    async def updateTier(self, ctx, tier):
        await self.update_tier(ctx, tier)

    async def update_until_id(self, ctx, tid:int):
        tables = await API.get.getPending()
        if tables is False:
            await ctx.send("There are no pending tables")
            return
        for table in tables:
            if table["id"] > tid:
                continue
            try:
                success = await self.update_table(ctx, table["id"])
                if success is False:
                    return
            except Exception as e:
                traceback.print_exc()
        await ctx.send(f'Updated all tables up to ID {tid}')

    @commands.check(command_check_staff_roles)
    @update_group.command(name="until", aliases=['u'])
    @app_commands.guilds(445404006177570829)
    async def update_until_hybrid(self, ctx, tableid: int):
        await self.update_until_id(ctx, tableid)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['uu'])
    async def updateUntil(self, ctx, tableid:int):
        await self.update_until_id(ctx, tableid)

    async def update_tier_until_id(self, ctx, tier, tid:int):
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
                success = await self.update_table(ctx, table["id"])
                if success is False:
                    return
            except Exception as e:
                traceback.print_exc()
        await ctx.send(f'Updated all tables up to ID {tid} in tier {tier.upper()}')

    @commands.check(command_check_staff_roles)
    @update_group.command(name="tier_until", aliases=['tu'])
    @app_commands.guilds(445404006177570829)
    async def update_tier_until_hybrid(self, ctx, tier, tableid: int):
        await self.update_tier_until_id(ctx, tier, tableid)

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['utu'])
    async def updateTierUntil(self, ctx, tier, tableid:int):
        await self.update_tier_until_id(ctx, tier, tableid)

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
                await workmsg.edit(content=f"Error setting multipliers:\n{updatedMultipliers}")
                return False
        await workmsg.edit(content=f"Successfully set multipliers for table")

    @commands.check(command_check_staff_roles)
    @commands.command(aliases=['mlraces'])
    async def multiplierRaces(self, ctx, tableid: int, *, extraArgs=""):
        table = await API.get.getTable(tableid)
        if table is False:
            await ctx.send("Table couldn't be found")
            return
        workmsg = await ctx.send("Working...")
        race_args = extraArgs.split(",")
        missed_races = {}
        min_missed_races = 3
        no_loss_races = 8
        for arg in race_args:
            split_arg = arg.split()
            if len(split_arg) >= 2:
                player_name = " ".join(split_arg[:-1]).strip()
                player_races = split_arg[-1].strip()
                if not player_races.isdigit():
                    await workmsg.edit(content=f"{player_races} is not an integer between {min_missed_races}-12")
                    return
                player_races_int = int(player_races)
                if player_races_int < min_missed_races:
                    await workmsg.edit(content=f"The minimum number of races to be missed for increased loss is f{min_missed_races}")
                    return
                if player_name.isdigit():
                    for team in table["teams"]:
                        for team_player in team["scores"]:
                            if team_player["playerDiscordId"] == player_name:
                                player_name = team_player["playerName"]
                missed_races[player_name] = player_races_int
        if len(missed_races) == 0:
            await ctx.send("No valid arguments found")
            return
        def get_player_team(player):
            for team in table["teams"]:
                for team_player in team["scores"]:
                    if team_player["playerName"].lower() == player.lower():
                        return team
            return None
        
        multipliers = {}
        for player, races in missed_races.items():
            team = get_player_team(player)
            if team is None:
                await workmsg.edit(content=f"{player} not found on table ID {tableid}!")
                return
            if races >= no_loss_races:
                mult = 0
            else:
                mult = 1 - (races/12)
            for team_player in team["scores"]:
                if team_player["playerName"].lower() != player.lower():
                    multipliers[team_player["playerName"]] = mult

        updatedMultipliers = await API.post.setMultipliers(tableid, multipliers)
        if updatedMultipliers is not True:
            await workmsg.edit(content=f"Error setting multipliers:\n{updatedMultipliers}")
            return
        
        mult_msg = "\n".join([f"{player}: {mult:.2f}" for player, mult in multipliers.items()])
        await workmsg.edit(content=f"Set the following multipliers:\n{mult_msg}")
            
    async def update_table(self, ctx, tableid:int, *, extraArgs=""):
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
            await ctx.send(f"An error occurred while updating table ID {tableid}:\n{table}")
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
        #await workmsg.delete()
        if ctx.channel.id != channel.id:
            await workmsg.edit(content=f"Table ID `{tableid}` updated successfully; check {updateMsg.jump_url} to view")
        else:
            await workmsg.delete()
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
    async def fixNames(self, ctx, table_id:int, *, args):
        table = await API.get.getTableClass(table_id)
        if table is None:
            await ctx.send("Table couldn't be found")
            return
        old_table = copy.deepcopy(table) # make a deep copy so we can preserve data after mutation
        names = args.split(",")
        if len(names) % 2 != 0:
            await ctx.send("You must enter an even number of names to use this command")
            return
        old_names = [names[i].strip() for i in range(0, len(names), 2)]
        new_names = [names[i].strip() for i in range(1, len(names), 2)]
        nameAPIchecks = await API.get.checkNames(new_names)
        err_str = ""
        for name in nameAPIchecks:
            if name is False:
                if len(err_str) == 0:
                    err_str += "The following players cannot be found on the leaderboard:\n"
                err_str += "%s\n" % name
        if len(err_str) > 0:
            await ctx.send(err_str)
            return
        new_names = nameAPIchecks
        for i in range(len(old_names)):
            score = table.get_score(old_names[i])
            if not score:
                await ctx.send(f"An error has occurred: Player {old_names[i]} not found on table ID {table_id}")
                return
            score.player.name = new_names[i]
        new_table = await submit_table(ctx, table)
        if not new_table:
            return
        await delete_table(ctx, old_table, send_log=False)
        strike_log = ctx.guild.get_channel(strike_log_channel)
        e = discord.Embed(title="Table names fixed")
        e.add_field(name="Old ID", value=old_table.id)
        e.add_field(name="New ID", value=new_table.id)
        e.add_field(name="Updated by", value=ctx.author.mention, inline=False)
        if strike_log is not None:
            await strike_log.send(embed=e)


    # @commands.check(command_check_staff_roles)
    # @commands.command()
    # async def fixNames(self, ctx, tableID:int, *, args):
    #     table = await API.get.getTable(tableID)
    #     if table is False:
    #         await ctx.send("Table couldn't be found")
    #         return
    #     names = args.split(",")
    #     if len(names) % 2 != 0:
    #         await ctx.send("You must enter an even number of names to use this command")
    #         return
    #     old_names = [names[i].strip() for i in range(0, len(names), 2)]
    #     new_names = [names[i].strip() for i in range(1, len(names), 2)]
    #     nameAPIchecks = await API.get.checkNames(new_names)
    #     err_str = ""
    #     for name in nameAPIchecks:
    #         if name is False:
    #             if len(err_str) == 0:
    #                 err_str += "The following players cannot be found on the leaderboard:\n"
    #             err_str += "%s\n" % name
    #     if len(err_str) > 0:
    #         await ctx.send(err_str)
    #         return
    #     new_names = nameAPIchecks
        
    #     def get_table_player(player):
    #         for team in table["teams"]:
    #             for team_player in team["scores"]:
    #                 if team_player["playerName"].lower() == player.lower():
    #                     return team_player
    #         return None

    #     names = []
    #     scores = []
    #     size = int(12/table["numTeams"])
    #     tier = table["tier"]
    #     for i in range(len(old_names)):
    #         table_player = get_table_player(old_names[i])
    #         if not table_player:
    #             await ctx.send(f"An error has occurred: Player {old_names[i]} not found on table ID {tableID}")
    #             return
    #         table_player["playerName"] = new_names[i]
    #     for team in table["teams"]:
    #         for team_player in team["scores"]:
    #             names.append(team_player["playerName"])
    #             scores.append(team_player["score"])
        
    #     is984 = sum(scores)
    #     teamscores = []
    #     teamnames = []
    #     teamplayerscores = []
    #     for i in range(int(12/size)):
    #         teamscore = 0
    #         tnames = []
    #         pscores = []
    #         for j in range(size):
    #             teamscore += scores[i*size+j]
    #             tnames.append(names[i*size+j])
    #             pscores.append(scores[i*size+j])
    #         teamscores.append(teamscore)
    #         teamnames.append(tnames)
    #         teamplayerscores.append(pscores)

    #     sortedScoresTeams = sorted(zip(teamscores, teamnames, teamplayerscores), reverse=True)
    #     sortedScores = [x for x, _, _ in sortedScoresTeams]
    #     sortedTeams = [x for _, x, _ in sortedScoresTeams]
    #     sortedpScores = [x for _, _, x in sortedScoresTeams]
    #     sortedNames = []
    #     tableScores = []
    #     placements = []
    #     for i in range(len(sortedScores)):
    #         sortedNames += sortedTeams[i]
    #         tableScores += sortedpScores[i]
    #         if i == 0:
    #             placements.append(1)
    #             continue
    #         if sortedScores[i] == sortedScores[i-1]:
    #             placements.append(placements[i-1])
    #             continue
    #         placements.append(i+1)

    #     base_url_lorenzi = "https://gb.hlorenzi.com/table.png?data="
    #     if size > 1:
    #         table_text = ("#title Tier %s %dv%d\n"
    #                       % (tier.upper(), size, size))
    #     else:
    #         table_text = ("#title Tier %s FFA\n"
    #                       % (tier.upper()))
    #     if size == 1:
    #         table_text += "FFA - Free for All #4A82D0\n"
    #     for i in range(int(12/size)):
    #         if size != 1:
    #             if i % 2 == 0:
    #                 teamcolor = "#1D6ADE"
    #             else:
    #                 teamcolor = "#4A82D0"
    #             table_text += "%d %s\n" % (placements[i], teamcolor)
    #         for j in range(size):
    #             index = size * i + j
    #             table_text += ("%s %d\n"
    #                            % (sortedTeams[i][j], sortedpScores[i][j]))

    #     url_table_text = urllib.parse.quote(table_text)
    #     image_url = base_url_lorenzi + url_table_text

    #     e = discord.Embed(title="Table")
    #     e.set_image(url=image_url)
    #     content = "Please react to this message with \U00002611 within the next 30 seconds to confirm the table is correct"
    #     if is984 != 984:
    #         warning = ("The total score of %d might be incorrect! Most tables should add up to 984 points"
    #                    % is984)
    #         e.add_field(name="Warning", value=warning)
    #     embedded = await ctx.send(content=content, embed=e)
    #     #ballot box with check emoji
    #     CHECK_BOX = "\U00002611"
    #     X_MARK = "\U0000274C"
    #     await embedded.add_reaction(CHECK_BOX)
    #     await embedded.add_reaction(X_MARK)

    #     def check(reaction, user):
    #         if user != ctx.author:
    #             return False
    #         if reaction.message != embedded:
    #             return False
    #         if str(reaction.emoji) == X_MARK:
    #             return True
    #         if str(reaction.emoji) == CHECK_BOX:
    #             return True
    #     try:
    #         reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
    #     except:
    #         await embedded.delete()
    #         return

    #     if str(reaction.emoji) == X_MARK:
    #         await embedded.delete()
    #         return
        
    #     # delete the previous table
    #     rankChanges = ""
    #     if 'verifiedOn' in table.keys():
    #         names = []
    #         oldMMRs = []
    #         newMMRs = []
    #         discordids = []
    #         channel = ctx.guild.get_channel(channels[tier.upper()])
    #         for team in table['teams']:
    #             team['scores'].sort(key=lambda p: p['score'], reverse=True)
    #             for player in team['scores']:
    #                 names.append(player['playerName'])
    #                 oldMMRs.append(player['newMmr'])
    #                 newMMRs.append(player['prevMmr'])
    #                 if 'discordId' not in player.keys():
    #                     discordids.append(None)
    #                 else:
    #                     discordids.append(player['discordId'])
    #         for i in range(len(names)):
    #             oldRank = getRank(oldMMRs[i])
    #             newRank = getRank(newMMRs[i])
    #             if discordids[i] is None:
    #                 member = findmember(ctx, names[i], ranks[oldRank]["roleid"])
    #                 if member is not None:
    #                     await API.post.updateDiscord(names[i], member.id)
    #             if oldRank != newRank:
    #                 if discordids[i] is None:
    #                     member = findmember(ctx, names[i], ranks[oldRank]["roleid"])
    #                 else:
    #                     member = ctx.guild.get_member(int(discordids[i]))
    #                 # don't want to mention people in ticket threads and add them to it
    #                 if member is not None and not hasattr(ctx.channel, 'parent_id'):
    #                     memName = member.mention
    #                 else:
    #                     memName = names[i]
    #                 rankChanges += ("%s -> %s\n"
    #                                 % (memName, ranks[newRank]["emoji"]))
    #                 oldRole = ctx.guild.get_role(ranks[oldRank]["roleid"])
    #                 newRole = ctx.guild.get_role(ranks[newRank]["roleid"])
    #                 if member is not None and oldRole is not None and newRole is not None:
    #                     if oldRole in member.roles:
    #                         await member.remove_roles(oldRole)
    #                     if newRole not in member.roles:
    #                         await member.add_roles(newRole)
    #     channel = ctx.guild.get_channel(channels[tier])
    #     if 'tableMessageId' in table.keys():
    #         try:
    #             deleteMsg = await channel.fetch_message(table['tableMessageId'])
    #             if deleteMsg is not None:
    #                 await deleteMsg.delete()
    #         except:
    #             pass
    #     if 'updateMessageId' in table.keys():
    #         try:
    #             deleteMsg = await channel.fetch_message(table['updateMessageId'])
    #             if deleteMsg is not None:
    #                 await deleteMsg.delete()
    #         except:
    #             pass
    #     success = await API.post.deleteTable(tableID)
    #     if success is True:
    #         await ctx.send("Successfully deleted table with ID %d\n%s" % (tableID, rankChanges))
    #     else:
    #         await ctx.send("Failed to delete the table: Error %d" % success)
    #         return

    #     # send the new table
    #     success, sentTable = await API.post.createTable(tier.upper(), sortedTeams, sortedpScores, ctx.author.id)
    #     if success is False:
    #         await ctx.send("An error occurred trying to send the new table!\n%s"
    #                        % sentTable)
    #         return
    #     newid = sentTable["id"]
    #     tableurl = ctx.bot.site_creds["website_url"] + sentTable["url"]

    #     e = discord.Embed(title="Mogi Table", colour=int("0A2D61", 16))

    #     e.add_field(name="ID", value=newid)
    #     e.add_field(name="Tier", value=tier.upper())
    #     e.add_field(name="Submitted by", value=ctx.author.mention)
    #     e.add_field(name="Submitted from", value=ctx.channel.jump_url)
    #     e.add_field(name="View on website", value=(ctx.bot.site_creds["website_url"] + "/TableDetails/%d" % newid), inline=False)
    #     if is984 != 984:
    #         warning = ("The total score of %d might be incorrect! Most tables should add up to 984 points"
    #                    % is984)
    #         e.add_field(name="Warning", value=warning, inline=False)

    #     e.set_image(url=tableurl)
    #     channel = ctx.guild.get_channel(channels[tier.upper()])

    #     tableMsg = await channel.send(embed=e)
        
    #     await API.post.setTableMessageId(newid, tableMsg.id)
    #     await embedded.delete()
    #     if channel == ctx.channel:
    #         await ctx.message.delete()
    #     else:
    #         await ctx.send("Successfully sent table to %s `(ID: %d)`" %
    #                        (tableMsg.jump_url, newid))
    #     strike_log = ctx.guild.get_channel(strike_log_channel)
    #     e = discord.Embed(title="Table names fixed")
    #     e.add_field(name="Old ID", value=tableID)
    #     e.add_field(name="New ID", value=newid)
    #     e.add_field(name="Updated by", value=ctx.author.mention, inline=False)
    #     if strike_log is not None:
    #         await strike_log.send(embed=e)

    @commands.check(command_check_staff_roles)
    @commands.command()
    async def fixScores(self, ctx, table_id:int, *, args):
        table = await API.get.getTableClass(table_id)
        if table is None:
            await ctx.send("Table couldn't be found")
            return
        old_table = copy.deepcopy(table) # make a deep copy so we can preserve data after mutation
        success, parsed_scores = parseScores(args)
        if success is False:
            await ctx.send(f"An error has occurred parsing input:\n{parsed_scores}")
            return
        for player in parsed_scores:
            table_score = table.get_score(player)
            if not table_score:
                await ctx.send(f"An error has occurred: Player {player} not found on table ID {table_id}")
                return
            table_score.score = parsed_scores[player]
        new_table = await submit_table(ctx, table)
        if not new_table:
            return
        await delete_table(ctx, old_table, send_log=False)
        strike_log = ctx.guild.get_channel(strike_log_channel)
        e = discord.Embed(title="Table scores fixed")
        e.add_field(name="Old ID", value=old_table.id)
        e.add_field(name="New ID", value=new_table.id)
        e.add_field(name="Updated by", value=ctx.author.mention, inline=False)
        if strike_log is not None:
            await strike_log.send(embed=e)

    # @commands.check(command_check_staff_roles)
    # @commands.command()
    # async def fixScores(self, ctx, tableID:int, *, args):
    #     table = await API.get.getTable(tableID)
    #     if table is False:
    #         await ctx.send("Table couldn't be found")
    #         return
    #     success, parsed_scores = parseScores(args)
    #     if success is False:
    #         await ctx.send(f"An error has occurred parsing input:\n{parsed_scores}")
    #         return
        
    #     def get_table_player(player):
    #         for team in table["teams"]:
    #             for team_player in team["scores"]:
    #                 if team_player["playerName"].lower() == player.lower():
    #                     return team_player
    #         return None
        
    #     names = []
    #     scores = []
    #     size = int(12/table["numTeams"])
    #     tier = table["tier"]
    #     for player in parsed_scores:
    #         table_player = get_table_player(player)
    #         if not table_player:
    #             await ctx.send(f"An error has occurred: Player {player} not found on table ID {tableID}")
    #             return
    #         table_player["score"] = parsed_scores[player]
    #     for team in table["teams"]:
    #         for team_player in team["scores"]:
    #             names.append(team_player["playerName"])
    #             scores.append(team_player["score"])
        
    #     is984 = sum(scores)
    #     teamscores = []
    #     teamnames = []
    #     teamplayerscores = []
    #     for i in range(int(12/size)):
    #         teamscore = 0
    #         tnames = []
    #         pscores = []
    #         for j in range(size):
    #             teamscore += scores[i*size+j]
    #             tnames.append(names[i*size+j])
    #             pscores.append(scores[i*size+j])
    #         teamscores.append(teamscore)
    #         teamnames.append(tnames)
    #         teamplayerscores.append(pscores)

    #     sortedScoresTeams = sorted(zip(teamscores, teamnames, teamplayerscores), reverse=True)
    #     sortedScores = [x for x, _, _ in sortedScoresTeams]
    #     sortedTeams = [x for _, x, _ in sortedScoresTeams]
    #     sortedpScores = [x for _, _, x in sortedScoresTeams]
    #     sortedNames = []
    #     tableScores = []
    #     placements = []
    #     for i in range(len(sortedScores)):
    #         sortedNames += sortedTeams[i]
    #         tableScores += sortedpScores[i]
    #         if i == 0:
    #             placements.append(1)
    #             continue
    #         if sortedScores[i] == sortedScores[i-1]:
    #             placements.append(placements[i-1])
    #             continue
    #         placements.append(i+1)

    #     base_url_lorenzi = "https://gb.hlorenzi.com/table.png?data="
    #     if size > 1:
    #         table_text = ("#title Tier %s %dv%d\n"
    #                       % (tier.upper(), size, size))
    #     else:
    #         table_text = ("#title Tier %s FFA\n"
    #                       % (tier.upper()))
    #     if size == 1:
    #         table_text += "FFA - Free for All #4A82D0\n"
    #     for i in range(int(12/size)):
    #         if size != 1:
    #             if i % 2 == 0:
    #                 teamcolor = "#1D6ADE"
    #             else:
    #                 teamcolor = "#4A82D0"
    #             table_text += "%d %s\n" % (placements[i], teamcolor)
    #         for j in range(size):
    #             index = size * i + j
    #             table_text += ("%s %d\n"
    #                            % (sortedTeams[i][j], sortedpScores[i][j]))

    #     url_table_text = urllib.parse.quote(table_text)
    #     image_url = base_url_lorenzi + url_table_text

    #     e = discord.Embed(title="Table")
    #     e.set_image(url=image_url)
    #     content = "Please react to this message with \U00002611 within the next 30 seconds to confirm the table is correct"
    #     if is984 != 984:
    #         warning = ("The total score of %d might be incorrect! Most tables should add up to 984 points"
    #                    % is984)
    #         e.add_field(name="Warning", value=warning)
    #     embedded = await ctx.send(content=content, embed=e)
    #     #ballot box with check emoji
    #     CHECK_BOX = "\U00002611"
    #     X_MARK = "\U0000274C"
    #     await embedded.add_reaction(CHECK_BOX)
    #     await embedded.add_reaction(X_MARK)

    #     def check(reaction, user):
    #         if user != ctx.author:
    #             return False
    #         if reaction.message != embedded:
    #             return False
    #         if str(reaction.emoji) == X_MARK:
    #             return True
    #         if str(reaction.emoji) == CHECK_BOX:
    #             return True
    #     try:
    #         reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
    #     except:
    #         await embedded.delete()
    #         return

    #     if str(reaction.emoji) == X_MARK:
    #         await embedded.delete()
    #         return
        
    #     # delete the previous table
    #     rankChanges = ""
    #     if 'verifiedOn' in table.keys():
    #         names = []
    #         oldMMRs = []
    #         newMMRs = []
    #         discordids = []
    #         channel = ctx.guild.get_channel(channels[tier.upper()])
    #         for team in table['teams']:
    #             team['scores'].sort(key=lambda p: p['score'], reverse=True)
    #             for player in team['scores']:
    #                 names.append(player['playerName'])
    #                 oldMMRs.append(player['newMmr'])
    #                 newMMRs.append(player['prevMmr'])
    #                 if 'discordId' not in player.keys():
    #                     discordids.append(None)
    #                 else:
    #                     discordids.append(player['discordId'])
    #         for i in range(len(names)):
    #             oldRank = getRank(oldMMRs[i])
    #             newRank = getRank(newMMRs[i])
    #             if discordids[i] is None:
    #                 member = findmember(ctx, names[i], ranks[oldRank]["roleid"])
    #                 if member is not None:
    #                     await API.post.updateDiscord(names[i], member.id)
    #             if oldRank != newRank:
    #                 if discordids[i] is None:
    #                     member = findmember(ctx, names[i], ranks[oldRank]["roleid"])
    #                 else:
    #                     member = ctx.guild.get_member(int(discordids[i]))
    #                 # don't want to mention people in ticket threads and add them to it
    #                 if member is not None and not hasattr(ctx.channel, 'parent_id'):
    #                     memName = member.mention
    #                 else:
    #                     memName = names[i]
    #                 rankChanges += ("%s -> %s\n"
    #                                 % (memName, ranks[newRank]["emoji"]))
    #                 oldRole = ctx.guild.get_role(ranks[oldRank]["roleid"])
    #                 newRole = ctx.guild.get_role(ranks[newRank]["roleid"])
    #                 if member is not None and oldRole is not None and newRole is not None:
    #                     if oldRole in member.roles:
    #                         await member.remove_roles(oldRole)
    #                     if newRole not in member.roles:
    #                         await member.add_roles(newRole)
    #     channel = ctx.guild.get_channel(channels[tier])
    #     if 'tableMessageId' in table.keys():
    #         try:
    #             deleteMsg = await channel.fetch_message(table['tableMessageId'])
    #             if deleteMsg is not None:
    #                 await deleteMsg.delete()
    #         except:
    #             pass
    #     if 'updateMessageId' in table.keys():
    #         try:
    #             deleteMsg = await channel.fetch_message(table['updateMessageId'])
    #             if deleteMsg is not None:
    #                 await deleteMsg.delete()
    #         except:
    #             pass
    #     success = await API.post.deleteTable(tableID)
    #     if success is True:
    #         await ctx.send("Successfully deleted table with ID %d\n%s" % (tableID, rankChanges))
    #     else:
    #         await ctx.send("Failed to delete the table: Error %d" % success)
    #         return

    #     # send the new table
    #     success, sentTable = await API.post.createTable(tier.upper(), sortedTeams, sortedpScores, ctx.author.id)
    #     if success is False:
    #         await ctx.send("An error occurred trying to send the new table!\n%s"
    #                        % sentTable)
    #         return
    #     newid = sentTable["id"]
    #     tableurl = ctx.bot.site_creds["website_url"] + sentTable["url"]

    #     e = discord.Embed(title="Mogi Table", colour=int("0A2D61", 16))

    #     e.add_field(name="ID", value=newid)
    #     e.add_field(name="Tier", value=tier.upper())
    #     e.add_field(name="Submitted by", value=ctx.author.mention)
    #     e.add_field(name="Submitted from", value=ctx.channel.jump_url)
    #     e.add_field(name="View on website", value=(ctx.bot.site_creds["website_url"] + "/TableDetails/%d" % newid), inline=False)
    #     if is984 != 984:
    #         warning = ("The total score of %d might be incorrect! Most tables should add up to 984 points"
    #                    % is984)
    #         e.add_field(name="Warning", value=warning, inline=False)

    #     e.set_image(url=tableurl)
    #     channel = ctx.guild.get_channel(channels[tier.upper()])

    #     tableMsg = await channel.send(embed=e)
        
    #     await API.post.setTableMessageId(newid, tableMsg.id)
    #     await embedded.delete()
    #     if channel == ctx.channel:
    #         await ctx.message.delete()
    #     else:
    #         await ctx.send("Successfully sent table to %s `(ID: %d)`" %
    #                        (tableMsg.jump_url, newid))
    #     strike_log = ctx.guild.get_channel(strike_log_channel)
    #     e = discord.Embed(title="Table names fixed")
    #     e.add_field(name="Old ID", value=tableID)
    #     e.add_field(name="New ID", value=newid)
    #     e.add_field(name="Updated by", value=ctx.author.mention, inline=False)
    #     if strike_log is not None:
    #         await strike_log.send(embed=e)

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
