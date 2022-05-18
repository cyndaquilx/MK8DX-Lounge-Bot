import discord
from discord.ext import commands

import urllib
import json
import io
import re

import API.post, API.get

from constants import (channels, ranks, bot_channels)

class Tables(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S", "Reporter ‍")
    @commands.command()
    async def delete(self, ctx, tableID:int):
        table = await API.get.getTable(tableID)
        if table is False:
            await ctx.send("Table not found")
            return
        if 'authorId' in table.keys():
            authorid = table['authorId']
            if ctx.author.id != int(authorid):
                await ctx.send("You are not the author of this table!")
                return
        if 'verifiedOn' in table.keys():
            await ctx.send("This table has been updated already, so you can't delete it. If there's an error with the table, please contact a staff member.")
            return
        tier = table['tier']
        if 'tableMessageId' in table.keys():
            channel = ctx.guild.get_channel(channels[tier])
            deleteMsg = await channel.fetch_message(table['tableMessageId'])
            if deleteMsg is not None:
                await deleteMsg.delete()
        success = await API.post.deleteTable(tableID)
        if success is True:
            await ctx.send("Successfully deleted table with ID %d" % tableID)
        else:
            await ctx.send("Table not found: Error %d" % success)

        

    @commands.has_any_role("Administrator", "Moderator", "Updater", "Staff-S", "Reporter ‍")
    @commands.command()
    async def submit(self, ctx, size:int, tier, *, data):
        #basic parameter checks
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
                err_str += "%s\n" % names[i]
        if len(err_str) > 0:
            await ctx.send(err_str)
            return

            
        is984 = sum(scores)
        teamscores = []
        teamnames = []
        teamplayerscores = []
        for i in range(int(12/size)):
            teamscore = 0
            tnames = []
            pscores = []
            for j in range(size):
                teamscore += scores[i*size+j]
                tnames.append(nameAPIchecks[i*size+j])
                pscores.append(scores[i*size+j])
            teamscores.append(teamscore)
            teamnames.append(tnames)
            teamplayerscores.append(pscores)

        sortedScoresTeams = sorted(zip(teamscores, teamnames, teamplayerscores), reverse=True)
        sortedScores = [x for x, _, _ in sortedScoresTeams]
        sortedTeams = [x for _, x, _ in sortedScoresTeams]
        sortedpScores = [x for _, _, x in sortedScoresTeams]
        sortedNames = []
        tableScores = []
        placements = []
        for i in range(len(sortedScores)):
            sortedNames += sortedTeams[i]
            tableScores += sortedpScores[i]
            if i == 0:
                placements.append(1)
                continue
            if sortedScores[i] == sortedScores[i-1]:
                placements.append(placements[i-1])
                continue
            placements.append(i+1)

        base_url_lorenzi = "https://gb.hlorenzi.com/table.png?data="
        if size > 1:
            table_text = ("#title Tier %s %dv%d\n"
                          % (tier.upper(), size, size))
        else:
            table_text = ("#title Tier %s FFA\n"
                          % (tier.upper()))
        if size == 1:
            table_text += "FFA - Free for All #4A82D0\n"
        for i in range(int(12/size)):
            if size != 1:
                if i % 2 == 0:
                    teamcolor = "#1D6ADE"
                else:
                    teamcolor = "#4A82D0"
                table_text += "%d %s\n" % (placements[i], teamcolor)
            for j in range(size):
                index = size * i + j
                table_text += ("%s %d\n"
                               % (sortedTeams[i][j], sortedpScores[i][j]))

        url_table_text = urllib.parse.quote(table_text)
        image_url = base_url_lorenzi + url_table_text

        e = discord.Embed(title="Table")
        e.set_image(url=image_url)
        content = "Please react to this message with \U00002611 within the next 30 seconds to confirm the table is correct"
        if is984 != 984:
            warning = ("The total score of %d might be incorrect! Most tables should add up to 984 points"
                       % is984)
            e.add_field(name="Warning", value=warning)
        embedded = await ctx.send(content=content, embed=e)
        #ballot box with check emoji
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

        success, sentTable = await API.post.createTable(tier.upper(), sortedTeams, sortedpScores, ctx.author.id)
        if success is False:
            await ctx.send("An error occurred trying to send the table to the website!\n%s"
                           % sentTable)
            return
        newid = sentTable["id"]
        tableurl = ctx.bot.site_creds["website_url"] + sentTable["url"]

        e = discord.Embed(title="Mogi Table", colour=int("0A2D61", 16))

        e.add_field(name="ID", value=newid)
        e.add_field(name="Tier", value=tier.upper())
        e.add_field(name="Submitted by", value=ctx.author.mention)
        e.add_field(name="View on website", value=(ctx.bot.site_creds["website_url"] + "/TableDetails/%d" % newid))

        e.set_image(url=tableurl)
        channel = ctx.guild.get_channel(channels[tier.upper()])

        tableMsg = await channel.send(embed=e)
        
        await API.post.setTableMessageId(newid, tableMsg.id)
        await embedded.delete()
        if channel == ctx.channel:
            await ctx.message.delete()
        else:
            await ctx.send("Successfully sent table to %s `(ID: %d)`" %
                           (channel.mention, newid))
    

async def setup(bot):
    await bot.add_cog(Tables(bot))
