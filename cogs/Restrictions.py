import discord
from discord.ext import commands
import json

RESTRICT_ROLE = 619698507703517184

class Restrictions(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        with open('./allowed_phrases.json', 'r', encoding='utf-8') as f:
            self.phrases = json.load(f)
        self.allowed_phrases = self.phrases["ALLOWED_PHRASES"]

    @commands.Cog.listener(name='on_message')
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.category_id == 719034776929042513:
            return
        if message.channel.category_id == 920488310302994432:
            return
        for role in message.author.roles:
            if role.id == RESTRICT_ROLE:
                if message.content.lower() not in self.allowed_phrases:
                    await message.delete()

    @commands.command(aliases=['rw'])
    @commands.cooldown(1, 300, commands.BucketType.member)
    async def restrictedwords(self, ctx):
        await ctx.send(", ".join(self.allowed_phrases))

    @commands.has_any_role("Administrator", "Lounge Staff")
    @commands.command(aliases=['addrw'])
    async def add_restricted_word(self, ctx, *, phrase):
        if phrase.lower() in self.allowed_phrases:
            await ctx.send("already a restricted word")
            return
        self.allowed_phrases.append(phrase.lower())
        with open('./allowed_phrases.json', 'w', encoding='utf-8') as f:
            json.dump(self.phrases, f, ensure_ascii=False, indent=4)
        await ctx.send("added phrase")

    @commands.has_any_role("Administrator", "Lounge Staff")
    @commands.command(aliases=['delrw'])
    async def remove_restricted_word(self, ctx, *, phrase):
        if phrase.lower() not in self.allowed_phrases:
            await ctx.send("not a restricted word")
            return
        self.allowed_phrases.remove(phrase.lower())
        with open('./allowed_phrases.json', 'w', encoding='utf-8') as f:
            json.dump(self.phrases, f, ensure_ascii=False, indent=4)
        await ctx.send("removed phrase")
        

    @commands.Cog.listener(name='on_message_edit')
    async def on_message_edit(self, before, after):
        if after.author.bot:
            return
        if after.channel.category_id in [719034776929042513,920488310302994432, 946990059456987167]:
            return
        for role in after.author.roles:
            if role.id == RESTRICT_ROLE:
                if after.content.lower() not in self.allowed_phrases:
                    await after.delete()
    

    
async def setup(bot):
    await bot.add_cog(Restrictions(bot))
