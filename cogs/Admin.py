import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

import json

import API.post, API.get
import asyncio

from constants import place_MMRs, channels, getRank, ranks, placementRoleID, player_role_ID
from util.Leaderboards import get_leaderboard, get_leaderboard_slash
from models import ServerConfig
from custom_checks import leaderboard_autocomplete

class Admin(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        self.stopped = False

    @commands.has_any_role("Administrator")
    @commands.command(aliases=['pc'])
    async def placeEveryone(self, ctx):
        await ctx.send("working...")
        wb = openpyxl.load_workbook("s8Changes.xlsx", data_only=True)
        ws = wb["Sheet"]
        for i in range(1001, 20264):
            if(i % 100 == 0):
                await ctx.send(f"{i}/{20263}")
            name = ws[f"A{i}"].value
            mmr = ws[f"E{i}"].value
            success, player = await API.post.placePlayer(mmr, name)
            if success is False:
                print(f"{name} - {player}")
                continue
            await asyncio.sleep(0.05)
        await ctx.send("done")

    # old command when we completely remade roles, not used anymore
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

    # use this after all players have been placed on the website for new season
    @commands.has_any_role("Administrator")
    @commands.command()
    async def fixAllRoles(self, ctx: commands.Context):
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

    @commands.has_any_role("Administrator")
    @commands.command()
    async def startseason(self, ctx, seasonnum:int):
        for channel in ctx.guild.channels:
            #if channel.category_id in [445404698795573250, 876282435623608330, 1003118792794177568]:
            if channel.category_id in [445404698795573250]:
                await self.unlockdown(channel)
        await ctx.send(f"All tier chats have been unlocked. ENJOY SEASON {seasonnum}!! @everyone")
        
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
 

    @commands.command()
    async def countchannels(self, ctx: commands.Context):
        count = 0
        for _ in ctx.guild.channels:
            count += 1
        await ctx.send(count)

    @commands.command()
    @commands.is_owner()
    async def sync_server(self, ctx):
        await self.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
        await ctx.send("synced")

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx):
        await self.bot.tree.sync()
        await ctx.send("synced")

    @commands.command()
    @commands.is_owner()
    async def testcom(self, ctx):
        lb = get_leaderboard(ctx)
        await ctx.send(lb.player_role_id)

    # async def leaderboard_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    #     #ctx = await commands.Context.from_interaction(interaction)
    #     server_info: ServerConfig | None = interaction.client.config.servers.get(interaction.guild_id, None)
    #     if not server_info:
    #         return []
    #     choices = [app_commands.Choice(name=lb, value=lb) for lb in server_info.leaderboards]
    #     return choices
    
    @app_commands.guilds(741867051035000853)
    @app_commands.autocomplete(leaderboard=leaderboard_autocomplete)
    @app_commands.command()
    async def test_slash(self, interaction: discord.Interaction, leaderboard: Optional[str]):
        ctx = await commands.Context.from_interaction(interaction)
        lb = get_leaderboard_slash(ctx, leaderboard)
        await ctx.send("found lb")

async def setup(bot):
    await bot.add_cog(Admin(bot))
