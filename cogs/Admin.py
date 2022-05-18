import discord
from discord.ext import commands

import openpyxl

import API.post, API.get
import asyncio
import aiohttp

from constants import place_MMRs, channels, getRank, ranks, placementRoleID

class Admin(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    #@commands.has_any_role("Administrator")
    #@commands.command(aliases=['pc'])
    async def placeEveryone(self, ctx):
        await ctx.send("working...")
        wb = openpyxl.load_workbook("s6Changes.xlsx", data_only=True)
        ws = wb["Sheet"]
        for i in range(10000, 13556):
            if(i % 100 == 0):
                await ctx.send(f"{i}/{13554}")
            name = ws[f"A{i}"].value
            mmr = ws[f"E{i}"].value
            success, player = await API.post.placePlayer(mmr, name)
            if success is False:
                print(f"{name} - {player}")
                continue
            await asyncio.sleep(0.05)
        await ctx.send("done")

    #@commands.has_any_role("Administrator")
    #@commands.command(aliases=['all'])
    async def addAll(self, ctx):
        apiplayers = await API.get.getPlayerList()
        players = apiplayers['players']
        print('added:')
        for player in players:
            if 'discordId' not in player.keys():
                continue
            if 'mmr' not in player.keys():
                continue
            rank = getRank(player['mmr'])
            role = ctx.guild.get_role(ranks[rank]['roleid'])
            member = ctx.guild.get_member(int(player['discordId']))
            if member is None:
                continue
            for mrole in member.roles:
                if mrole.id == role.id:
                    continue
            await member.add_roles(role)
            print(f"{player['name']} - {role.name}")

    async def unlockdown(self, channel:discord.TextChannel):
        overwrite = channel.overwrites_for(channel.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)
        await channel.send("Unlocked " + channel.mention)

    #@commands.has_any_role("Administrator")
    #@commands.command()
    async def fixAllRoles(self, ctx):
        i = 0
        for member in ctx.guild.members:
            i+=1
            if i % 100 == 0:
                await ctx.send(f"{i}/{len(ctx.guild.members)}")
            playerRoles = []
            for role in member.roles:
                for rank in ranks.values():
                    if role.id == rank['roleid']:
                        playerRoles.append(role)
                    if role.id == placementRoleID:
                        playerRoles.append(role)

            player = await API.get.getPlayerFromDiscord(member.id)
            if player is None:
                for role in playerRoles:
                    try:
                        await member.remove_roles(role)
                    except Exception as e:
                        print(e)
                        continue
                continue
            
            if 'mmr' not in player.keys():
                role = member.guild.get_role(placementRoleID)
            else:
                rank = getRank(player['mmr'])
                role = member.guild.get_role(ranks[rank]['roleid'])

            for currRole in playerRoles:
                if currRole.id != role.id:
                    try:
                        await member.remove_roles(currRole)
                    except Exception as e:
                        print(e)
            if role not in playerRoles:
                try:
                    await member.add_roles(role)
                except Exception as e:
                    print(e)
        await ctx.send("done")
            
            

    #@commands.has_any_role("Administrator")
    #@commands.command()
    async def startseason(self, ctx):
        for channel in ctx.guild.channels:
            if channel.category_id == 445404698795573250 or channel.category_id == 876282435623608330:
                await self.unlockdown(channel)
        await ctx.send("All tier chats have been unlocked. ENJOY SEASON 6!! @everyone")
        
    #@commands.has_any_role("Administrator")
    #@commands.command()
    async def checkNumDiscords(self, ctx):
        apiplayers = await API.get.getPlayerList()
        players = apiplayers['players']
        count = 0
        for player in players:
            if 'discordId' in player.keys():
                count += 1
        await ctx.send(f"{count}/{len(players)} players have Discord accounts added, which is {(count/len(players)*100):.2f}% of the players in the database")
 
    #@commands.has_any_role("Administrator")
    #@commands.command()
    async def regmkc(self, ctx):
        await ctx.send("working...")
        wb = openpyxl.load_workbook("tourney bonus.xlsx", data_only=True)
        ws = wb["Sheet1"]
        base_url = "https://mariokartcentral.com/mkc/api/registry/players/"
        connector=aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            for i in range(2, 745):
                full_url = base_url + str(ws[f"A{i}"].value)
                async with session.get(full_url) as resp:
                    info = await resp.json()
                    ws[f"E{i}"] = info["user_id"]
                    if i % 100 == 0:
                        await ctx.send(i)
                    await asyncio.sleep(0.1)
        wb.save("tourney bonus.xlsx")
        await ctx.send("done")

    #@commands.has_any_role("Administrator")
    #@commands.command()
    async def getname(self, ctx):
        await ctx.send("working...")
        wb = openpyxl.load_workbook("tourney bonus.xlsx", data_only=True)
        ws = wb["Sheet1"]
        for i in range(2, 745):
            mkcid = ws[f"E{i}"].value
            p = await API.get.getPlayerFromMKC(mkcid)
            if p is not None:
                ws[f"F{i}"] = p['name']
            if i % 100 == 0:
                await ctx.send(i)
            await asyncio.sleep(0.1)
        wb.save("tourney bonus.xlsx")
        await ctx.send("done")

    #@commands.has_any_role("Administrator")
    #@commands.command()
    async def givebonuses(self, ctx):
        wb = openpyxl.load_workbook("tourney bonus.xlsx", data_only=True)
        ws = wb["Sheet1"]
        for i in range(429, 737):
            loungename = ws[f"F{i}"].value
            bonus = ws[f"D{i}"].value
            p = await API.get.getPlayer(loungename)
            a, b = await API.post.createBonus(loungename, bonus)
            if a is False:
                await ctx.send(f"{loungename}: {b}")
            else:
                ws[f"G{i}"] = "yes"
                mmr1 = p["mmr"]
                mmr2 = mmr1 + bonus
                ws[f"H{i}"] = mmr1
                ws[f"I{i}"] = mmr2
                oldRank = getRank(mmr1)
                newRank = getRank(mmr2)
                if oldRank != newRank:
                    ws[f"J{i}"] = "yes"
                    if 'discordId' in p.keys():
                        member = ctx.guild.get_member(int(p['discordId']))
                        oldRole = ctx.guild.get_role(ranks[oldRank]["roleid"])
                        newRole = ctx.guild.get_role(ranks[newRank]["roleid"])
                        if member is not None and oldRole is not None and newRole is not None:
                            if oldRole in member.roles:
                                await member.remove_roles(oldRole)
                            if newRole not in member.roles:
                                await member.add_roles(newRole)
                            ws[f"K{i}"] = "yes"
            if i % 100 == 0:
                await ctx.send(i)
            await asyncio.sleep(0.1)
        wb.save("tourney bonus.xlsx")
        await ctx.send("done")

    @commands.command()
    async def countchannels(self, ctx):
        count = 0
        for channel in ctx.guild.channels:
            count += 1
        await ctx.send(count)
    
async def setup(bot):
    await bot.add_cog(Admin(bot))
