from discord.ext import commands
import json
from credentials import discord_via_id


def via_check(ctx):
    return ctx.guild.id == discord_via_id


class Neons(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError) and str(error.original):
            await ctx.send('Ошибка:\n' + str(error.original))

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.guild.id == discord_via_id:
            profiles = json.load(open('../Monokuma/MonoKuma/profiles.json', 'r'))
            for user in profiles:
                if profiles[user]['discord']['user_id'] and profiles[user]['discord']['confirmed']:
                    profiles[user]['neons'] += 1
            json.dump(profiles, open('../Monokuma/MonoKuma/profiles.json', 'w'), indent=4, ensure_ascii=False)

    @commands.check(via_check)
    @commands.command(aliases=['vc'], help='Команда для связи аккаунта вк с аккаунтом дискорда', usage='{}[vk_connect|vc]')
    async def vk_connect(self, ctx):
        profiles = json.load(open('../Monokuma/MonoKuma/profiles.json', 'r'))
        for user in profiles:
            if profiles[user]['discord']['user_name'].lower() == str(ctx.author).lower():
                profiles[user]['discord']['user_id'] = ctx.author.id
                profiles[user]['discord']['confirmed'] = True
                json.dump(profiles, open('../Monokuma/MonoKuma/profiles.json', 'w'), indent=4, ensure_ascii=False)
                return await ctx.send('Профиль успешно привязан')
        return await ctx.send('Профиль не найден. Проверьте правильность написания ника в дискорде при привязке и попробуйте еще раз')


def neons_setup(bot):
    bot.add_cog(Neons(bot))
