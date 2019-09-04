import requests
from discord.ext import commands
import discord


class Shadowverse(commands.Cog):
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

    @commands.command(name='svcard', help='Команда для поиска карты из Shadowverse',
                      usage='?svcard <запрос>')
    async def svcard_(self, ctx, *, search=''):
        if not search:
            return await ctx.send('Использование: ?svcard <запрос>')
        cards = self.cards
        results = []
        if cards.__class__ != dict:
            return await ctx.send('Не удалось получить список карт. Попробуйте использовать ?svupdate')
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
                    canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith('?')) and len(
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
                      usage='?svart <запрос>')
    async def svart_(self, ctx, *, search=''):
        if not search:
            return await ctx.send('Использование: ?svcard <запрос>')
        cards = self.cards
        results = []
        if cards.__class__ != dict:
            return await ctx.send('Не удалось получить список карт. Попробуйте использовать ?svupdate')
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
                    canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith('?')) and len(m.content) > 1
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
                      usage='?svupdate')
    async def update_(self, ctx):
        try:
            self.cards = requests.get('https://sv.bagoum.com/cardsFullJSON').json()
            return await ctx.send('База данных карт успешно обновлена')
        except Exception as e:
            return await ctx.send('При обновлении базы данных карт произошла ошибка. Подробнее:\n{}'.format(e))


def sv_setup(bot):
    bot.add_cog(Shadowverse(bot))
