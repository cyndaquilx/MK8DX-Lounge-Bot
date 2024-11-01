from discord.ext.commands import CommandError

class LeaderboardNotFoundException(CommandError):
    def __init__(self, leaderboard: str):
        self.leaderboard = leaderboard

class GuildNotFoundException(CommandError):
    def __init__(self):
        pass