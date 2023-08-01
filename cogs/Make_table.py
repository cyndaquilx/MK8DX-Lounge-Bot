import discord
import re

from discord import app_commands
from discord.ext import commands

player_score = {}


class Make_table(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or "tier" not in message.channel.name or "results" in message.channel.name:
            return

        if message.content.isdecimal() and 12 <= int(message.content) <= 180:
            player_score[message.author.display_name] = message.content


@app_commands.context_menu(name="Make table")
@app_commands.guilds(discord.Object(id=445404006177570829))
async def make_table(interaction: discord.Interaction, message: discord.Message):
    """setup the command to submit table"""

    if "**Poll Ended!**" not in message.content:
        return await interaction.response.send_message(content="invalid message", ephemeral=True)

    player_data = message.content.split("!scoreboard ")[1]
    player_count = player_data[:2]
    player_list = player_data[2:].replace("`", '').split(", ")
    formated_players = ""
    tier = re.split("-|_", message.channel.name)[1]

    for player in player_list:
        if player in player_score:
            formated_players += f"{player} {player_score[player]}\n"
            player_score.pop(player)
        else:
            formated_players += f"{player} 0\n"

    await interaction.response.send_message(content=f"!submit {str(round(12/int(player_count)))} {tier}\n{formated_players}")


async def setup(bot: commands.Bot):
    bot.tree.add_command(make_table)
    await bot.add_cog(Make_table(bot))