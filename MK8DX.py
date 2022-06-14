import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
import asyncio

with open('./config.json', 'r') as cjson:
    config = json.load(cjson)

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents, application_id = config["application_id"])
bot = commands.Bot(command_prefix='!', case_insensitive=True, intents=intents,
                    tree = app_commands.CommandTree(client))
bot.config = config

initial_extensions = ['cogs.Updating', 'cogs.Tables', 'cogs.Admin', 'cogs.Restrictions']



with open('./credentials.json', 'r') as cjson:
    bot.site_creds = json.load(cjson)

@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await(await ctx.send("Your command is missing an argument: `%s`" %
                       str(error.param))).delete(delay=10)
        return
    if isinstance(error, commands.CommandOnCooldown):
        await(await ctx.send("This command is on cooldown; try again in %.0fs"
                       % error.retry_after)).delete(delay=5)
        return
    if isinstance(error, commands.MissingAnyRole):
        await(await ctx.send("You need one of the following roles to use this command: `%s`"
                             % (", ".join(error.missing_roles)))
              ).delete(delay=10)
        return
    if isinstance(error, commands.BadArgument):
        await(await ctx.send("BadArgument Error: `%s`" % error.args)).delete(delay=10)
        return
    if isinstance(error, commands.BotMissingPermissions):
        await(await ctx.send("I need the following permissions to use this command: %s"
                       % ", ".join(error.missing_perms))).delete(delay=10)
        return
    if isinstance(error, commands.NoPrivateMessage):
        await(await ctx.send("You can't use this command in DMs!")).delete(delay=5)
        return
    if isinstance(error, commands.BadUnionArgument):
        await(await ctx.send("Please use either a integer or mention a user")).delete(delay=10)
        return
    raise error

async def main():
    async with bot:
        for extension in initial_extensions:
            await bot.load_extension(extension)
        await bot.start(bot.config["token"])

asyncio.run(main())
