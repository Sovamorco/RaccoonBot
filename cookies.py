from discord.ext import commands
import discord
import json
import asyncio
from random import randrange


class Cookies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.add_cookies())

    async def add_cookies(self):
        while True:
            guilds = self.bot.guilds
            cookies = json.load(open('resources/cookies.json', 'r'))
            online = {}
            for guild in guilds:
                members = guild.members
                for member in members:
                    if member.status == discord.Status.online and not member.bot:
                        voice = False if member.voice is None else True
                        if (str(member.id) not in online.keys()) or voice:
                            online[str(member.id)] = {'nick': member.name, 'voice': voice}
            for user_id in online.keys():
                if str(user_id) in cookies.keys():
                    if online[user_id]['voice']:
                        cookies[user_id]['cookies'] += randrange(31, 35)
                    else:
                        cookies[user_id]['cookies'] += randrange(11, 15)
                else:
                    cookies[user_id] = {'id': int(user_id), 'name': online[user_id]['nick'],
                                        'cookies': randrange(289, 296)}
            json.dump(cookies, open('resources/cookies.json', 'w'))
            await asyncio.sleep(300)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.bot:
            cookies = json.load(open('resources/cookies.json', 'r'))
            if str(member.id) not in cookies.keys():
                cookies[str(member.id)] = {'id': member.id, 'name': member.name, 'cookies': randrange(289, 296)}
            json.dump(cookies, open('resources/cookies.json', 'w'))

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        user = ctx.author
        if not user.bot and not ctx.valid:
            cookies = json.load(open('resources/cookies.json', 'r'))
            if str(user.id) not in cookies.keys():
                cookies[str(user.id)] = {'id': user.id, 'name': user.name, 'cookies': randrange(289, 296)}
            else:
                cookies[str(user.id)]['cookies'] += randrange(10, 17)
            json.dump(cookies, open('resources/cookies.json', 'w'))

    @commands.command(name='cookies', aliases=['points'], help='Команда для отображения печенек',
                      usage='?[cookies|points]')
    async def cookies_(self, ctx):
        try:
            user = ctx.author
            cookies = json.load(open('resources/cookies.json', 'r')).get(str(user.id), None)
            if cookies is None:
                cookies = 'нет'
            else:
                cookies = '{:,}'.format(cookies['cookies'])
            return await ctx.send('У <@!{}> {} печенек'.format(user.id, cookies))
        except Exception as e:
            await ctx.send('Ошибка: \n {}'.format(e))

    @commands.command(name='leaderboard', aliases=['lb'], help='Команда для отображения топа печенек',
                      usage='?[lb|leaderboard]')
    async def leaderboard_(self, ctx):
        try:
            cookies = json.load(open('resources/cookies.json', 'r'))
            cookies = sorted(cookies.items(), key=lambda kv: kv[1]['cookies'], reverse=True)
            length = 10 if len(cookies) > 10 else len(cookies)
            embedValue = ''
            for i in range(length):
                embedValue += '{}. {}: {:,} печенек\n\n'.format(i+1, cookies[i][1]['name'], cookies[i][1]['cookies'])
            embed = discord.Embed(title='Топ печенек', description=embedValue)
            return await ctx.send('<@!{}>'.format(ctx.author.id), embed=embed)
        except Exception as e:
            await ctx.send('Ошибка: \n {}'.format(e))


def cookies_setup(bot):
    bot.add_cog(Cookies(bot))
