import math
import re
import random
import json
import aiohttp
import asyncio
import pickle
import os

from pathvalidate import validate_filename, ValidationError
from tts import *
from time import time
import discord
import lavalink
from discord.ext import commands
from bs4 import BeautifulSoup
from utils import form, get_prefix, get_color
from credentials import main_password, discord_pers_id, main_web_addr, gachi_things, genius_token, dev, discord_guild_id,\
    discord_inter_guild_id, discord_inter_afk_channel_id, discord_dev_guild_id, discord_dev_afk_channel_id, vk_audio_token

vk_album_rx = re.compile(r'https?://(?:www\.)?vk.com/(audios-?[0-9]+\?(?:section=playlists&)?z=audio_playlist-?[0-9]+_[0-9]+|music/album/-?[0-9]+_[0-9]+|music/playlist/-?[0-9]+_[0-9]+)')
vk_pers_rx = re.compile(r'https?://(?:www\.)?vk.com/audios-?[0-9]+')
url_rx = re.compile(r'https?://(?:www\.)?.+')
agent = 'KateMobileAndroid/52.1 lite-445 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)'


# noinspection PyProtectedMember
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_guild = discord_dev_guild_id if dev else discord_inter_guild_id
        self.afk_channel = discord_dev_afk_channel_id if dev else discord_inter_afk_channel_id

        if not hasattr(bot, 'lavalink'):
            addr = main_web_addr if dev else '127.0.0.1'
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node(addr, 2333, main_password, 'ru', 'default-node')
            bot.add_listener(bot.lavalink.voice_update_handler, 'on_socket_response')

        self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        saved = json.load(open('resources/saved.json', 'r'))
        while True:
            # noinspection PyUnresolvedReferences
            try:
                for guild in self.bot.guilds:
                    player = self.bot.lavalink.player_manager.create(guild.id, 'ru')
                    if str(guild.id) not in saved.keys():
                        saved[str(guild.id)] = {}
                        saved[str(guild.id)]['volume'] = 100
                        saved[str(guild.id)]['shuffle'] = False
                    else:
                        await player.set_volume(saved[str(guild.id)]['volume'])
                        player.shuffle = saved[str(guild.id)]['shuffle']
                    json.dump(saved, open('resources/saved.json', 'w'))
            except lavalink.exceptions.NodeException:
                await asyncio.sleep(1)
            else:
                print('Initialized!')
                break

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        saved = json.load(open('resources/saved.json', 'r'))
        saved[str(guild.id)] = {}
        saved[str(guild.id)]['volume'] = 100
        saved[str(guild.id)]['shuffle'] = False
        json.dump(saved, open('resources/saved.json', 'w'))
        return

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not after.channel and before.channel:
            if any(self.bot.user in channel.members and all(member.bot for member in channel.members) for channel in member.guild.voice_channels):
                await self.connect_to(member.guild.id, None)
        if member.guild.id == self.afk_guild and not member.bot:
            if after.channel and after.channel.id == self.afk_channel and before.channel and before.channel.id != after.channel.id:
                return await member.send('Вы были перемещены в АФК-канал')

    class MusicCommandError(commands.CommandInvokeError):
        pass

    def cog_unload(self):
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        guild_check = ctx.guild is not None
        if guild_check:
            await self.ensure_voice(ctx)
        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError) and str(error.original):
            if isinstance(error, self.MusicCommandError):
                return await ctx.send(str(error.original))
            return await ctx.send('Ошибка:\n' + str(error.original))

    async def connect_to(self, guild_id: int, channel_id):
        ws = self.bot._connection._get_websocket(guild_id)
        await ws.voice_state(str(guild_id), channel_id)

    async def vk_album_add(self, url, ctx, force=False):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        album = re.search(r'-?[0-9]+_[0-9]+', url)
        if album:
            album = album.group()
        else:
            return discord.Embed(color=discord.Color.blue(), title='❌Плейлист не найден')
        user, aid = album.split('_')
        headers = {
            'User-Agent': agent
        }
        params = {
            'access_token': vk_audio_token,
            'v': '5.999',
            'owner_id': user,
            'playlist_id': aid
        }
        async with aiohttp.ClientSession() as client:
            res = await client.get('https://api.vk.com/method/audio.get', headers=headers, params=params)
            playlist = await client.get('https://api.vk.com/method/audio.getPlaylistById', headers=headers, params=params)
            res = await res.json()
            playlist = await playlist.json()
        if 'error' in res.keys() and res['error']['error_code'] == 201:
            return discord.Embed(color=discord.Color.blue(), title='❌Нет доступа к аудио пользователя')
        res = res['response']
        playlist = playlist['response']
        items = reversed(res['items']) if force else res['items']
        added = 0
        first = False
        for item in items:
            if item['url']:
                results = await player.node.get_tracks(item['url'])
                track = results['tracks'][0]
                track['info']['author'] = item['artist']
                track['info']['title'] = f'{item["artist"]} - {item["title"]}'
                track['info']['uri'] = f'https://vk.com/music/album/{album}'
                player.add(requester=ctx.author.id, track=track, index=0) if force else player.add(requester=ctx.author.id, track=track)
                if not first:
                    await player.play()
                    first = True
                added += 1
        return discord.Embed(color=discord.Color.blue(), title='✅Плейлист добавлен', description=f'{playlist["title"]} - {added} {form(added, ["трек", "трека", "треков"])}')

    async def vk_pers_add(self, url, ctx, force=False):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        user = re.search(r'-?[0-9]+', url)
        if user:
            user = user.group()
        else:
            return discord.Embed(color=discord.Color.blue(), title='❌Плейлист не найден')
        headers = {
            'User-Agent': agent
        }
        params = {
            'access_token': vk_audio_token,
            'v': '5.999',
            'owner_id': user,
            'need_user': 1
        }
        async with aiohttp.ClientSession() as client:
            playlist = await client.get('https://api.vk.com/method/audio.get', headers=headers, params=params)
            playlist = await playlist.json()
        if 'error' in playlist.keys() and playlist['error']['error_code'] == 201:
            return discord.Embed(color=discord.Color.blue(), title='❌Нет доступа к аудио пользователя')
        playlist = playlist['response']
        items = playlist['items']
        user_info = items.pop(0)
        if force:
            items = reversed(items)
        added = 0
        first = False
        for item in items:
            if item['url']:
                results = await player.node.get_tracks(item['url'])
                track = results['tracks'][0]
                track['info']['author'] = item['artist']
                track['info']['title'] = f'{item["artist"]} - {item["title"]}'
                track['info']['uri'] = f'https://vk.com/audios/{user}'
                player.add(requester=ctx.author.id, track=track, index=0) if force else player.add(requester=ctx.author.id, track=track)
                if not first:
                    await player.play()
                    first = True
                added += 1
        return discord.Embed(color=discord.Color.blue(), title='✅Плейлист добавлен', description=f'Аудиозаписи {user_info["name_gen"]} - {added} {form(added, ["трек", "трека", "треков"])}')

    @commands.command(aliases=['p'], usage='{}[p|play] <ссылка/название>', help='Команда для проигрывания музыки')
    async def play(self, ctx, *, query: str = ''):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        pref = await get_prefix(self.bot, ctx.message)
        if not query:
            if player.paused:
                await player.set_pause(False)
                return await ctx.send('⏯ | Воспроизведение возобновлено')
            if not player.is_playing and (player.queue or player.current):
                return await player.play()
            else:
                return await ctx.send(f'Использование: {pref}[p|play] <ссылка/название>')
        query = query.strip('<>')
        if vk_album_rx.match(query):
            embed = await self.vk_album_add(query, ctx)
        elif vk_pers_rx.match(query):
            embed = await self.vk_pers_add(query, ctx)
        else:
            if not url_rx.match(query):
                query = f'ytsearch:{query}'
            results = await player.node.get_tracks(query)
            if not results or not results['tracks']:
                return await ctx.send('Ничего не найдено')
            embed = discord.Embed(color=get_color(results['tracks'][0]['info']['uri']))
            if results['loadType'] == 'PLAYLIST_LOADED':
                tracks = results['tracks']
                for track in tracks:
                    player.add(requester=ctx.author.id, track=track)
                embed.title = '✅Плейлист добавлен'
                embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} {form(len(tracks), ["трек", "трека", "треков"])}'
            else:
                if url_rx.match(query):
                    track = results['tracks'][0]
                else:
                    text_channel = ctx.message.channel
                    user = ctx.message.author
                    tracks = results['tracks']
                    embedValue = ''
                    length = 10 if len(tracks) > 10 else len(tracks)
                    for i in range(length):
                        title = tracks[i]['info']['title']
                        embedValue += '{}: {}\n'.format(i + 1, title)
                    choiceEmbed = discord.Embed(title="Выберите трек", description=embedValue,
                                                color=discord.Color.red())
                    choiceEmbed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
                    choice = await ctx.send(embed=choiceEmbed, delete_after=30)
                    canc = False

                    def verify(m):
                        nonlocal canc
                        if m.content.isdigit():
                            return (0 <= int(m.content) < 11) and (m.channel == text_channel) and (m.author == user)
                        canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith(pref)) and len(
                            m.content) > 1
                        return canc

                    msg = await self.bot.wait_for('message', check=verify, timeout=30)
                    if canc or int(msg.content) == 0:
                        return await choice.delete()
                    track = tracks[int(msg.content) - 1]
                    await choice.delete()
                embed.title = '✅Трек добавлен'
                embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'
                player.add(requester=ctx.author.id, track=track)
        await ctx.send(embed=embed)
        if not player.is_playing:
            await player.play()

    @commands.command(aliases=['fp'], usage='{}[fp|force] <ссылка/название>', help='Команда для добавления трека в начало очереди')
    async def force(self, ctx, *, query: str = ''):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        pref = await get_prefix(self.bot, ctx.message)
        if not query:
            return await ctx.send(f'Использование: {pref}[fp|force] <ссылка/название>')
        query = query.strip('<>')
        if vk_album_rx.match(query):
            embed = await self.vk_album_add(query, ctx, force=True)
        elif vk_pers_rx.match(query):
            embed = await self.vk_pers_add(query, ctx, force=True)
        else:
            if not url_rx.match(query):
                query = f'ytsearch:{query}'
            results = await player.node.get_tracks(query)
            if not results or not results['tracks']:
                return await ctx.send('Ничего не найдено')
            embed = discord.Embed(color=get_color(results['tracks'][0]['info']['uri']))
            if results['loadType'] == 'PLAYLIST_LOADED':
                tracks = results['tracks']
                for track in reversed(tracks):
                    player.add(requester=ctx.author.id, track=track, index=0)
                embed.title = '✅Плейлист добавлен'
                embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)} {form(len(tracks), ["трек", "трека", "треков"])}'
            else:
                if url_rx.match(query):
                    track = results['tracks'][0]
                else:
                    text_channel = ctx.message.channel
                    user = ctx.message.author
                    tracks = results['tracks']
                    embedValue = ''
                    length = 10 if len(tracks) > 10 else len(tracks)
                    for i in range(length):
                        title = tracks[i]['info']['title']
                        embedValue += '{}: {}\n'.format(i + 1, title)
                    choiceEmbed = discord.Embed(title="Выберите трек", description=embedValue,
                                                color=discord.Color.red())
                    choiceEmbed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
                    choice = await ctx.send(embed=choiceEmbed, delete_after=30)
                    canc = False

                    def verify(m):
                        nonlocal canc
                        if m.content.isdigit():
                            return (0 <= int(m.content) < 11) and (m.channel == text_channel) and (m.author == user)
                        canc = (m.channel == text_channel) and (m.author == user) and (m.content.startswith(pref)) and len(
                            m.content) > 1
                        return canc

                    msg = await self.bot.wait_for('message', check=verify, timeout=30)
                    if canc or int(msg.content) == 0:
                        return await choice.delete()
                    track = tracks[int(msg.content) - 1]
                    await choice.delete()
                embed.title = '✅Трек добавлен'
                embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'
                player.add(requester=ctx.author.id, track=track, index=0)
        await ctx.send(embed=embed)
        if not player.is_playing:
            await player.play()

    @commands.command(usage='{}[gachi|gachibass] [кол-во]', help='Команда для проигрывания правильных версий музыки',
                      aliases=['gachi'])
    async def gachibass(self, ctx, amt: int = 1):
        if amt > 100:
            return await ctx.send('Нет')
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        with open('resources/gachi.txt', 'r') as f:
            tracks = json.load(f)
        tracks = random.sample(tracks, amt)
        player.add(requester=ctx.author.id, track=tracks.pop(0))
        await ctx.send(random.choice(gachi_things))
        if not player.is_playing:
            await player.play()
        for track in tracks:
            player.add(requester=ctx.author.id, track=track)

    @commands.command(help='Зачем', usage='{}why [кол-во]\n(Не используйте, пожалуйста)', hidden=True)
    async def why(self, ctx, amt: int = 1):
        if ctx.guild.id == int(discord_guild_id):
            player = self.bot.lavalink.player_manager.get(ctx.guild.id)
            if (int(amt) > 20) and (ctx.author.id != discord_pers_id):
                return await ctx.send('Нет')
            query = 'why.mp3'
            results = await player.node.get_tracks(query)
            track = results['tracks'][0]
            for i in range(int(amt)):
                player.add(requester=ctx.author.id, track=track)
            if not player.is_playing:
                await player.play()

    @commands.command(help='Команда для преобразования текста в голос', usage='{}tts <текст>')
    async def tts(self, ctx, *, text):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not text:
            pref = get_prefix(self.bot, ctx.message)
            return await ctx.send(f'Использование: {pref}tts <сообщение>')
        ts = time()
        name = 'output{}.mp3'.format(ts)
        await create_mp3(text, name)
        query = 'outputs/'+name
        results = await player.node.get_tracks(query)
        track = results['tracks'][0]
        player.add(requester=ctx.author.id, track=track)
        if not player.is_playing:
            await player.play()

    @commands.command(help='Команда для перемотки музыки', usage='{}seek <время в секундах>')
    async def seek(self, ctx, *, seconds: int):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        track_time = player.position + (seconds * 1000)
        await player.seek(track_time)

        await ctx.message.add_reaction('👌')

    @commands.command(help='Команда для пропуска трека', usage='{}skip')
    async def skip(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Ничего не играет')

        await player.skip()
        if player.queue or player.current:
            while not player.is_playing:
                pass
            embed = discord.Embed(color=get_color(player.current.uri), title='⏩Дальше', description=f'[{player.current.title}]({player.current.uri})')
            await ctx.send(embed=embed)
        await ctx.message.add_reaction('👌')

    @commands.command(help='Команда для остановки плеера и очистки очереди', usage='{}stop')
    async def stop(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        player.queue.clear()
        await player.stop()
        await self.connect_to(ctx.guild.id, None)
        await ctx.message.add_reaction('👌')

    @commands.command(help='Команда для очистки очереди плеера', usage='{}clear')
    async def clear(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.queue:
            return await ctx.send('Очередь пустая')

        player.queue.clear()
        await ctx.message.add_reaction('👌')

    @commands.command(aliases=['n', 'np', 'playing', 'current'], usage='{}[n|np|now|playing|current]',
                      help='Команда для отображения текущего трека')
    async def now(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.current:
            return await ctx.send('Ничего не играет')
        position = lavalink.utils.format_time(player.position)
        if player.current.stream:
            duration = '🔴 LIVE'
        else:
            duration = lavalink.utils.format_time(player.current.duration)
        song = f'[{player.current.title}]({player.current.uri})\n({position}/{duration})'
        embed = discord.Embed(color=get_color(player.current.uri),
                              title='Сейчас играет', description=song)
        await ctx.send(embed=embed)

    @commands.command(aliases=['nl', 'npl', 'cl'], usage='{}[nl|npl|cl|currentlyrics]',
                      help='Команда для отображения текста текущего трека')
    async def currentlyrics(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.current:
            return await ctx.send('Ничего не играет')
        title = player.current.title
        ftitle = re.sub(r'\[([^)]+?)]', '', re.sub(r'\(([^)]+?)\)', '', title.lower())).replace('lyric video', '').replace('lyrics video', '').replace('lyrics', '')
        params = {
            'q': ftitle
        }
        headers = {
            'Authorization': 'Bearer ' + genius_token
        }
        async with aiohttp.ClientSession() as client:
            req = await client.get('https://api.genius.com/search', params=params, headers=headers)
            req = await req.json()
        result = req['response']['hits']
        if len(result) == 0:
            return await ctx.send('Песня не найдена')
        else:
            result = result[0]
            if result['type'] == 'song':
                if result['result']['lyrics_state'] == 'complete':
                    url = result['result']['url']
                    title = '{} - {}'.format(result['result']['primary_artist']['name'], result['result']['title'])
                    async with aiohttp.ClientSession() as client:
                        lyrics = await client.get(url)
                        lyrics = await lyrics.text()
                    soup = BeautifulSoup(lyrics, 'html.parser')
                    lyrics = soup.p.get_text()
                    if len(lyrics) > 4000:
                        return await ctx.send('Слишком длинный текст, скорее всего это не текст песни')
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
                                              title='Текст '+title, description=lyrics)
                        return await ctx.send(embed=embed)
                else:
                    return await ctx.send('Текст песни не найден')
            else:
                return await ctx.send('Текст песни не найден')

    @commands.command(aliases=['q', 'list'], help='Команда для отображения очереди воспроизведения',
                      usage='{}[q|queue|list]')
    async def queue(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        items_per_page = 10
        local_queue = player.queue.copy()
        pages = math.ceil(len(player.queue) / items_per_page)
        queue_list = ''
        for index, track in enumerate(local_queue[0:10], start=0):
            queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
        embed = discord.Embed(color=discord.Color.dark_purple(),
                              description=f'**{len(local_queue)} {form(len(local_queue), ["трек", "трека", "треков"])}**\n\n{queue_list}')
        msg = await ctx.send(embed=embed)

        def verify(react, member):
            return (react.message.id == msg.id) and (member != self.bot.user)

        page = 1
        await msg.add_reaction('❌')
        await msg.add_reaction('🔄')
        if pages > 1:
            await msg.add_reaction('▶')
            await msg.add_reaction('⏭')
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=verify, timeout=1200)
            except asyncio.TimeoutError:
                return
            if str(reaction.emoji) == '▶' and page < pages:
                page += 1
                start = (page - 1) * items_per_page
                end = start + items_per_page
                queue_list = ''
                for index, track in enumerate(local_queue[start:end], start=start):
                    queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                embed = discord.Embed(color=discord.Color.dark_purple(),
                                      description=f'**{len(local_queue)} {form(len(local_queue), ["трек", "трека", "треков"])}**\n\n{queue_list}')
                await msg.edit(embed=embed)
                await reaction.remove(user)
                await msg.add_reaction('⏮')
                await msg.add_reaction('◀')
                if page == pages:
                    await msg.remove_reaction('▶', self.bot.user)
                    await msg.remove_reaction('⏭', self.bot.user)
                await msg.add_reaction('❌')
            elif str(reaction.emoji) == '⏭' and page < pages:
                page = pages
                start = (page - 1) * items_per_page
                end = start + items_per_page
                queue_list = ''
                for index, track in enumerate(local_queue[start:end], start=start):
                    queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                embed = discord.Embed(color=discord.Color.dark_purple(),
                                      description=f'**{len(local_queue)} {form(len(local_queue), ["трек", "трека", "треков"])}**\n\n{queue_list}')
                await msg.edit(embed=embed)
                await reaction.remove(user)
                await msg.add_reaction('⏮')
                await msg.add_reaction('◀')
                await msg.add_reaction('❌')
                await msg.remove_reaction('▶', self.bot.user)
                await msg.remove_reaction('⏭', self.bot.user)
            elif str(reaction.emoji) == '◀' and page > 1:
                page -= 1
                start = (page - 1) * items_per_page
                end = start + items_per_page
                queue_list = ''
                for index, track in enumerate(local_queue[start:end], start=start):
                    queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                embed = discord.Embed(color=discord.Color.dark_purple(),
                                      description=f'**{len(local_queue)} {form(len(local_queue), ["трек", "трека", "треков"])}**\n\n{queue_list}')
                await msg.edit(embed=embed)
                await reaction.remove(user)
                if page == 1:
                    await msg.remove_reaction('⏮', self.bot.user)
                    await msg.remove_reaction('◀', self.bot.user)
                await msg.add_reaction('▶')
                await msg.add_reaction('⏭')
                await msg.add_reaction('❌')
            elif str(reaction.emoji) == '⏮' and page > 1:
                page = 1
                start = (page - 1) * items_per_page
                end = start + items_per_page
                queue_list = ''
                for index, track in enumerate(local_queue[start:end], start=start):
                    queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                embed = discord.Embed(color=discord.Color.dark_purple(),
                                      description=f'**{len(local_queue)} {form(len(local_queue), ["трек", "трека", "треков"])}**\n\n{queue_list}')
                await msg.edit(embed=embed)
                await reaction.remove(user)
                await msg.add_reaction('▶')
                await msg.add_reaction('⏭')
                await msg.add_reaction('❌')
                await msg.remove_reaction('⏮', self.bot.user)
                await msg.remove_reaction('◀', self.bot.user)
            elif str(reaction.emoji) == '❌':
                return await msg.delete()
            elif str(reaction.emoji) == '🔄':
                items_per_page = 10
                local_queue = player.queue.copy()
                pages = math.ceil(len(player.queue) / items_per_page)
                queue_list = ''
                for index, track in enumerate(local_queue[0:10], start=0):
                    queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                embed = discord.Embed(color=discord.Color.dark_purple(),
                                      description=f'**{len(local_queue)} {form(len(local_queue), ["трек", "трека", "треков"])}**\n\n{queue_list}')
                page = 1
                await msg.edit(embed=embed)
                await msg.clear_reactions()
                await msg.add_reaction('❌')
                await msg.add_reaction('🔄')
                if pages > 1:
                    await msg.add_reaction('▶')
                    await msg.add_reaction('⏭')
            else:
                await reaction.remove(user)

    @commands.command(usage='{}save <название>', help='Команда для сохранения текущей очереди в плейлист')
    async def save(self, ctx, *, name=None):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue and not player.current:
            return await ctx.send('Очередь пустая')
        if not name:
            return await ctx.send('Укажите название для сохраняемого плейлиста')
        playlists = os.listdir(os.path.join('resources', 'playlists'))
        playlist_name = f'{ctx.author.id}_{name.lower()}'
        try:
            validate_filename(playlist_name)
        except ValidationError:
            return await ctx.send('Запрещенные символы в названии плейлиста')
        if playlist_name in playlists:
            pref = await get_prefix(self.bot, ctx.message)
            return await ctx.send(f'Плейлист с таким названием уже существует\nДля удаления плейлиста используйте {pref}delete <название>')
        if len(name) > 100:
            return await ctx.send('Слишком длинное название для плейлиста')
        local_queue = player.queue.copy() if player.queue else []
        if player.current:
            local_queue.insert(0, player.current)
        with open(os.path.join('resources', 'playlists', playlist_name), 'wb+') as queue_file:
            pickle.dump(local_queue, queue_file)
        ln = len(local_queue)
        return await ctx.send(f'Плейлист {name} [{ln} {form(ln, ["трек", "трека", "треков"])}] сохранен')

    @commands.command(usage='{}load <название>', help='Команда для загрузки плейлиста в очередь')
    async def load(self, ctx, *, name=None):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not name:
            return await ctx.send('Укажите название для загружаемого плейлиста')
        playlists = os.listdir(os.path.join('resources', 'playlists'))
        playlist_name = f'{ctx.author.id}_{name.lower()}'
        try:
            validate_filename(playlist_name)
        except ValidationError:
            return await ctx.send('Запрещенные символы в названии плейлиста')
        if playlist_name not in playlists:
            pref = await get_prefix(self.bot, ctx.message)
            return await ctx.send(f'Нет плейлиста с таким названием\nДля просмотра своих плейлистов используйте {pref}playlists')
        with open(os.path.join('resources', 'playlists', playlist_name), 'rb') as queue_file:
            queue = pickle.load(queue_file)
        for track in queue:
            player.add(requester=ctx.author.id, track=track)
        ln = len(queue)
        await ctx.send(f'Плейлист {name} [{ln} {form(ln, ["трек", "трека", "треков"])}] добавлен в очередь')
        if not player.is_playing:
            await player.play()

    @commands.command(usage='{}delete <название>', help='Команда для удаления сохраненного плейлиста')
    async def delete(self, ctx, *, name=None):
        if not name:
            return await ctx.send('Укажите название для загружаемого плейлиста')
        playlists = os.listdir(os.path.join('resources', 'playlists'))
        playlist_name = f'{ctx.author.id}_{name.lower()}'
        try:
            validate_filename(playlist_name)
        except ValidationError:
            return await ctx.send('Запрещенные символы в названии плейлиста')
        if playlist_name not in playlists:
            pref = await get_prefix(self.bot, ctx.message)
            return await ctx.send(f'Нет плейлиста с таким названием\nДля просмотра своих плейлистов используйте {pref}playlists')
        os.remove(os.path.join('resources', 'playlists', playlist_name))
        return await ctx.send(f'Плейлист {name} удален!')

    @commands.command(usage='{}playlists', help='Команда для просмотра списка сохраненных плейлистов')
    async def playlists(self, ctx):
        playlists = os.listdir(os.path.join('resources', 'playlists'))
        personal = []
        for playlist in playlists:
            user_id, name = playlist.split('_', 1)
            if int(user_id) == ctx.author.id:
                personal.append(name)
        if not personal:
            return await ctx.send('У вас нет сохраненных плейлистов!')
        embed = discord.Embed(color=discord.Color.dark_purple(), title='Сохраненные плейлисты',
                              description='\n'.join([f'{i+1}. {name}' for i, name in enumerate(personal)]))
        return await ctx.send(embed=embed)

    @commands.command(aliases=['resume'], usage='{}[pause|resume]',
                      help='Команда для приостановки или продолжения поспроизведения воспроизведения')
    async def pause(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        await player.set_pause(not player.paused)
        await ctx.message.add_reaction('⏸' if player.paused else '▶')

    @commands.command(aliases=['vol'], help='Команда для изменения громкости плеера',
                      usage='{}[vol|volume] <громкость(1-1000)>')
    async def volume(self, ctx, volume: int = None):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not volume:
            return await ctx.send(f'🔈 | {player.volume}%')
        await player.set_volume(volume)
        await ctx.message.add_reaction('👌')
        vols = json.load(open('resources/saved.json', 'r'))
        vols[str(ctx.guild.id)]['volume'] = player.volume
        json.dump(vols, open('resources/saved.json', 'w'))

    @commands.command(help='Команда для включения/выключения перемешивания очереди', usage='{}shuffle')
    async def shuffle(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        player.shuffle = not player.shuffle
        shffl = json.load(open('resources/saved.json', 'r'))
        shffl[str(ctx.guild.id)]['shuffle'] = player.shuffle
        json.dump(shffl, open('resources/saved.json', 'w'))
        await ctx.send('🔀 | Перемешивание ' + ('включено' if player.shuffle else 'выключено'))

    @commands.command(help='Команда для перемешивания текущей очереди', aliases=['qs'], usage='{}[qshuffle|qs]')
    async def qshuffle(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        random.shuffle(player.queue)
        await ctx.message.add_reaction('👌')

    @commands.command(aliases=['loop'], usage='{}[loop/repeat]',
                      help='Команда для включения/выключения зацикливания очереди')
    async def repeat(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        player.repeat = not player.repeat
        await ctx.send('🔁 | Циклическое воспроизведение ' + ('включено' if player.repeat else 'выключено'))

    @commands.command(help='Команда для удаления трека из очереди', usage='{}remove <индекс>')
    async def remove(self, ctx, index: int):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        if index > len(player.queue) or index < 1:
            return await ctx.send(f'Индекс дожен быть **между** 1 и {len(player.queue)}')
        removed = player.queue.pop(index - 1)
        embed = discord.Embed(color=discord.Color.dark_purple(), title='❌Трек удален', description=f'[{removed.title}]({removed.uri})')
        await ctx.send(embed=embed)

    @commands.command(aliases=['dc', 'leave'], help='Команда для отключения бота от голосового канала',
                      usage='{}[dc|disconnect|leave]')
    async def disconnect(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_connected:
            return await ctx.send('Не подключен к голосовому каналу')
        player.queue.clear()
        await player.stop()
        await self.connect_to(ctx.guild.id, None)
        await ctx.message.add_reaction('👌')

    @commands.command(aliases=['connect', 'c'], usage='{}[c|connect|join]',
                      help='Команда для подключения бота к голосовому каналу')
    async def join(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if player.channel_id:
            if ctx.author.voice.channel.id == int(player.channel_id):
                return await ctx.send('Уже подключен к голосовому каналу')
        await self.connect_to(ctx.guild.id, ctx.author.voice.channel.id)
        await ctx.message.add_reaction('👌')

    async def ensure_voice(self, ctx):
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        should_connect = ctx.command.name in ('play', 'force', 'join', 'why', 'tts', 'join', 'gachibass', 'move', 'load')
        ignored = ctx.command.name in ['volume', 'shuffle', 'playlists', 'delete']
        if ignored:
            return
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise self.MusicCommandError('Сначала подключитесь к голосовому каналу')
        if not player.is_connected:
            if not should_connect:
                raise self.MusicCommandError('Я не подключен к каналу')
            permissions = ctx.author.voice.channel.permissions_for(ctx.me)
            if not permissions.connect or not permissions.speak:
                raise self.MusicCommandError('I need the `CONNECT` and `SPEAK` permissions.')
            player.store('channel', ctx.channel.id)
            await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
        else:
            if int(player.channel_id) == ctx.author.voice.channel.id and should_connect:
                return
            if should_connect:
                return await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise self.MusicCommandError('Мы в разных голосовых каналах')


def music_setup(bot):
    bot.add_cog(Music(bot))
