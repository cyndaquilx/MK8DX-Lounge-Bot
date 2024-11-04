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

    @commands.check(command_check_reporter_roles)
    @commands.command()
    async def submit(self, ctx, size:int, tier, *, data):
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

        table = TableBasic.from_text(size, tier, nameAPIchecks, scores, ctx.author.id)
        await submit_table(ctx, table)
       
async def setup(bot):
    await bot.add_cog(Tables(bot))
