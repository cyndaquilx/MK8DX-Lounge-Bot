import discord
from discord.ext import commands

import urllib
import json
import io
import re

import API.post, API.get

from constants import (channels, ranks, bot_channels, getRank, findmember, strike_log_channel)
from custom_checks import command_check_reporter_roles, check_staff_roles, command_check_staff_roles, yes_no_check
from models import TableBasic
from util import submit_table, delete_table

class Tables(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.check(command_check_reporter_roles)
    @commands.command(aliases=['undo'])
    async def delete(self, ctx, table_id:int, *, reason=""):
        table = await API.get.getTableClass(table_id)
        if table is None:
            await ctx.send("Table not found")
            return
        # players that aren't lounge staff can't delete other people's tables or already updated tables
        if not check_staff_roles(ctx):
            if table.verified_on:
                await ctx.send("This table has been updated already, so you can't delete it. If there's an error with the table, please contact a staff member.")
                return
            if ctx.author.id != table.author_id:
                await ctx.send("You are not the author of this table!")
                return
        await delete_table(ctx, table, reason=reason)
        # rank_changes = ""
        # if table.verified_on:
        #     for team in table.teams:
        #         for score in team.scores:
        #             # if this table was one where the player ranked up/down, we want to put them in their previous rank
        #             old_rank = getRank(score.new_mmr)
        #             new_rank = getRank(score.prev_mmr)
        #             if old_rank == new_rank:
        #                 continue
        #             member = ctx.guild.get_member(int(score.player.discord_id))
        #             # don't want to mention people in ticket threads and add them to it
        #             if member and not hasattr(ctx.channel, 'parent_id'):
        #                 player_name = member.mention
        #             else:
        #                 player_name = score.player.name
        #             emoji = ranks[new_rank]["emoji"]
        #             rank_changes += f"{player_name} -> {emoji}\n"
        #             old_role = ctx.guild.get_role(ranks[old_rank]["roleid"])
        #             new_role = ctx.guild.get_role(ranks[new_rank]["roleid"])
        #             if member:
        #                 if old_role and old_role in member.roles:
        #                     await member.remove_roles(old_role)
        #                 if new_role and new_role not in member.roles:
        #                     await member.add_roles(new_role)
        # channel = ctx.guild.get_channel(channels[table.tier])
        # if table.table_message_id:
        #     try:
        #         table_msg = await channel.fetch_message(table.table_message_id)
        #         if table_msg is not None:
        #             await table_msg.delete()
        #     except:
        #         pass
        # if table.update_message_id:
        #     try:
        #         update_msg = await channel.fetch_message(table.update_message_id)
        #         if update_msg is not None:
        #             await update_msg.delete()
        #     except:
        #         pass
        # success = await API.post.deleteTable(table_id)
        # if success is True:
        #     await ctx.send(f"Successfully deleted table with ID {table_id}\n{rank_changes}")
        # else:
        #     await ctx.send(f"Table not found: Error {success}")
        # e = discord.Embed(title="Deleted Table")
        # e.add_field(name="Table ID", value=table_id)
        # e.add_field(name="Removed by", value=ctx.author.mention)
        # e.add_field(name="Removed in", value=ctx.channel.mention)
        # if len(reason):
        #     e.add_field(name="Reason", value=reason, inline=False)
        # strike_log = ctx.guild.get_channel(strike_log_channel)
        # if strike_log is not None:
        #     await strike_log.send(embed=e)

    #@commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S", "Reporter ‍")
    # @commands.check(command_check_reporter_roles)
    # @commands.command(aliases=['undo'])
    # async def delete(self, ctx, tableID:int, *, reason=""):
    #     table = await API.get.getTable(tableID)
    #     if table is False:
    #         await ctx.send("Table not found")
    #         return
    #     # players that aren't lounge staff can't delete other people's tables or already updated tables
    #     if not check_staff_roles(ctx):
    #         if 'authorId' in table.keys():
    #             authorid = table['authorId']
    #             if ctx.author.id != int(authorid):
    #                 await ctx.send("You are not the author of this table!")
    #                 return
    #         else:
    #             await ctx.send("You are not the author of this table!")
    #             return
    #         if 'verifiedOn' in table.keys():
    #             await ctx.send("This table has been updated already, so you can't delete it. If there's an error with the table, please contact a staff member.")
    #             return
    #     tier = table['tier']
    #     rankChanges = ""
    #     if 'verifiedOn' in table.keys():
    #         names = []
    #         oldMMRs = []
    #         newMMRs = []
    #         peakMMRs = []
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
    #         await ctx.send("Table not found: Error %d" % success)
    #     e = discord.Embed(title="Deleted Table")
    #     e.add_field(name="Table ID", value=tableID)
    #     e.add_field(name="Removed by", value=ctx.author.mention)
    #     e.add_field(name="Removed in", value=ctx.channel.mention)
    #     if len(reason):
    #         e.add_field(name="Reason", value=reason, inline=False)
    #     strike_log = ctx.guild.get_channel(strike_log_channel)
    #     if strike_log is not None:
    #         await strike_log.send(embed=e)

    @commands.check(command_check_reporter_roles)
    @commands.command()
    async def submit(self, ctx, size:int, tier, *, data):
        if ctx.guild.id != ctx.bot.config["server"]:
            await ctx.send("You cannot use this command in this server!")
            return
        VALID_SIZES = [1, 2, 3, 4, 6]
        if size not in VALID_SIZES:
            await ctx.send("Your size is not valid. Correct sizes are: %s"
                           % (VALID_SIZES))
            return
        if tier.upper() not in channels.keys():
            await ctx.send("Your tier is not valid. Correct tiers are: %s"
                           % (list(channels.keys())))
            return
        #functions for parsing lorenzi table data
        def isGps(scores:str):
            gps = re.split("[|+]", scores)
            for gp in gps:
                if gp.strip().isdigit() == False:
                    return False
        def sumGps(scores:str):
            gps = re.split("[|+]", scores)
            sum = 0
            for gp in gps:
                sum += int(gp.strip())
            return sum
        def removeExtra(line):
            splitLine = line.split()
            if line.strip() == "":
                return False
            if len(splitLine) == 1:
                return False
            scores = splitLine[len(splitLine)-1]
            if scores.isdigit() == False and isGps(scores) == False:
                return False
            else:
                return True
            
        lines = filter(removeExtra, data.split("\n"))
        names = []
        scores = []
        for line in lines:
            # removes country flag brackets
            newline = re.sub("[\[].*?[\]]", "", line).split()
            names.append(" ".join(newline[0:len(newline)-1]))
            gps = newline[len(newline)-1]
            scores.append(sumGps(gps))
        if len(names) != 12:
            await ctx.send("Your table does not contain 12 valid score lines, try again!")
            return
        #checking names with the leaderboard API
        nameAPIchecks = await API.get.checkNames(names)
        err_str = ""
        for i in range(12):
            if nameAPIchecks[i] is False:
                if len(err_str) == 0:
                    err_str += "The following players cannot be found on the leaderboard:\n"
                err_str += f"{names[i]}\n"
        if len(err_str) > 0:
            await ctx.send(err_str)
            return

        table = TableBasic.from_text(size, tier, names, scores, ctx.author.id)
        await submit_table(ctx, table)
        # total = table.score_total()

        # e = discord.Embed(title="Table")
        # e.set_image(url=table.get_lorenzi_url())
        # if total != 984:
        #     e.add_field(name="Warning", value=f"The total score of {total} might be incorrect! Most tables should add up to 984 points")
        # content = "Please react to this message with \U00002611 within the next 30 seconds to confirm the table is correct"
        # embedded = await ctx.send(content=content, embed=e)
        # if not await yes_no_check(ctx, embedded):
        #     return
        
        # sent_table, error = await API.post.createTableFromClass(table)
        # if sent_table is None:
        #     await ctx.send(f"An error occurred trying to send the table to the website!\n{error}")
        #     return
        # e = discord.Embed(title="Mogi Table", colour=int("0A2D61", 16))
        # e.add_field(name="ID", value=sent_table.id)
        # e.add_field(name="Tier", value=sent_table.tier)
        # e.add_field(name="Submitted by", value=ctx.author.mention)
        # e.add_field(name="Submitted from", value=ctx.channel.jump_url)
        # e.add_field(name="View on website", value=(ctx.bot.site_creds["website_url"] + "/TableDetails/%d" % sent_table.id), inline=False)
        # if total != 984:
        #     warning = f"The total score of {total} might be incorrect! Most tables should add up to 984 points"
        #     e.add_field(name="Warning", value=warning, inline=False)

        # table_image_url = ctx.bot.site_creds["website_url"] + sent_table.get_table_image_url()
        # e.set_image(url=table_image_url)
        # channel = ctx.guild.get_channel(channels[tier.upper()])

        # tableMsg = await channel.send(embed=e)
        
        # await API.post.setTableMessageId(sent_table.id, tableMsg.id)
        # await embedded.delete()
        # if channel == ctx.channel:
        #     await ctx.message.delete()
        # else:
        #     await ctx.send(f"Successfully sent table to {tableMsg.jump_url} `(ID: {sent_table.id})`")

    #@commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S", "Reporter ‍")
    # @commands.check(command_check_reporter_roles)
    # @commands.command()
    # async def submit(self, ctx, size:int, tier, *, data):
    #     #basic parameter checks
    #     if ctx.guild.id != ctx.bot.config["server"]:
    #         await ctx.send("You cannot use this command in this server!")
    #         return
    #     VALID_SIZES = [1, 2, 3, 4, 6]
    #     if size not in VALID_SIZES:
    #         await ctx.send("Your size is not valid. Correct sizes are: %s"
    #                        % (VALID_SIZES))
    #         return

    #     if tier.upper() not in channels.keys():
    #         await ctx.send("Your tier is not valid. Correct tiers are: %s"
    #                        % (list(channels.keys())))
    #         return
    #     #functions for parsing lorenzi table data
    #     def isGps(scores:str):
    #         gps = re.split("[|+]", scores)
    #         for gp in gps:
    #             if gp.strip().isdigit() == False:
    #                 return False
    #     def sumGps(scores:str):
    #         gps = re.split("[|+]", scores)
    #         sum = 0
    #         for gp in gps:
    #             sum += int(gp.strip())
    #         return sum
    #     def removeExtra(line):
    #         splitLine = line.split()
    #         if line.strip() == "":
    #             return False
    #         if len(splitLine) == 1:
    #             return False
    #         scores = splitLine[len(splitLine)-1]
    #         if scores.isdigit() == False and isGps(scores) == False:
    #             return False
    #         else:
    #             return True

    #     lines = filter(removeExtra, data.split("\n"))
    #     names = []
    #     scores = []
    #     for line in lines:
    #         # removes country flag brackets
    #         newline = re.sub("[\[].*?[\]]", "", line).split()
    #         names.append(" ".join(newline[0:len(newline)-1]))
    #         gps = newline[len(newline)-1]
    #         scores.append(sumGps(gps))
    #     if len(names) != 12:
    #         await ctx.send("Your table does not contain 12 valid score lines, try again!")
    #         return
    #     #checking names with the leaderboard API
    #     nameAPIchecks = await API.get.checkNames(names)
    #     err_str = ""
    #     for i in range(12):
    #         if nameAPIchecks[i] is False:
    #             if len(err_str) == 0:
    #                 err_str += "The following players cannot be found on the leaderboard:\n"
    #             err_str += f"{names[i]}\n"
    #     if len(err_str) > 0:
    #         await ctx.send(err_str)
    #         return

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
    #             tnames.append(nameAPIchecks[i*size+j])
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

    #     success, sentTable = await API.post.createTable(tier.upper(), sortedTeams, sortedpScores, ctx.author.id)
    #     if success is False:
    #         await ctx.send("An error occurred trying to send the table to the website!\n%s"
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
    

async def setup(bot):
    await bot.add_cog(Tables(bot))
