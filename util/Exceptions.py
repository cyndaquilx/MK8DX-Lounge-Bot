from discord.ext.commands import CommandError
from discord.app_commands import AppCommandError

class LeaderboardNotFoundException(CommandError, AppCommandError):
    def __init__(self):
        pass

class GuildNotFoundException(CommandError, AppCommandError):
    def __init__(self):
        pass