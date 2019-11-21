from discord.ext import commands
import discord
import httpx
from json import load
from random import choice
from html import unescape
from credentials import genius_token, shiki_client_id, shiki_client_secret
from bs4 import BeautifulSoup
import re
from utils import get_prefix
import os
import time
import git
import json
import asyncio
import datetime
import locale

proxies = {
    'all': 'http://51.68.141.240:3128'
}
locale.setlocale(locale.LC_ALL, 'ru_RU')


async def shiki_refresh(rt):
    payload = {
        'grant_type': 'refresh_token',
        'client_id': shiki_client_id,
        'client_secret': shiki_client_secret,
        'refresh_token': rt
    }
    headers = {
        'User-Agent': 'RaccoonBot'
    }
    async with httpx.AsyncClient() as client:
        req = await client.post('https://shikimori.one/oauth/token', data=payload, headers=headers)
        req = req.json()
    json.dump(req, open('resources/shiki.json', 'w+'))


async def refresh_shiki_token():
    while True:
        auth = json.load(open('resources/shiki.json', 'r+'))
        if time.time() - 3800 > auth['created_at'] + auth['expires_in']:
            await shiki_refresh(auth['refresh_token'])
        await asyncio.sleep(3600)


# noinspection PyTypeChecker
class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(refresh_shiki_token())

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError) and str(error.original):
            await ctx.send('Ошибка:\n' + str(error.original))

    @commands.command(name='raccoon', aliases=['racc'], help='Команда, которая сделает вашу жизнь лучше',
                      usage='{}[racc|raccoon]')
    async def raccoon_(self, ctx, *, msg=None):
        user = ctx.author
        if msg is None:
            msg = user.mention
        with open('resources/raccoons.txt', 'r') as f:
            raccoons = load(f)
            raccoon = choice(raccoons)
        embed = discord.Embed(color=discord.Color.dark_purple())
        embed.set_image(url=raccoon)
        return await ctx.send(msg, embed=embed)

    @commands.command(name='inspirobot', aliases=['inspire'], help='Команда для генерации "воодушевляющих" картинок',
                      usage='{}[inspire|inspirobot]')
    async def inspire_(self, ctx, *, msg=None):
        user = ctx.author
        if msg is None:
            msg = user.mention
        async with httpx.AsyncClient(proxies=proxies) as client:
            image = await client.get('http://inspirobot.me/api?generate=true')
            image = image.text
        embed = discord.Embed(color=discord.Color.dark_purple())
        embed.set_image(url=image)
        return await ctx.send(msg, embed=embed)

    @commands.command(name='fact', aliases=['facts'], help='Команда, возвращающая случайные факты',
                      usage='{}[fact|facts]')
    async def fact_(self, ctx, *, msg=None):
        user = ctx.author
        if msg is None:
            msg = user.mention
        with open('resources/facts.json', 'r') as f:
            facts = load(f)
            fact = choice(facts)
        embed = discord.Embed(color=discord.Color.dark_purple(), description=fact)
        return await ctx.send(msg, embed=embed)

    @commands.command(name='wikia', aliases=['wiki'], help='Команда для поиска статей на Fandom',
                      usage='{}[wikia|wiki] <запрос>')
    async def wikia_(self, ctx, *, query=None):
        try:
            text_channel = ctx.message.channel
            pref = await get_prefix(self.bot, ctx.message)
            if query is None:
                return await ctx.send(f'Использование: {pref}[wikia|wiki] <запрос>')
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
            async with httpx.AsyncClient() as client:
                result = await client.get(apiurl, params=params, timeout=0.5)
                result = result.json()
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
            embed = discord.Embed(color=discord.Color.dark_purple(), title='Выберите фэндом', description=embedValue)
            embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                if m.content.isdigit():
                    return (0 <= int(m.content) <= len(new_results)) and (m.channel == text_channel) and (
                            m.author == user)
                canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith(pref)) and len(
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
                async with httpx.AsyncClient() as client:
                    result = await client.get(apiurl + 'Search/List', params=params, timeout=0.5)
                    result = result.json()
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
            async with httpx.AsyncClient() as client:
                result = await client.get(apiurl + 'Articles/Details', params=params, timeout=0.5)
                result = result.json()
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
                async with httpx.AsyncClient() as client:
                    result = await client.get(apiurl + 'Articles/Details', params=params, timeout=0.5)
                    result = result.json()
                thumb = result['items'][str(page_id)]['thumbnail']
            embed = discord.Embed(color=discord.Color.dark_purple(), title=title, url=page_url, description=desc)
            if thumb is not None:
                embed.set_thumbnail(url=thumb)
            return await ctx.send(user.mention, embed=embed)
        except httpx.exceptions.ConnectTimeout:
            await ctx.send('Не удалось подключиться к Wikia')

    @commands.command(name='fandom', help='Вторая команда для поиска статей на Fandom',
                      usage='{}fandom <фэндом>')
    async def fandom_(self, ctx, *, query=None):
        try:
            text_channel = ctx.message.channel
            pref = await get_prefix(self.bot, ctx.message)
            if query is None:
                return await ctx.send(f'Использование: {pref}fandom <фэндом>')
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
            async with httpx.AsyncClient() as client:
                result = await client.get(apiurl, params=params, timeout=0.5)
                result = result.json()
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
                async with httpx.AsyncClient() as client:
                    result = await client.get(apiurl, params=params, timeout=0.5)
                    result = result.json()
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
            embed = discord.Embed(color=discord.Color.dark_purple(), title='Выберите фэндом', description=embedValue)
            embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                if m.content.isdigit():
                    return (0 <= int(m.content) <= len(new_results)) and (m.channel == text_channel) and (
                            m.author == user)
                canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith(pref)) and len(
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
            embed = discord.Embed(color=discord.Color.dark_purple(), title='Введите запрос', description='Отправьте запрос для поска по {}'.format(result['title']))
            embed.set_footer(text='Автоматическая отмена через 60 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith(pref)) and len(
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
                async with httpx.AsyncClient() as client:
                    result = await client.get(apiurl + 'Search/List', params=params, timeout=0.5)
                    result = result.json()
            except Exception as e:
                embed = discord.Embed(color=discord.Color.dark_purple(), title='Ошибка', description='Ничего не найдено')
                await choicemsg.edit(embed=embed)
                return print(e)
            if 'exception' in result.keys() or result['batches'] == 0:
                embed = discord.Embed(color=discord.Color.dark_purple(), title='Ошибка', description='Ничего не найдено')
                return await choicemsg.edit(embed=embed)
            page_id = result['items'][0]['id']
            params = {
                'ids': page_id,
                'abstract': 500,
                'width': 200,
                'height': 200
            }
            async with httpx.AsyncClient() as client:
                result = await client.get(apiurl + 'Articles/Details', params=params, timeout=0.5)
                result = result.json()
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
                async with httpx.AsyncClient() as client:
                    result = await client.get(apiurl + 'Articles/Details', params=params, timeout=0.5)
                    result = result.json()
                thumb = result['items'][str(page_id)]['thumbnail']
            embed = discord.Embed(color=discord.Color.dark_purple(), title=title, url=page_url, description=desc)
            if thumb is not None:
                embed.set_thumbnail(url=thumb)
            return await choicemsg.edit(content=user.mention, embed=embed)
        except httpx.exceptions.ConnectTimeout:
            await ctx.send('Не удалось подключиться к Wikia')

    @commands.command(aliases=['l'], usage='{}[l|lyrics] <запрос>', help='Команда для поиска текста песен')
    async def lyrics(self, ctx, *, title=None):
        pref = await get_prefix(self.bot, ctx.message)
        if title is None:
            return await ctx.send(f'Использование: {pref}[l|lyrics] <запрос>')
        text_channel = ctx.message.channel
        user = ctx.message.author
        ftitle = re.sub(r'\[([^)]+?)]', '', re.sub(r'\(([^)]+?)\)', '', title.lower()))
        params = {
            'q': ftitle
        }
        headers = {
            'Authorization': 'Bearer ' + genius_token
        }
        async with httpx.AsyncClient() as client:
            req = await client.get('https://api.genius.com/search', params=params, headers=headers)
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

            embed = discord.Embed(color=discord.Color.dark_purple(), title='Выберите трек', description=embedValue)
            embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                if m.content.isdigit():
                    return (0 <= int(m.content) <= len(new_results)) and (m.channel == text_channel) and (
                            m.author == user)
                canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith(pref)) and len(
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
            async with httpx.AsyncClient() as client:
                lyrics = await client.get(url)
            soup = BeautifulSoup(lyrics.text, 'html.parser')
            lyrics = soup.p.get_text()
            if len(lyrics) > 2000:
                lyrlist = lyrics.split('\n')
                lyrics = ''
                it = 1
                for i in range(len(lyrlist)):
                    lyrics += lyrlist[i] + '\n'
                    if i < len(lyrlist) - 1 and len(lyrics + lyrlist[i + 1]) > 2000:
                        embed = discord.Embed(color=discord.Color.dark_purple(),
                                              title='Текст {} ({})'.format(title, it), description=lyrics)
                        await ctx.send(embed=embed)
                        lyrics = ''
                        it += 1
                    elif i == len(lyrlist) - 1:
                        embed = discord.Embed(color=discord.Color.dark_purple(),
                                              title='Текст {} ({})'.format(title, it), description=lyrics)
                        return await ctx.send(embed=embed)
            else:
                embed = discord.Embed(color=discord.Color.dark_purple(),
                                      title='Текст ' + title, description=lyrics)
                return await ctx.send(embed=embed)

    @commands.command(name='link', usage='{}link [канал]', help='Команда для генерации ссылки для создания видеозвонка из голосового канала')
    async def link_(self, ctx, *, channel=None):
        if channel is None:
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.send('Сначала подключитесь к голосовому каналу')
            channel = ctx.author.voice.channel.name
        channels = await ctx.guild.fetch_channels()
        for ch in channels:
            if (ch.__class__ == discord.channel.VoiceChannel) and (ch.name.lower() == channel.lower()):
                link = 'https://discordapp.com/channels/{}/{}'.format(ctx.guild.id, ch.id)
                embed = discord.Embed(color=discord.Color.dark_purple(), description='[Магическая ссылка для канала {}]({})'.format(ch.name, link))
                return await ctx.send(embed=embed)
        return await ctx.send('Канал с таким именем не найден')

    @commands.command(name='shikimori', aliases=['shiki'], usage='{}shikimori <запрос>', help='Команда для поиска аниме на шикимори')
    async def shiki_(self, ctx, *, query=''):
        pref = await get_prefix(self.bot, ctx.message)
        if not query:
            return await ctx.send(f'Использование {pref}[shikimori|shiki] <запрос>')
        auth = json.load(open('resources/shiki.json', 'r'))
        at = '{token_type} {access_token}'.format(**auth)
        headers = {
            'User-Agent': 'RaccoonBot',
            'Authorization': at
        }
        params = {
            'limit': 10,
            'search': query,
            'order': 'popularity'
        }
        async with httpx.AsyncClient() as client:
            results = await client.get('https://shikimori.one/api/animes', headers=headers, params=params)
            results = results.json()
        embed = discord.Embed(color=discord.Color.dark_purple())
        if not results:
            embed.description = 'Ничего не найдено'
            return await ctx.send(embed=embed)
        if len(results) > 1:
            embed.title = 'Выберите аниме'
            embed.description = '\n'.join(
                f'{i + 1}. {results[i]["russian"]} [{results[i]["kind"].capitalize() + " (Анонс)" * (results[i]["status"] == "anons")}]' for i in range(len(results)))
            embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choicemsg = await ctx.send(embed=embed)
            canc = False

            def verify(m):
                nonlocal canc
                if m.content.isdigit():
                    return (0 <= int(m.content) <= len(results)) and (m.channel == ctx.channel) and (m.author == ctx.author)
                canc = (m.channel == ctx.channel) and (m.author == ctx.author) and (m.content.startswith(pref)) and len(m.content) > len(pref)
                return canc

            msg = await self.bot.wait_for('message', check=verify, timeout=30)
            if canc or int(msg.content) == 0:
                return await choicemsg.delete()
            result = results[int(msg.content) - 1]
            await choicemsg.delete()
        else:
            result = results[0]
        title = result['russian'] if result['russian'] else result['name']
        embed = discord.Embed(color=discord.Color.dark_purple(), title=title, url='https://shikimori.one' + result['url'])
        async with httpx.AsyncClient() as client:
            info = await client.get(f'https://shikimori.one/api/animes/{result["id"]}', headers=headers)
            info = info.json()
        embed.set_thumbnail(url='https://shikimori.one' + info['image']['original'])
        if not info['anons']:
            episodes = '{episodes_aired}/{episodes}'.format(**info) if info['ongoing'] else info['episodes']
            embed.add_field(name='Эпизоды', value=episodes, inline=False)
        kind = info['kind'].capitalize() + ' (анонс)' if info['anons'] else info['kind'].capitalize()
        embed.add_field(name='Формат', value=kind, inline=False)
        if any(studio['real'] for studio in info['studios']):
            studios = []
            for studio in info['studios']:
                if studio['real']:
                    studios += [studio['filtered_name']]
            embed.add_field(name='Студии', value=', '.join(studios), inline=False)
        if info['japanese']:
            embed.add_field(name='Оригинальное название', value=info['japanese'][0], inline=False)
        if info['genres']:
            embed.add_field(name='Жанры', value=', '.join(gen['russian'] for gen in info['genres']), inline=False)
        if info['score'] and not info['anons']:
            embed.add_field(name='Оценка', value=info['score'], inline=False)
        if info['anons']:
            if info['aired_on']:
                date = datetime.datetime.strptime(info['aired_on'][:-6], '%Y-%m-%dT%H:%M:%S.%f').strftime('%a, %d %b %Y %H:%M')
                embed.add_field(name='Дата начала показа', value=date, inline=False)
        else:
            if info['released_on'] or info['aired_on']:
                date = ('Дата окончания показа', info['released_on']) if info['released_on'] and not info['ongoing'] else ('Дата начала показа', info['aired_on'])
                date = date[0], datetime.datetime.strptime(date[1], '%Y-%m-%d').strftime('%d %b %Y')
                embed.add_field(name=date[0], value=date[1], inline=False)
            if info['next_episode_at']:
                date = datetime.datetime.strptime(info['next_episode_at'][:-6], '%Y-%m-%dT%H:%M:%S.%f').strftime('%a, %d %b %Y %H:%M')
                embed.add_field(name='Дата выхода следующего эпизода', value=date, inline=False)
        if info['description']:
            desc = info['description']
            desc = re.sub(r'\[([^)]+?)]', '', desc)
            if len(desc) > 300:
                desc = desc[:300] + '...'
            embed.add_field(name='Описание', value=desc, inline=False)
        return await ctx.send(embed=embed)

    @commands.command(name='changelog', usage='{}changelog', help='Команда, показывающая последние обновления бота')
    async def changelog_(self, ctx):
        repo = git.Repo(os.getcwd())
        commits = list(repo.iter_commits('master'))
        cnt = 0
        unique = []
        embed = discord.Embed(color=discord.Color.dark_purple(), title='Последние изменения', description='')
        for commit in commits:
            if commit.message not in unique:
                unique.append(commit.message)
                cnt += 1
                embed.description += f'\n{time.strftime("%d-%m-%Y", time.gmtime(commit.authored_date - commit.author_tz_offset))}: {commit.message.strip()}'
            if cnt == 20:
                return await ctx.send(embed=embed)


def misc_setup(bot):
    bot.add_cog(Misc(bot))
