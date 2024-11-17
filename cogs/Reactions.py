import discord
from discord.ext import commands
from models import ServerConfig

class Reactions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener(name='on_reaction_add')
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        if user.bot:
            return
        if reaction.message.author.bot:
            return
        
        server_info: ServerConfig = self.bot.config.servers.get(reaction.message.guild.id, None)
        if not server_info:
            return
        reaction_channel_id = server_info.reaction_log_channel
        channel = reaction.message.guild.get_channel(reaction_channel_id)
        if not channel:
            return
        e = discord.Embed(title="Reaction added")
        e.add_field(name="Message", value=reaction.message.jump_url)
        e.add_field(name="Message Author", value=reaction.message.author.mention)
        e.add_field(name="Reacted by", value=user.mention)
        if isinstance(reaction.emoji, discord.Emoji):
            reaction_str = str(reaction.emoji)
        else:
            reaction_str = reaction.emoji
        e.add_field(name="Emoji", value=reaction_str)
        await channel.send(embed=e)

async def setup(bot):
    await bot.add_cog(Reactions(bot))