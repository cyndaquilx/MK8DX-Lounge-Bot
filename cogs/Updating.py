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

from custom_checks import (yes_no_check, check_staff_roles, command_check_reporter_roles, command_check_staff_roles, check_name_restricted_roles, check_valid_name, command_check_admin_mkc_roles, command_check_all_staff_roles)
import custom_checks

from typing import Union, Optional
from util import submit_table, delete_table, get_server_config, get_leaderboard, get_leaderboard_slash
from models import ServerConfig, LeaderboardConfig

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

    #adds correct roles and nicknames for players when they join server
    @commands.Cog.listener(name='on_member_join')
    async def on_member_join(self, member):
        if member.bot:
            return

        server_info: ServerConfig = self.bot.config.servers.get(member.guild.id, None)
        if not server_info:
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
        for server_id in self.bot.config.servers:
            server = self.bot.get_guild(server_id)
            if server is None:
                continue
            member = server.get_member(before.id)
            if member is None:
                continue
            if member.nick is not None:
                continue
            if before.display_name == after.display_name:
                continue
            player = await API.get.getPlayerFromDiscord(before.id)
            if player is None:
                continue
            if player['name'] != after.display_name:
                await member.edit(nick=player['name'])
        
        

async def setup(bot):
    await bot.add_cog(Updating(bot))
