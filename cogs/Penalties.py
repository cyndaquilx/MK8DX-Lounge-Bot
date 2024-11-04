import discord
from discord import app_commands
from discord.ext import commands
import API.get, API.post
from models import LeaderboardConfig, Player
from util import update_roles, get_leaderboard, get_leaderboard_slash
from custom_checks import app_command_check_staff_roles, command_check_staff_roles
import custom_checks
from typing import Optional

class Penalties(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    penalty_group = app_commands.Group(name="penalty", description="Manage penalties", guild_ids=[741867051035000853, 445404006177570829])

    async def pen_channel(self, ctx: commands.Context, lb: LeaderboardConfig, player: Player, tier: str, reason: str | None, 
                          amount: int, channel: discord.TextChannel, is_anonymous: bool, is_strike: bool):
        pen, error = await API.post.createPenalty(lb.website_credentials, player.name, abs(amount), is_strike)
        if pen is None:
            await ctx.send(f"An error occurred while penalizing {player.name}:\n{error}")
            return
        embed_title = "Penalty added"
        if is_strike:
            embed_title = "Penalty + strike added"
        tier = tier.upper()
        e = discord.Embed(title=embed_title)
        e.add_field(name="Player", value=pen.player_name, inline=False)
        e.add_field(name="Amount", value="-%d" % abs(amount))
        e.add_field(name="ID", value=pen.id)
        e.add_field(name="Tier", value=tier)
        if not is_anonymous:
            e.add_field(name="Given by", value=ctx.author.mention)
        if reason:
            e.add_field(name="Reason", value=reason, inline=False)
        if is_strike:
            recent_strikes, error = await API.get.getStrikes(lb.website_credentials, player.name)
            if recent_strikes:
                reverse_order = recent_strikes[::-1][:6] # get last 6 strikes only to prevent msg getting too long
                strike_str = ""
                for i, pen in enumerate(reverse_order):
                    date_formatted = discord.utils.format_dt(pen.awarded_on, style="d")
                    date_relative = discord.utils.format_dt(pen.awarded_on, "R")
                    strike_str += f"{date_formatted} ({date_relative})\n"
                    # add a divider for strikes counting towards the current limit
                    # ex. if we have 5 strikes, we are 2 strikes towards next limit
                    # so on the 2nd strike, i = 1 < 3, 1+1%3 == 5%3
                    if i < 3 and (i+1) % 3 == len(recent_strikes) % 3 and len(recent_strikes) > 3:
                        strike_str += "----------\n"
                if len(recent_strikes):
                    e.add_field(name="Strikes", value=strike_str, inline=False)
        rank_change = await update_roles(ctx, lb, pen.player_name, pen.prev_mmr, pen.new_mmr)
        pen_msg = await channel.send(embed=e, content=rank_change)
        member = ctx.guild.get_member(player.discord_id)
        if member:
            try:
                if not is_anonymous:
                    # change from mention to name because we are in DMs
                    e.set_field_at(4, name='Given by', value=ctx.author.display_name)
                if is_strike:
                    dm_content = "You received a strike in 150cc Lounge:"
                else:
                    dm_content = "You received a penalty in 150cc Lounge:"
                await member.send(embed=e, content=dm_content)
            except Exception as ex:
                pass
        updating_log = ctx.guild.get_channel(lb.updating_log_channel)
        if updating_log:
            if is_anonymous:
                e.add_field(name="Given by", value=ctx.author.mention)
            else:
                e.set_field_at(4, name='Given by', value=ctx.author.mention)
            await updating_log.send(embed=e, content=rank_change)
        if ctx.channel.id == channel.id:
            await ctx.message.delete()
        else:
            await ctx.send(f"Added -{abs(amount)} penalty to {pen.player_name} in {pen_msg.jump_url} (ID: {pen.id})")

    async def add_penalty(self, ctx: commands.Context, lb: LeaderboardConfig, amount:int, tier: str, names: list[str], reason: str | None, is_anonymous=False, is_strike=False):
        tier = tier.upper()
        if tier not in lb.tier_results_channels.keys():
            await ctx.send(f"Your tier is not valid! Valid tiers are: {list(lb.tier_results_channels.keys())}")
            return
        if abs(amount) > 200:
            await ctx.send("Individual penalties can only be 200 points or lower")
            return
        channel = ctx.guild.get_channel(lb.tier_results_channels[tier])
        players: list[Player] = []
        for name in names:
            if name.isdigit():
                player = await API.get.getPlayerFromDiscordNew(lb.website_credentials, name)
                if player is None:
                    await ctx.send(f"The following player could not be found: {name}")
                    return
                players.append(player)
            else:
                player = await API.get.getPlayerNew(lb.website_credentials, name)
                if player is None:
                    await ctx.send(f"The following player could not be found: {name}")
                    return
                players.append(player)
        for player in players:
            await self.pen_channel(ctx, lb, player, tier, reason, amount, channel, is_anonymous, is_strike)

    async def parse_and_add_penalty(self, ctx: commands.Context, lb: LeaderboardConfig, amount:int, tier, args: str, is_anonymous=False, is_strike=False):
        split_args = args.split(";")
        names = [s.strip() for s in split_args[0].split(",")]
        if len(set(names)) < len(names):
            await ctx.send("There is at least one duplicate name in your input, try again")
            return
        reason = None
        if len(split_args) > 1:
            reason = split_args[1].strip()
        await self.add_penalty(ctx, lb, amount, tier, names, reason, is_anonymous, is_strike)

    @penalty_group.command(name="new")
    @app_commands.check(app_command_check_staff_roles)
    @app_commands.autocomplete(leaderboard=custom_checks.leaderboard_autocomplete)
    async def penalty_slash(self, interaction: discord.Interaction, amount:app_commands.Range[int, 1, 200], tier:str, names: str, 
                                reason:str | None, leaderboard: Optional[str], strike: bool = False, anonymous: bool = False):
        ctx = await commands.Context.from_interaction(interaction)
        lb = get_leaderboard_slash(ctx, leaderboard)
        parsed_names = [n.strip() for n in names.split(",")]
        await self.add_penalty(ctx, lb, amount, tier, parsed_names, reason, anonymous, strike)

    @penalty_group.command(name="strike")
    @app_commands.check(app_command_check_staff_roles)
    @app_commands.autocomplete(leaderboard=custom_checks.leaderboard_autocomplete)
    async def strike_slash(self, interaction: discord.Interaction, amount:app_commands.Range[int, 1, 200], tier:str, names: str, 
                                reason:str | None, leaderboard: Optional[str], anonymous: bool = False):
        ctx = await commands.Context.from_interaction(interaction)
        lb = get_leaderboard_slash(ctx, leaderboard)
        parsed_names = [n.strip() for n in names.split(",")]
        await self.add_penalty(ctx, lb, amount, tier, parsed_names, reason, anonymous, True)

    @commands.check(command_check_staff_roles)
    @commands.command(name="penalty", aliases=['pen'])
    async def penalty_text(self, ctx, amount:int, tier, *, args):
        lb = get_leaderboard(ctx)
        await self.parse_and_add_penalty(ctx, lb, amount, tier, args)

    @commands.check(command_check_staff_roles)
    @commands.command(name="anonymousPenalty", aliases=['apen', 'apenalty'])
    async def penalty_anonymous_text(self, ctx, amount:int, tier, *, args):
        lb = get_leaderboard(ctx)
        await self.parse_and_add_penalty(ctx, lb, amount, tier, args, is_anonymous=True)

    @commands.check(command_check_staff_roles)
    @commands.command(name="strike", aliases=['str'])
    async def strike_text(self, ctx, amount:int, tier, *, args):
        lb = get_leaderboard(ctx)
        await self.parse_and_add_penalty(ctx, lb, amount, tier, args, is_strike=True)

    @commands.check(command_check_staff_roles)
    @commands.command(name="anonymousStrike", aliases=['astr', 'astrike'])
    async def strike_anonymous_text(self, ctx, amount:int, tier, *, args):
        lb = get_leaderboard(ctx)
        await self.parse_and_add_penalty(ctx, lb, amount, tier, args, is_strike=True, is_anonymous=True)

    async def delete_penalty(self, ctx: commands.Context, lb: LeaderboardConfig, pen_id: int, reason: str | None):
        success, error = await API.post.deletePenalty(lb.website_credentials, pen_id)
        if success is True:
            await ctx.send(f"Successfully deleted penalty ID {pen_id}")
        else:
            await ctx.send(f"An error occurred: {error}")
            return
        e = discord.Embed(title="Deleted Penalty")
        e.add_field(name="Penalty ID", value=pen_id)
        e.add_field(name="Removed by", value=ctx.author.mention)
        e.add_field(name="Removed in", value=ctx.channel.mention)
        if reason:
            e.add_field(name="Reason", value=reason, inline=False)
        updating_log = ctx.guild.get_channel(lb.updating_log_channel)
        if updating_log:
            await updating_log.send(embed=e)

    @commands.check(command_check_staff_roles)
    @commands.command(name="deletePenalty")
    async def delete_penalty_text(self, ctx, pen_id:int, *, reason=None):
        lb = get_leaderboard(ctx)
        await self.delete_penalty(ctx, lb, pen_id, reason)

    @penalty_group.command(name="delete")
    @app_commands.check(app_command_check_staff_roles)
    @app_commands.autocomplete(leaderboard=custom_checks.leaderboard_autocomplete)
    async def delete_penalty_slash(self, interaction: discord.Interaction, pen_id: int, reason: Optional[str], leaderboard: Optional[str]):
        ctx = await commands.Context.from_interaction(interaction)
        lb = get_leaderboard_slash(ctx, leaderboard)
        await self.delete_penalty(ctx, lb, pen_id, reason)

async def setup(bot):
    await bot.add_cog(Penalties(bot))