import discord
from discord.ext import commands

# check if user has any roles in the list of IDs
def check_role_list(member, check_roles):
    for role in check_roles:
        if member.get_role(role) is not None:
            return True
    return False

# check if user has reporter or staff roles
def check_reporter_roles(ctx):
    check_roles = (ctx.bot.server_config["reporter_roles"][str(ctx.guild.id)] +
        ctx.bot.server_config["staff_roles"][str(ctx.guild.id)] +
        ctx.bot.server_config["admin_roles"][str(ctx.guild.id)])
    return check_role_list(ctx.author, check_roles)
    
# check if user has staff roles
def check_staff_roles(ctx):
    check_roles = (ctx.bot.server_config["staff_roles"][str(ctx.guild.id)] +
        ctx.bot.server_config["admin_roles"][str(ctx.guild.id)])
    return check_role_list(ctx.author, check_roles)

# check if user is chat restricted
def check_chat_restricted_roles(bot, member):
    if str(member.guild.id) not in bot.server_config["chat_restricted_roles"].keys():
        return False
    check_roles = bot.server_config["chat_restricted_roles"][str(member.guild.id)]
    return check_role_list(member, check_roles)

# check if user is name restricted
def check_name_restricted_roles(ctx, member):
    check_roles = ctx.bot.server_config["name_restricted_roles"][str(member.guild.id)]
    return check_role_list(member, check_roles)
    
# command version of check_reporter_roles; throws error if false
def command_check_reporter_roles(ctx):
    check_roles = (ctx.bot.server_config["reporter_roles"][str(ctx.guild.id)] +
        ctx.bot.server_config["staff_roles"][str(ctx.guild.id)] +
        ctx.bot.server_config["admin_roles"][str(ctx.guild.id)])
    if check_role_list(ctx.author, check_roles):
        return True
    error_roles = [ctx.guild.get_role(role).name for role in check_roles if ctx.guild.get_role(role) is not None]
    raise commands.MissingAnyRole(error_roles)

# command version of check_staff_roles; throws error if false
def command_check_staff_roles(ctx):
    check_roles = (ctx.bot.server_config["staff_roles"][str(ctx.guild.id)] +
        ctx.bot.server_config["admin_roles"][str(ctx.guild.id)])
    if check_role_list(ctx.author, check_roles):
        return True
    error_roles = [ctx.guild.get_role(role).name for role in check_roles if ctx.guild.get_role(role) is not None]
    raise commands.MissingAnyRole(error_roles)

def command_check_admin_mkc_roles(ctx):
    check_roles = (ctx.bot.server_config["mkc_roles"][str(ctx.guild.id)] +
        ctx.bot.server_config["admin_roles"][str(ctx.guild.id)])
    if check_role_list(ctx.author, check_roles):
        return True
    error_roles = [ctx.guild.get_role(role).name for role in check_roles if ctx.guild.get_role(role) is not None]
    raise commands.MissingAnyRole(error_roles)

async def check_valid_name(ctx, name):
    if len(name) > 16:
        await ctx.send("Names can only be up to 16 characters! Please choose a different name")
        return False
    if len(name) < 2:
        await ctx.send("Names must be at least 2 characters long")
        return
    if name.startswith("_") or name.endswith("_"):
        await ctx.send("Nicknames cannot start or end with `_` (underscore)")
        return False
    if name.startswith(".") or name.endswith("."):
        await ctx.send("Nicknames cannot start or end with `.` (period)")
        return False
    allowed_characters = 'abcdefghijklmnopqrstuvwxyz._ -1234567890'
    for c in range(len(name)):
        if name[c].lower() not in allowed_characters:
            await ctx.send(f"The character {name[c]} is not allowed in nicknames!")
            return False
    return True