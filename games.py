import requests
from discord.ext import commands
import discord
from enum import IntFlag
from credentials import osu_key
from utils import get_prefix


class osumods(IntFlag):
    NoMod = 0,
    NF = 1,
    EZ = 2,
    TD = 4,
    HD = 8,
    HR = 16,
    SD = 32,
    DT = 64,
    RX = 128,
    HT = 256,
    NC = 512,
    FL = 1024,
    Auto = 2048,
    SO = 4096,
    AP = 8192,
    PF = 16384,
    Key4 = 32768,
    Key5 = 65536,
    Key6 = 131072,
    Key7 = 262144,
    Key8 = 524288,
    FadeIn = 1048576,
    Random = 2097152,
    Cinema = 4194304,
    Target = 8388608,
    Key9 = 16777216,
    KeyCoop = 33554432,
    Key1 = 67108864,
    Key3 = 134217728,
    Key2 = 268435456,
    ScoreV2 = 536870912,
    LastMod = 1073741824


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.cards = requests.get('https://sv.bagoum.com/cardsFullJSON').json()
        except Exception as e:
            print(e)
            self.cards = requests.get('https://sv.bagoum.com/cardsFullJSON').json()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError) and str(error.original):
            await ctx.send('Ошибка:\n' + str(error.original))

    @commands.command(name='osuplayer', aliases=['op'], help='Команда для получения информации о игроке osu!standart',
                      usage='{}[op|osuplayer] <ник/id>')
    async def op_(self, ctx, *, nickname=''):
        if not nickname:
            pref = await get_prefix(self.bot, ctx.message)
            return await ctx.send(f'Использование: {pref}[op|osuplayer] <ник/id>')
        api_link = 'https://osu.ppy.sh/api/'
        params = {
            'k': osu_key,
            'u': nickname
        }
        r = requests.get(api_link + 'get_user', params=params, timeout=2).json()
        if not r:
            return await ctx.send('Пользователь не найден')
        result = r[0]
        if result['playcount'] is None:
            return await ctx.send('Слишком мало информации по пользователю')
        embed = discord.Embed(title=result['username'], url='https://osu.ppy.sh/users/{}'.format(result['user_id']))
        embed.set_thumbnail(url='https://a.ppy.sh/{}'.format(result['user_id']))
        embed.add_field(name='Rank', value='{:,}'.format(int(result['pp_rank'])))
        embed.add_field(name='Country rank :flag_{}:'.format(result['country'].lower()),
                        value='{:,}'.format(int(result['pp_country_rank'])))
        embed.add_field(name='PP', value='{:,}'.format(round(float(result['pp_raw']))))
        embed.add_field(name='Accuracy', value=str(round(float(result['accuracy']), 2)) + '%')
        embed.add_field(name='Level', value=str(int(float(result['level']))))
        embed.add_field(name='Play Count', value='{:,}'.format(int(result['playcount'])))
        embed.add_field(name='Ranked Score', value='{:,}'.format(int(result['ranked_score'])))
        embed.add_field(name='Total Score', value='{:,}'.format(int(result['total_score'])))
        await ctx.send(ctx.author.mention, embed=embed)

    @commands.command(name='osuplays', aliases=['ops'], usage='{}[ops|osuplays] <ник/id>',
                      help='Команда для получения информации о лучших плеях игрока osu!standart')
    async def ops_(self, ctx, *, nickname=''):
        if not nickname:
            pref = await get_prefix(self.bot, ctx.message)
            return await ctx.send(f'Использование: {pref}[ops|osuplays] <ник/id>')
        api_link = 'https://osu.ppy.sh/api/'
        params = {
            'k': osu_key,
            'u': nickname
        }
        plays = requests.get(api_link + 'get_user_best', params=params, timeout=2).json()
        if not plays:
            return await ctx.send('Пользователь не найден')
        embed = discord.Embed(description='Loading...')
        msg = await ctx.send(ctx.author.mention, embed=embed)
        embed = discord.Embed()
        for i in range(len(plays)):
            params = {
                'k': osu_key,
                'b': plays[i]['beatmap_id']
            }
            info = requests.get(api_link + 'get_beatmaps', params=params).json()[0]
            accuracy = round(
                (int(plays[i]['count300']) * 300 + int(plays[i]['count100']) * 100 + int(
                    plays[i]['count50']) * 50) / (
                        (int(plays[i]['count300']) + int(plays[i]['count100']) + int(plays[i]['count50'])) * 3), 2)
            combo = '{:,} ({})'.format(int(plays[i]['maxcombo']),
                                       'FC' if plays[i]['maxcombo'] == info['max_combo'] else info['max_combo'])
            mods = str(osumods(int(plays[i]['enabled_mods']))).replace('osumods.', '', 1)
            if 'NC' in mods:
                mods = mods.replace('|DT', '')
            if 'PF' in mods:
                mods = mods.replace('|SD', '')
            name = '{}. {} [{}] ({})'.format(i + 1, info['title'], info['version'], mods)
            value = 'Score: {:,}; Combo: {}; PP: {:,}; Acc: {}%; Rank: {}'.format(int(plays[i]['score']), combo, round(float(plays[i]['pp']), 2), accuracy,
                                                                                  plays[i]['rank'].replace('H', '', 1))
            embed.add_field(name=name, value=value)
        await msg.edit(content=ctx.author.mention, embed=embed)

    @commands.command(name='svcard', help='Команда для поиска карты из Shadowverse', usage='{}svcard <запрос>')
    async def svcard_(self, ctx, *, search=''):
        pref = await get_prefix(self.bot, ctx.message)
        if not search:
            return await ctx.send(f'Использование: {pref}svcard <запрос>')
        cards = self.cards
        results = []
        if cards.__class__ != dict:
            return await ctx.send(f'Не удалось получить список карт. Попробуйте использовать {pref}svupdate')
        text_channel = ctx.message.channel
        user = ctx.message.author
        terms = search.split(' ')
        for card in cards:
            if all(term.lower() in cards[card]['searchableText'].lower() for term in terms):
                results.append(cards[card])
                if len(results) == 10:
                    break
        if not results:
            return await ctx.send('Карты не найдены')
        else:
            if len(results) == 1:
                result = results[0]
            else:
                content = ''
                for i in range(len(results)):
                    content += '{}. {}\n'.format(i+1, results[i]['name'])
                embed = discord.Embed(title='Выберите карту', description=content)
                embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
                choice = await ctx.send(embed=embed)
                canc = False

                def verify(m):
                    nonlocal canc
                    if m.content.isdigit():
                        return (0 <= int(m.content) <= len(results)) and (m.channel == text_channel) and (
                                m.author == user)
                    canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith(pref)) and len(
                        m.content) > 1
                    return canc

                msg = await self.bot.wait_for('message', check=verify, timeout=30)
                if canc:
                    return await choice.delete()
                if int(msg.content) == 0:
                    return await choice.delete()
                result = results[int(msg.content)-1]
            embed = discord.Embed(title=result['name'], url='https://sv.bagoum.com/cards/{}'.format(result['id']))
            race = result['faction'] if not result['race'] else '{}/{}'.format(result['faction'], result['race'])
            embed.set_thumbnail(url='https://sv.bagoum.com/cardF/en/c/{}'.format(result['id']))
            embed.set_image(url='https://sv.bagoum.com/getRawImage/0/0/{}'.format(result['id']))
            embed.add_field(name='Класс', value=race)
            embed.add_field(name='Дополнение', value=result['expansion'])
            if result['baseData']['description']:
                embed.add_field(name='Описание', value=result['baseData']['description'].replace('<br>', '\n'))
            embed.add_field(name='Flair', value=result['baseData']['flair'].replace('<br>', '\n'))
            if result['hasEvo']:
                evoembed = discord.Embed(title=result['name']+' (evolved)',
                                         url='https://sv.bagoum.com/cards/{}'.format(result['id']))
                evoembed.set_thumbnail(url='https://sv.bagoum.com/cardF/en/e/{}'.format(result['id']))
                evoembed.set_image(url='https://sv.bagoum.com/getRawImage/1/0/{}'.format(result['id']))
                if result['evoData']['description']:
                    evoembed.add_field(name='Описание', value=result['evoData']['description'].replace('<br>', '\n'))
                elif result['baseData']['description']:
                    evoembed.add_field(name='Описание', value=result['baseData']['description'].replace('<br>', '\n'))
                evoembed.add_field(name='Flair', value=result['evoData']['flair'].replace('<br>', '\n'))
                await ctx.send(embed=embed)
                return await ctx.send(embed=evoembed)
            return await ctx.send(embed=embed)

    @commands.command(name='svart', help='Команда для поиска арта карты из Shadowverse',
                      usage='{}svart <запрос>')
    async def svart_(self, ctx, *, search=''):
        pref = await get_prefix(self.bot, ctx.message)
        if not search:
            return await ctx.send(f'Использование: {pref}svcard <запрос>')
        cards = self.cards
        results = []
        if cards.__class__ != dict:
            return await ctx.send(f'Не удалось получить список карт. Попробуйте использовать {pref}svupdate')
        text_channel = ctx.message.channel
        user = ctx.message.author
        terms = search.split(' ')
        for card in cards:
            if all(term.lower() in cards[card]['searchableText'].lower() for term in terms):
                results.append(cards[card])
                if len(results) == 10:
                    break
        if not results:
            return await ctx.send('Карты не найдены')
        else:
            if len(results) == 1:
                result = results[0]
            else:
                content = ''
                for i in range(len(results)):
                    content += '{}. {}\n'.format(i + 1, results[i]['name'])
                embed = discord.Embed(title='Выберите карту', description=content)
                embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
                choice = await ctx.send(embed=embed)
                canc = False

                def verify(m):
                    nonlocal canc
                    if m.content.isdigit():
                        return (0 <= int(m.content) <= len(results)) and (m.channel == text_channel) and (
                                    m.author == user)
                    canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith(pref)) and len(m.content) > 1
                    return canc

                msg = await self.bot.wait_for('message', check=verify, timeout=30)
                if canc:
                    return await choice.delete()
                if int(msg.content) == 0:
                    return await choice.delete()
                result = results[int(msg.content) - 1]
            embed = discord.Embed(title=result['name'], url='https://sv.bagoum.com/cards/{}'.format(result['id']))
            embed.set_image(url='https://sv.bagoum.com/getRawImage/0/0/{}'.format(result['id']))
            if result['hasEvo']:
                evoembed = discord.Embed(title=result['name']+' (evolved)',
                                         url='https://sv.bagoum.com/cards/{}'.format(result['id']))
                evoembed.set_image(url='https://sv.bagoum.com/getRawImage/1/0/{}'.format(result['id']))
                await ctx.send(embed=embed)
                return await ctx.send(embed=evoembed)
            return await ctx.send(embed=embed)

    @commands.command(name='svupdate', help='Команда для обновления базы данных карт',
                      usage='{}svupdate')
    async def update_(self, ctx):
        try:
            self.cards = requests.get('https://sv.bagoum.com/cardsFullJSON').json()
            return await ctx.send('База данных карт успешно обновлена')
        except Exception as e:
            return await ctx.send('При обновлении базы данных карт произошла ошибка. Подробнее:\n{}'.format(e))


def games_setup(bot):
    bot.add_cog(Games(bot))
