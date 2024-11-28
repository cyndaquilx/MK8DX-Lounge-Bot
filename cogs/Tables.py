import discord
from discord.ext import commands
import re

import API.post, API.get

from custom_checks import command_check_reporter_roles, check_staff_roles
from models import TableBasic
from util import submit_table, delete_table, get_leaderboard
from datetime import datetime

class Tables(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.check(command_check_reporter_roles)
    @commands.command(aliases=['undo'])
    async def delete(self, ctx, table_id:int, *, reason=""):
        lb = get_leaderboard(ctx)
        table = await API.get.getTable(lb.website_credentials, table_id)
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
        await delete_table(ctx, lb, table, reason=reason)

    @commands.check(command_check_reporter_roles)
    @commands.command()
    async def submit(self, ctx: commands.Context, size:int, tier: str, *, data: str):
        lb = get_leaderboard(ctx)
        if size not in lb.valid_formats:
            await ctx.send(f"Your size is not valid. Correct sizes are: {lb.valid_formats}")
            return
        tier = tier.upper()
        if tier not in lb.tier_results_channels.keys():
            await ctx.send(f"Your tier is not valid. Correct tiers are: {list(lb.tier_results_channels.keys())}")
            return
        #functions for parsing lorenzi table data
        def isGps(scores:str):
            gps = re.split("[|+]", scores)
            for gp in gps:
                if gp.strip().isdigit() == False:
                    return False
        def get_gps(scores: str):
            gp_strings = re.split("[|+]", scores)
            gp_scores: list[int] = []
            for gp in gp_strings:
                gp_score = int(gp.strip())
                gp_scores.append(gp_score)
            # if there's only 1 gp per mogi for our lb,
            # just return the total sum
            if lb.gps_per_mogi == 1:
                return [sum(gp_scores)]
            return gp_scores

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
            
        # parse date from input if it exists
        date_pattern = r"#date (\d{4}-\d{2}-\d{2})"
        match = re.search(date_pattern, data)
        date = None
        if match:
            date_str = match.group(0).replace("#date ", "")
            date = datetime.strptime(date_str, "%Y-%m-%d")

        lines = filter(removeExtra, data.split("\n"))
        names = []
        scores: list[list[int]] = []
        for line in lines:
            # removes country flag brackets
            newline = re.sub(r"[\[].*?[\]]", "", line).split()
            names.append(" ".join(newline[0:len(newline)-1]))
            gps = newline[len(newline)-1]
            gp_scores = get_gps(gps)
            if len(gp_scores) != lb.gps_per_mogi:
                await ctx.send(f"One of your submitted scores has {len(gp_scores)} GPs but this leaderboard requires {lb.gps_per_mogi} GPs.")
                return
            scores.append(gp_scores)
        if len(names) != lb.players_per_mogi:
            await ctx.send(f"Your table does not contain {lb.players_per_mogi} valid score lines, try again!")
            return
        #checking names with the leaderboard API
        players = await API.get.getPlayers(lb.website_credentials, names)
        err_str = ""
        for i, player in enumerate(players):
            if player is None:
                err_str += f"{names[i]}\n"
        if len(err_str) > 0:
            await ctx.send(f"The following players cannot be found on the leaderboard:\n{err_str}")
            return
        correct_names = [p.name for p in players]
        table = TableBasic.from_text(size, tier, correct_names, scores, ctx.author.id, date)
        await submit_table(ctx, lb, table)
       
async def setup(bot):
    await bot.add_cog(Tables(bot))
