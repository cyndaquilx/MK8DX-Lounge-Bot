import discord
from discord.ext import commands, tasks
import json
from datetime import datetime, timedelta

from custom_checks import check_chat_restricted_roles

class Restrictions(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        with open('./allowed_phrases.json', 'r', encoding='utf-8') as f:
            self.phrases = json.load(f)
        self.allowed_phrases = self.phrases["ALLOWED_PHRASES"]

        #Dictionary containing a list of illegal messages sent by chat restricted users.
        #Keys are instances of discord.Member, values are lists of datetimes
        self.violations = {}
        #Dictionary containing lists of valid messages sent by chat restricted users.
        #Keys are instances of discord.Member, values are lists of datetimes
        self.restricted_msgs = {}

        self._remove_task = self.remove_expired_violations.start()

    # Removes any restriction violations / allowed message timestamps that are over a minute old
    @tasks.loop(seconds=5)
    async def remove_expired_violations(self):
        for time_list in self.violations.values():
            for i in range(len(time_list)-1, -1, -1):
                if time_list[i] + timedelta(minutes=1) > datetime.utcnow():
                    time_list.pop(i)
        for time_list in self.restricted_msgs.values():
            for i in range(len(time_list)-1, -1, -1):
                if time_list[i] + timedelta(minutes=1) > datetime.utcnow():
                    time_list.pop(i)

    async def add_violation(self, message:discord.Message):
        if message.author not in self.violations.keys():
            self.violations[message.author] = []
        self.violations[message.author].append(datetime.utcnow())
        if len(self.violations[message.author]) >= 3:
            await message.author.timeout(timedelta(minutes=5), reason="5-minute timeout for restricted message violation")
            await message.channel.send(f"{message.author.mention} you have been timed out for 5 minutes for violating chat restriction rules", delete_after=15.0)

    async def add_message(self, message:discord.Message):
        if message.author not in self.restricted_msgs.keys():
            self.restricted_msgs[message.author] = []
        self.restricted_msgs[message.author].append(datetime.utcnow())
        if len(self.restricted_msgs[message.author]) >= 5:
            await message.author.timeout(timedelta(minutes=5), reason="5-minute timeout for restricted message violation")
            await message.channel.send(f"{message.author.mention} you have been timed out for 5 minutes for violating chat restriction rules", delete_after=15.0)

    @commands.Cog.listener(name='on_message')
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.guild is None:
            return
        if message.channel.category_id in [719034776929042513, 920488310302994432]:
            return
        if check_chat_restricted_roles(self.bot, message.author):
            if message.reference is not None:
                await self.add_violation(message)
                await message.delete()
            elif message.content.lower() not in self.allowed_phrases:
                await self.add_violation(message)
                await message.delete()
            else:
                await self.add_message(message)

    @commands.Cog.listener(name='on_message_edit')
    async def on_message_edit(self, before, after):
        if after.author.bot:
            return
        if after.channel.category_id in [719034776929042513, 920488310302994432, 946990059456987167]:
            return
        if check_chat_restricted_roles(self.bot, after.author):
            if after.content.lower() not in self.allowed_phrases:
                await self.add_violation(after)
                await after.delete()

    @commands.command(aliases=['rw'])
    @commands.cooldown(1, 300, commands.BucketType.member)
    async def restrictedwords(self, ctx):
        await ctx.send("https://raw.githubusercontent.com/cyndaquilx/MK8DX-Lounge-Bot/main/allowed_phrases.json")

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
    

    
async def setup(bot):
    await bot.add_cog(Restrictions(bot))
