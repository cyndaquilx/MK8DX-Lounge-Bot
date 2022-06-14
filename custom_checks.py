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

def check_name_restricted_roles(ctx, member):
    check_roles = ctx.bot.server_config["name_restricted_roles"][str(ctx.guild.id)]
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