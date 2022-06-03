import discord
from discord.ext import commands

# check if user has any roles in the list of IDs
def check_role_list(ctx, check_roles):
    for role in check_roles:
        if ctx.author.get_role(role) is not None:
            return True
    return False

# check if user has reporter or staff roles
def check_reporter_roles(ctx):
    check_roles = ctx.bot.config["reporter_roles"] + ctx.bot.config["staff_roles"]
    return check_role_list(ctx, check_roles)
    
# check if user has staff roles
def check_staff_roles(ctx):
    check_roles = ctx.bot.config["staff_roles"]
    return check_role_list(ctx, check_roles)
    
# command version of check_reporter_roles; throws error if false
def command_check_reporter_roles(ctx):
    check_roles = ctx.bot.config["reporter_roles"] + ctx.bot.config["staff_roles"]
    if check_role_list(ctx, check_roles):
        return True
    error_roles = [ctx.guild.get_role(role).name for role in check_roles if ctx.guild.get_role(role) is not None]
    raise commands.MissingAnyRole(error_roles)

# command version of check_staff_roles; throws error if false
def command_check_staff_roles(ctx):
    check_roles = ctx.bot.config["staff_roles"]
    if check_role_list(ctx, check_roles):
        return True
    error_roles = [ctx.guild.get_role(role).name for role in check_roles if ctx.guild.get_role(role) is not None]
    raise commands.MissingAnyRole(error_roles)