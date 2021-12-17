import discord
from discord.ext import commands

ALLOWED_PHRASES = ['!c', '!d', 'tag a', 'tag b', 'tag c', 'tag d',
                   'tag e', 'tag f', '!l', '!s', '1', '2', '3', '4',
                   '6', '!ml', '!mllu', 'mks', 'wp', 'ssc', 'tr',
                   'mc', 'th', 'tm', 'sgf', 'sa', 'ds', 'ed', 'mw',
                   'cc', 'bdd', 'bc', 'rr', 'rmmm', 'rmc', 'rccb', 'rtt',
                   'rddd', 'rdp3', 'rrry', 'rdkj', 'dkj', 'dp3', 'rws',
                   'rsl', 'rmp', 'ryv', 'rttc', 'ttc', 'rpps', 'pps',
                   'gv', 'rgv', 'rrrd', 'dyc', 'dea', 'ddd', 'dmc',
                   'dwgm', 'drr', 'wgm', 'diio', 'iio', 'dhc', 'dbp',
                   'dcl', 'dww', 'dac', 'dnbc', 'drir', 'rir', 'dsbs',
                   'sbs', 'dbb', 'bb', 'ok', 'ナイス', "can't join",
                   "ct join", "<:ShyPraise:737517348466196532>",
                   "<:TheWman:611227967070142464>", "dc", "sorry"]

RESTRICT_ROLE = 619698507703517184

class Restrictions(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    @commands.Cog.listener(name='on_message')
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.category_id == 719034776929042513:
            return
        
        for role in message.author.roles:
            if role.id == RESTRICT_ROLE:
                if message.content.lower() not in ALLOWED_PHRASES:
                    await message.delete()

    @commands.command(aliases=['rw'])
    @commands.cooldown(1, 300, commands.BucketType.member)
    async def restrictedwords(self, ctx):
        await ctx.send(", ".join(ALLOWED_PHRASES))

    @commands.Cog.listener(name='on_message_edit')
    async def on_message_edit(self, before, after):
        if after.author.bot:
            return
        if after.channel.category_id == 719034776929042513:
            return
        for role in after.author.roles:
            if role.id == RESTRICT_ROLE:
                if after.content.lower() not in ALLOWED_PHRASES:
                    await after.delete()
    

    
def setup(bot):
    bot.add_cog(Restrictions(bot))
