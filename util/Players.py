import discord
from discord.ext import commands
from models import LeaderboardConfig, Player
from custom_checks import find_member
import API.get, API.post

async def give_placement_role_new(ctx: commands.Context, lb: LeaderboardConfig, player: Player, placeMMR: int):
    new_role_id = lb.get_rank(placeMMR).role_id
    new_role = ctx.guild.get_role(new_role_id)
    if player.discord_id:
        await ctx.send("Player does not have a discord ID on the site, please give them one to give them placement roles")
        return
    member = ctx.guild.get_member(int(player.discord_id))
    if member is None:
        await ctx.send(f"Couldn't find member {player.name}, please give them roles manually")
        return
    for role in member.roles:
        for rank in lb.ranks.values():
            if role.id == rank.role_id:
                await member.remove_roles(role)
        if role.id == lb.placement_role_id:
            await member.remove_roles(role)
    if new_role not in member.roles:
        await member.add_roles(new_role)
    await ctx.send(f"Managed to find member {member.display_name} and edit their roles")

async def place_player_with_mmr_new(ctx: commands.Context, lb: LeaderboardConfig, mmr: int, name: str, force=False):
    success, error = await API.post.placePlayerNew(lb.website_credentials, mmr, name, force=force)
    if success is False:
        await ctx.send(f"An error occurred while trying to place the player: {error}")
        return False
    player = await API.get.getPlayerNew(lb.website_credentials, name)
    await give_placement_role_new(ctx, lb, player, mmr)
    await ctx.send(f"Successfully placed {player.name} with {mmr} MMR")
    if force:
        e = discord.Embed(title="Player force placed")
        e.add_field(name="Player", value=player.name, inline=False)
        e.add_field(name="MMR", value=mmr)
        if player.discord_id:
            e.add_field(name="Mention", value=f"<@{player.discord_id}>")
        e.add_field(name="Placed by", value=ctx.author.mention, inline=False)
        updating_log = ctx.guild.get_channel(lb.updating_log_channel)
        if updating_log:
            await updating_log.send(embed=e)
    return True

async def update_roles(ctx: commands.Context, lb: LeaderboardConfig, name: str, oldMMR:int, newMMR:int):
    old_rank = lb.get_rank(oldMMR)
    new_rank = lb.get_rank(newMMR)
    rank_changes = ""
    if old_rank != new_rank:
        member = find_member(ctx, name, old_rank.role_id)
        if member is not None:
            memName = member.mention
        else:
            memName = name
        rank_changes += f"{memName} -> {new_rank.emoji}\n"
        old_role = ctx.guild.get_role(old_rank.role_id)
        new_role = ctx.guild.get_role(new_rank.role_id)
        if member:
            if old_role and old_role in member.roles:
                await member.remove_roles(old_role)
            if new_role and new_role in member.roles:
                await member.add_roles(new_role)
    return rank_changes