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

    async def get_display_name(self, uid):
        prof = await load_profile(uid)
        if not prof:
            user = await vk_request('users.get', vkRaccoonBotKey, user_ids=uid)
            return user['response']['first_name']
        if prof['discord']['user_id']:
            return self.bot.get_user(prof['discord']['user_id']).display_name
        if prof['nick']:
            return prof['nick']
        user = await vk_request('users.get', vkRaccoonBotKey, user_ids=uid)
        return user['response']['first_name']

    @commands.check(via_check)
    @commands.command(aliases=['vc'], help='Команда для связи аккаунта вк с аккаунтом дискорда', usage='{}[vk_connect|vc]')
    async def vk_connect(self, ctx):
        integ = json.load(open('resources/integrations.json', 'r'))
        if str(ctx.author.id) in integ.keys():
            return await ctx.send('Профиль VIA уже привязан')
        profiles = await load_profiles()
        for user in profiles:
            if profiles[user]['discord']['user_name'].lower() == str(ctx.author).lower():
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
    async def via_profile(self, ctx, user: User = None):
        if not user:
            user = ctx.author
        integ = json.load(open('resources/integrations.json', 'r'))
        if str(user.id) not in integ.keys():
            return await ctx.send('Профиль VIA не привязан')
        embed = discord.Embed(title='Профиль VIA', description='', color=discord.Color.dark_purple())
        target = await load_profile(integ[str(user.id)])
        embed.description += f'Неонов - {target["neons"]}\n\n'
        embed.description += f'Осколков - {target["oskolki"]}\n\n'

        if not target['brak']:
            embed.description += 'Не в браке\n\n'
        elif target["brak"][1] == 0:
            second = target["brak"][0]
            snick = await self.get_display_name(second)
            embed.description += f'В браке с {snick}\n\n'
        else:
            embed.description += 'Не в браке\n\n'

        if target["rab"][0] == 1:
            slavemaster = target["rab"][1]
            snick = await self.get_display_name(slavemaster)
            embed.description += f'Раб {snick}\n\n'
        elif target["rab"][0] == 2:
            embed.description += 'Рабовладелец\n\n'
        elif target["rab"][0] == 3:
            embed.description += 'Навеки свободный\n\n'

        if target['harem']['own']:
            embed.description += 'Владелец Гарема\n\n'
        elif target['harem']['is_owned']:
            owner = target['harem']['owner']
            onick = await self.get_display_name(owner)
            embed.description += f'В гареме у {onick}\n\n'
        else:
            embed.description += 'Не в гареме\n\n'

        if target['pets']['own']:
            embed.description += f'Хозяин питомцев\n\n'
        else:
            embed.description += f"Не имеет титула 'Хозяин Питомцев'\n\n"
            pe = target['pets']['is_owned']
            if pe[0]:
                owner = pe[2]
                snick = await self.get_display_name(owner)
                kl = pe[3] if pe[3] else "{Нет клички}"
                if pe[1] == 'hamster':
                    embed.description += f"Хомяк {snick} по кличке - {kl}"
                elif pe[1] == 'cat':
                    embed.description += f"Кот {snick} по кличке - {kl}"
                elif pe[1] == 'dog':
                    embed.description += f"Собака {snick} по кличке - {kl}"
                elif pe[1] == 'parrot':
                    embed.description += f"Попугай {snick} по кличке - {kl}"
                elif pe[1] == 'spider':
                    embed.description += f"Енот {snick} по кличке - {kl}"
                elif pe[1] == 'rabbit':
                    embed.description += f"Кролик {snick} по кличке - {kl}"
                elif pe[1] == 'raven':
                    embed.description += f"Ворон {snick} по кличке - {kl}"
            else:
                embed.description += f"Не питомец"

        if target['klan']['neko'][0] == 1:
            embed.description += 'Состоит в Clan Neko\n\n'
        if target['klan']['demons'][0] == 1:
            embed.description += 'Состоит в Clan Demons\n\n'
        if target['klan']['nanbamons'][0] == 1:
            embed.description += 'Состоит в Clan Nanbamons\n\n'
        elif all(target['klan'][kl][0] != 1 for kl in target['klan']):
            embed.description += 'Не в клане'
        return await ctx.send(embed=embed)


def neons_setup(bot):
    bot.add_cog(Neons(bot))
