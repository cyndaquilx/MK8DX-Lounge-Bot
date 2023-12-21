import discord

from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta

player_score = {}


class Make_table(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_whatchlist = {}
        self._remove_expired = self.remove_expired.start()


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot and "**Poll Ended!**" in message.content:
            self.channel_whatchlist[message.channel.id] = datetime.now()
            return

        if message.author.bot or message.channel.id not in self.channel_whatchlist:
            return

        if message.content.isdecimal() and 12 <= int(message.content) <= 180:
            player_score[message.author.display_name] = {"time": datetime.now(), "score": message.content}


    @tasks.loop(minutes=1)
    async def remove_expired(self):
        expired_player_date = datetime.now()-timedelta(minutes=30)
        expired_channel_date = datetime.now()-timedelta(hours=2)

        for player, data in list(player_score.items()):
            if data['time'] < expired_player_date:
                player_score.pop(player)

        for channel, date in list(self.channel_whatchlist.items()):
            if date < expired_channel_date:
                self.channel_whatchlist.pop(channel)


@app_commands.context_menu(name="Make table")
@app_commands.guilds(discord.Object(id=445404006177570829))
async def make_table(interaction: discord.Interaction, message: discord.Message):
    """setup the command to submit table"""

    if "**Poll Ended!**" not in message.content:
        return await interaction.response.send_message(content="invalid message", ephemeral=True)

    data = message.content.split("\n\n")[1]
    tier = data.split("Tier ")[1].split("**\n")[0]
    teams = data.split("\n")[1:]
    mogi_format = round(12/len(teams))
    players = []
    for team in teams:
        players += team.split(".` ")[1].split(" (")[0].split(", ")

    formated_players = ""
    for player in players:
        if player in player_score:
            formated_players += f"{player} {player_score[player]['score']}\n"
        else:
            formated_players += f"{player} 0\n"

    await interaction.response.send_message(content=f"!submit {mogi_format} {tier}\n{formated_players}")


async def setup(bot: commands.Bot):
    bot.tree.add_command(make_table)
    await bot.add_cog(Make_table(bot))