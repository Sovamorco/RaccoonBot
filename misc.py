from discord.ext import commands
import discord
import requests
from json import load
from random import choice
from html import unescape
from credentials import osu_key, genius_token
from enum import IntFlag
from bs4 import BeautifulSoup
import re


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


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError) and str(error.original):
            await ctx.send('Ошибка:\n' + str(error.original))

    @commands.command(name='raccoon', aliases=['racc'], help='Команда, которая сделает вашу жизнь лучше',
                      usage='?[racc|raccoon]')
    async def raccoon_(self, ctx, *, msg=None):
        user = ctx.author
        if msg is None:
            msg = user.mention
        with open('resources/raccoons.txt', 'r') as f:
            raccoons = load(f)
            raccoon = choice(raccoons)
        embed = discord.Embed()
        embed.set_image(url=raccoon)
        return await ctx.send(msg, embed=embed)

    @commands.command(name='inspirobot', aliases=['inspire'], help='Команда для генерации "воодушевляющих" картинок',
                      usage='?[inspire|inspirobot]')
    async def inspire_(self, ctx, *, msg=None):
        user = ctx.author
        if msg is None:
            msg = user.mention
        image = requests.get('http://inspirobot.me/api?generate=true').text
        embed = discord.Embed()
        embed.set_image(url=image)
        return await ctx.send(msg, embed=embed)

    @commands.command(name='fact', aliases=['facts'], help='Команда, возвращающая случайные факты',
                      usage='?[fact|facts]')
    async def fact_(self, ctx, *, msg=None):
        user = ctx.author
        if msg is None:
            msg = user.mention
        with open('resources/facts.json', 'r') as f:
            facts = load(f)
            fact = choice(facts)
        embed = discord.Embed(description=fact)
        return await ctx.send(msg, embed=embed)

    @commands.command(name='wikia', aliases=['wiki'], help='Команда для поиска статей на Fandom',
                      usage='?[wikia|wiki] <запрос>')
    async def wikia_(self, ctx, *, query=None):
        try:
            text_channel = ctx.message.channel
            if query is None:
                return await ctx.send('Использование: ?[wikia|wiki] <запрос>')
            apiurl = 'https://community.fandom.com/api/v1/Search/CrossWiki'
            user = ctx.message.author
            params = {
                'expand': 1,
                'query': query,
                'lang': 'ru,en',
                'limit': 10,
                'batch': 1,
                'rank': 'default'
            }
            result = requests.get(apiurl, params=params, timeout=0.5).json()
            if 'exception' in result.keys():
                return await ctx.send('Ничего не найдено')
            results = result['items']
            new_results = []
            embedValue = ''
            i = 0
            for result in results:
                if result:
                    if result['title']:
                        i += 1
                        embedValue += '{}. {}\n'.format(i, result['title'])
                        new_results.append(result)
            embed = discord.Embed(title='Выберите фэндом', description=embedValue)
            embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                if m.content.isdigit():
                    return (0 <= int(m.content) <= len(new_results)) and (m.channel == text_channel) and (
                            m.author == user)
                canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith('?')) and len(
                    m.content) > 1
                return canc

            msg = await self.bot.wait_for('message', check=verify, timeout=30)
            if canc:
                return await choicemsg.delete()
            if int(msg.content) == 0:
                return await choicemsg.delete()
            result = new_results[int(msg.content) - 1]
            await choicemsg.delete()
            if result['url'].endswith('/'):
                apiurl = '{}api/v1/'.format(result['url'])
            else:
                apiurl = '{}/api/v1/'.format(result['url'])
            params = {
                'query': query,
                'namespaces': '0,14',
                'limit': 1,
                'minArticleQuality': 0,
                'batch': 1
            }
            try:
                result = requests.get(apiurl + 'Search/List', params=params, timeout=0.5).json()
            except Exception as e:
                await ctx.send('Ничего не найдено')
                return print(e)
            if 'exception' in result.keys():
                return await ctx.send('Ничего не найдено')
            page_id = result['items'][0]['id']
            params = {
                'ids': page_id,
                'abstract': 500,
                'width': 200,
                'height': 200
            }
            result = requests.get(apiurl + 'Articles/Details', params=params, timeout=0.5).json()
            basepath = result['basepath']
            result = result['items'][str(page_id)]
            page_url = basepath + result['url']
            title = result['title']
            desc = unescape(result['abstract'])
            dims = result['original_dimensions']
            thumb = result['thumbnail']
            if dims is not None:
                width = dims['width']
                height = dims['height']
                if width <= 200:
                    params = {
                        'ids': page_id,
                        'abstract': 0,
                        'width': width,
                        'height': height
                    }
                else:
                    ratio = height / width
                    width = 200
                    height = ratio * width
                    params = {
                        'ids': page_id,
                        'abstract': 0,
                        'width': width,
                        'height': height
                    }
                result = requests.get(apiurl + 'Articles/Details', params=params, timeout=0.5).json()
                thumb = result['items'][str(page_id)]['thumbnail']
            embed = discord.Embed(title=title, url=page_url, description=desc)
            if thumb is not None:
                embed.set_thumbnail(url=thumb)
            return await ctx.send(user.mention, embed=embed)
        except requests.exceptions.ConnectTimeout:
            await ctx.send('Не удалось подключиться к Wikia')

    @commands.command(name='fandom', help='Вторая команда для поиска статей на Fandom',
                      usage='?fandom <фэндом>')
    async def fandom_(self, ctx, *, query=None):
        try:
            text_channel = ctx.message.channel
            if query is None:
                return await ctx.send('Использование: ?fandom <фэндом>')
            apiurl = 'https://community.fandom.com/api/v1/Search/CrossWiki'
            user = ctx.message.author
            params = {
                'expand': 1,
                'query': query,
                'lang': 'en',
                'limit': 10,
                'batch': 1,
                'rank': 'default'
            }
            result = requests.get(apiurl, params=params, timeout=0.5).json()
            if 'exception' in result.keys():
                return await ctx.send('Ничего не найдено')
            results = result['items']
            new_results = []
            embedValue = ''
            i = 0
            for result in results:
                if result:
                    if result['title']:
                        i += 1
                        embedValue += '{}. {}\n'.format(i, result['title'])
                        new_results.append(result)
            if len(new_results) < 10:
                params['lang'] = 'ru'
                result = requests.get(apiurl, params=params, timeout=0.5).json()
                if 'exception' in result.keys():
                    pass
                else:
                    results = result['items']
                    for result in results:
                        if i == 10:
                            break
                        if result:
                            if result['title']:
                                i += 1
                                embedValue += '{}. {}\n'.format(i, result['title'])
                                new_results.append(result)
            embed = discord.Embed(title='Выберите фэндом', description=embedValue)
            embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                if m.content.isdigit():
                    return (0 <= int(m.content) <= len(new_results)) and (m.channel == text_channel) and (
                            m.author == user)
                canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith('?')) and len(
                    m.content) > 1
                return canc

            msg = await self.bot.wait_for('message', check=verify, timeout=30)
            if canc:
                return await choicemsg.delete()
            if int(msg.content) == 0:
                return await choicemsg.delete()
            result = new_results[int(msg.content) - 1]
            await choicemsg.delete()
            if result['url'].endswith('/'):
                apiurl = '{}api/v1/'.format(result['url'])
            else:
                apiurl = '{}/api/v1/'.format(result['url'])
            embed = discord.Embed(title='Введите запрос', description='Отправьте запрос для поска по {}'.format(result['title']))
            embed.set_footer(text='Автоматическая отмена через 60 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith('?')) and len(
                    m.content) > 1
                return (m.channel == text_channel) and (m.author == user)

            msg = await self.bot.wait_for('message', check=verify, timeout=60)
            if canc:
                return await choicemsg.delete()
            query = msg.content
            params = {
                'query': query,
                'namespaces': '0,14',
                'limit': 1,
                'minArticleQuality': 0,
                'batch': 1
            }
            try:
                result = requests.get(apiurl + 'Search/List', params=params, timeout=0.5).json()
            except Exception as e:
                embed = discord.Embed(title='Ошибка', description='Ничего не найдено')
                await choicemsg.edit(embed=embed)
                return print(e)
            if 'exception' in result.keys() or result['batches'] == 0:
                embed = discord.Embed(title='Ошибка', description='Ничего не найдено')
                return await choicemsg.edit(embed=embed)
            page_id = result['items'][0]['id']
            params = {
                'ids': page_id,
                'abstract': 500,
                'width': 200,
                'height': 200
            }
            result = requests.get(apiurl + 'Articles/Details', params=params, timeout=0.5).json()
            basepath = result['basepath']
            result = result['items'][str(page_id)]
            page_url = basepath + result['url']
            title = result['title']
            desc = unescape(result['abstract'])
            dims = result['original_dimensions']
            thumb = result['thumbnail']
            if dims is not None:
                width = dims['width']
                height = dims['height']
                if width <= 200:
                    params = {
                        'ids': page_id,
                        'abstract': 0,
                        'width': width,
                        'height': height
                    }
                else:
                    ratio = height / width
                    width = 200
                    height = ratio * width
                    params = {
                        'ids': page_id,
                        'abstract': 0,
                        'width': width,
                        'height': height
                    }
                result = requests.get(apiurl + 'Articles/Details', params=params, timeout=0.5).json()
                thumb = result['items'][str(page_id)]['thumbnail']
            embed = discord.Embed(title=title, url=page_url, description=desc)
            if thumb is not None:
                embed.set_thumbnail(url=thumb)
            return await choicemsg.edit(content=user.mention, embed=embed)
        except requests.exceptions.ConnectTimeout:
            await ctx.send('Не удалось подключиться к Wikia')

    @commands.command(aliases=['l'], usage='?[l|lyrics] <запрос>',
                      help='Команда для отображения текста текущего трека')
    async def lyrics(self, ctx, *, title=None):
        if title is None:
            return await ctx.send('Использование: ?[l|lyrics] <запрос>')
        text_channel = ctx.message.channel
        user = ctx.message.author
        ftitle = re.sub(r'\[([^)]+?)]', '', re.sub(r'\(([^)]+?)\)', '', title.lower()))
        params = {
            'q': ftitle
        }
        headers = {
            'Authorization': 'Bearer ' + genius_token
        }
        req = requests.get('https://api.genius.com/search', params=params, headers=headers)
        r = req.json()['response']['hits']
        if len(r) == 0:
            return await ctx.send('Песни не найдены')
        else:
            new_results = []
            embedValue = ''
            i = 0
            for result in r:
                if result['type'] == 'song' and result['result']['lyrics_state'] == 'complete':
                    i += 1
                    embedValue += '{}. {} - {}\n'.format(i, result['result']['primary_artist']['name'],
                                                         result['result']['title'])
                    new_results.append(result)

            embed = discord.Embed(title='Выберите трек', description=embedValue)
            embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                if m.content.isdigit():
                    return (0 <= int(m.content) <= len(new_results)) and (m.channel == text_channel) and (
                                m.author == user)
                canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith('?')) and len(
                    m.content) > 1
                return canc

            msg = await self.bot.wait_for('message', check=verify, timeout=30)
            if canc:
                return await choicemsg.delete()
            if int(msg.content) == 0:
                return await choicemsg.delete()
            result = new_results[int(msg.content) - 1]
            url = result['result']['url']
            title = '{} - {}'.format(result['result']['primary_artist']['name'], result['result']['title'])
            lyrics = requests.get(url)
            soup = BeautifulSoup(lyrics.text, 'html.parser')
            lyrics = soup.p.get_text()
            if len(lyrics) > 2000:
                lyrlist = lyrics.split('\n')
                lyrics = ''
                it = 1
                for i in range(len(lyrlist)):
                    lyrics += lyrlist[i] + '\n'
                    if i < len(lyrlist) - 1 and len(lyrics + lyrlist[i + 1]) > 2000:
                        embed = discord.Embed(color=discord.Color.blurple(),
                                              title='Текст {} ({})'.format(title, it), description=lyrics)
                        await ctx.send(embed=embed)
                        lyrics = ''
                        it += 1
                    elif i == len(lyrlist) - 1:
                        embed = discord.Embed(color=discord.Color.blurple(),
                                              title='Текст {} ({})'.format(title, it), description=lyrics)
                        return await ctx.send(embed=embed)
            else:
                embed = discord.Embed(color=discord.Color.blurple(),
                                      title='Текст ' + title, description=lyrics)
                return await ctx.send(embed=embed)

    @commands.command(name='osuplayer', aliases=['op'], help='Команда для получения информации о игроке osu!standart',
                      usage='?[op|osuplayer] <ник/id>')
    async def op_(self, ctx, *, nickname=''):
        if not nickname:
            return await ctx.send('Использование: ?[op|osuplayer] <ник/id>')
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

    @commands.command(name='osuplays', aliases=['ops'], usage='?[ops|osuplays] <ник/id>',
                      help='Команда для получения информации о лучших плеях игрока osu!standart')
    async def ops_(self, ctx, *, nickname=''):
        if not nickname:
            return await ctx.send('Использование: ?[ops|osuplays] <ник/id>')
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
            value = 'Score: {:,}; Combo: {}; PP: {:,}; Acc: {}%; Rank: {}'.format(int(plays[i]['score']), combo,
                                                                                  round(float(plays[i]['pp']), 2),
                                                                                  accuracy,
                                                                                  plays[i]['rank'].replace('H', '',
                                                                                                           1))
            embed.add_field(name=name, value=value)
        await msg.edit(content=ctx.author.mention, embed=embed)

    @commands.command(name='link', usage='?link [канал]', help='Команда для генерации ссылки для создания видеозвонка'
                                                               'из голосового канала')
    async def link_(self, ctx, *, channel=None):
        if channel is None:
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.send('Сначала подключитесь к голосовому каналу')
            channel = ctx.author.voice.channel.name
        channels = await ctx.guild.fetch_channels()
        for ch in channels:
            if (ch.__class__ == discord.channel.VoiceChannel) and (ch.name.lower() == channel.lower()):
                link = 'https://discordapp.com/channels/{}/{}'.format(ctx.guild.id, ch.id)
                embed = discord.Embed(description='[Магическая ссылка для канала {}]({})'.format(ch.name, link))
                return await ctx.send(embed=embed)
        return await ctx.send('Канал с таким именем не найден')


def misc_setup(bot):
    bot.add_cog(Misc(bot))
