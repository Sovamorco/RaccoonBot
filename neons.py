from utils import *
from discord.ext import commands
import json
from credentials import discord_via_id
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
        profiles = await load_profiles()
        for user in profiles:
            if profiles[user]['discord']['user_name'].lower() == str(ctx.author).lower():
                integ = json.load(open('resources/integrations.json', 'r'))
                profiles[user]['discord']['user_name'] = str(ctx.author)
                profiles[user]['discord']['user_id'] = ctx.author.id
                profiles[user]['discord']['confirmed'] = True
                integ[str(ctx.author.id)] = user
                await dump_profile(user, profiles[user])
                json.dump(integ, open('resources/integrations.json', 'w'))
                return await ctx.send('Профиль успешно привязан')
        return await ctx.send('Профиль не найден. Проверьте правильность написания ника в дискорде при привязке и попробуйте еще раз')

    @commands.check(via_check)
    @commands.command(aliases=['vp'], help='Команда для просмотра профиля VIA', usage='{}[via_profile|vp]')
    async def via_profile(self, ctx):
        integ = json.load(open('resources/integrations.json', 'r'))
        if str(ctx.author.id) not in integ.keys():
            return await ctx.send('Профиль VIA не привязан')
        embed = discord.Embed(title='Профиль VIA', description='', color=discord.Color.dark_purple())
        target = await load_profile(integ[str(ctx.author.id)])
        embed.description += f'Неонов - {target["neons"]}\n\n'
        embed.description += f'Осколков - {target["oskolki"]}\n\n'

        if not target['brak']:
            embed.description += 'Не в браке\n\n'
        elif target["brak"][1] == 0:
            second = target["brak"][0]
            sprof = await load_profile(second)
            sid = sprof['discord']['user_id']
            if sid:
                embed.description += f'В браке с {self.bot.get_user(sid).display_name}\n\n'
            else:
                embed.description += 'В браке с кем-то, у кого не привязан ВК к Дискорду\n\n'
        else:
            embed.description += 'Не в браке\n\n'

        if target["rab"][0] == 1:
            slavemaster = target["rab"][1]
            sprof = await load_profile(slavemaster)
            sid = sprof['discord']['user_id']
            if sid:
                embed.description += f'Раб {self.bot.get_user(sid).display_name}\n\n'
            else:
                embed.description += 'Раб кого-то, у кого не привязан ВК к Дискорду\n\n'
        elif target["rab"][0] == 2:
            embed.description += 'Рабовладелец\n\n'
        elif target["rab"][0] == 3:
            embed.description += 'Навеки свободный\n\n'

        if target['harem']['own']:
            embed.description += 'Владелец Гарема\n\n'
        elif target['harem']['is_owned']:
            owner = target['harem']['owner']
            oprof = await load_profile(owner)
            sid = oprof['discord']['user_id']
            if sid:
                embed.description += f'В гареме у {self.bot.get_user(sid).display_name}\n\n'
            else:
                embed.description += 'В гареме у кого-то, у кого не привязан ВК к Дискорду\n\n'
        else:
            embed.description += 'Не в гареме\n\n'

        if target['pets']['own']:
            embed.description += 'Хозяин Питомцев\nПитомцы:\n\n'
        else:
            embed.description += 'Не Хозяин Питомцев\n\n'

        if target['klan']['neko'][0] == 1:
            embed.description += 'Состоит в Clan Neko'
        else:
            embed.description += 'Не в клане'
        return await ctx.send(embed=embed)


def neons_setup(bot):
    bot.add_cog(Neons(bot))
