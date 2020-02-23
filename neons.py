from utils import *
from discord.ext import commands
from discord import User
import json
from credentials import discord_via_id, vkRaccoonBotKey
from vk_botting.general import vk_request
import discord


def via_check(ctx):
    return ctx.guild.id == discord_via_id or dev


class Neons(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError) and str(error.original):
            await ctx.send('Ошибка:\n' + str(error.original))

    @commands.check(via_check)
    @commands.command(aliases=['vc'], help='Команда для связи аккаунта вк с аккаунтом дискорда', usage='{}[vk_connect|vc]')
    async def vk_connect(self, ctx):
        pending = await abstract_fetch(False, 'via_profiles', ['lower(discord_name)'], [str(ctx.author).lower()])
        if not pending:
            return await ctx.send('Профиль не найден. Проверьте правильность написания ника в дискорде при привязке и попробуйте еще раз')
        await ctx.send('Профиль успешно привязан')
        return await confirm(pending[0], str(ctx.author), ctx.author.id)


def neons_setup(bot):
    bot.add_cog(Neons(bot))
