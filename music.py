from asyncio import sleep
from json import load, dump
from os import path, listdir, remove
from pickle import load as pload, dump as pdump
from random import sample, choice, shuffle
from textwrap import wrap

from bs4 import BeautifulSoup
from credentials import main_password, main_web_addr, gachi_things, genius_token, dev
from discord.ext.commands import Cog, command, Bot
from lavalink import Client, NodeException, format_time, add_event_hook, TrackEndEvent
from pathvalidate import validate_filename, ValidationError

from music_funcs import *


# noinspection PyProtectedMember
class Music(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        addr = main_web_addr if dev else '127.0.0.1'
        lc = Client(bot.user.id, player=Player)
        lc.add_node(addr, 2333, main_password, 'ru', 'default-node')
        bot.add_listener(lc.voice_update_handler, 'on_socket_response')
        self.lavalink = lc

        self.bot.loop.create_task(self.initialize())
        add_event_hook(update_queues, event=TrackEndEvent)

    async def initialize(self):
        saved = load(open('resources/saved.json', 'r'))
        while True:
            try:
                for guild in self.bot.guilds:
                    player = self.lavalink.player_manager.create(guild.id, 'ru')
                    if str(guild.id) not in saved.keys():
                        saved[str(guild.id)] = {}
                        saved[str(guild.id)]['volume'] = 100
                        saved[str(guild.id)]['shuffle'] = False
                    else:
                        await player.set_volume(saved[str(guild.id)]['volume'])
                        player.shuffle = saved[str(guild.id)]['shuffle']
                    dump(saved, open('resources/saved.json', 'w'))
            except NodeException:
                await sleep(1)
            else:
                print('Initialized!')
                break

    @Cog.listener()
    async def on_guild_join(self, guild):
        saved = load(open('resources/saved.json', 'r'))
        saved[str(guild.id)] = {}
        saved[str(guild.id)]['volume'] = 100
        saved[str(guild.id)]['shuffle'] = False
        dump(saved, open('resources/saved.json', 'w'))

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not after.channel and before.channel:
            if any(self.bot.user in channel.members and all(member.bot for member in channel.members) for channel in member.guild.voice_channels):
                await self.connect_to(member.guild.id, None)

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user != self.bot.user:
            for queue in queues:
                if queue.message.id == reaction.message.id:
                    return await queue.react(reaction)

    def cog_unload(self):
        self.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        guild_check = ctx.guild is not None
        if guild_check:
            await self.ensure_voice(ctx)
        return guild_check

    async def connect_to(self, guild_id, channel_id):
        ws = self.bot._connection._get_websocket(guild_id)
        await ws.voice_state(str(guild_id), channel_id)

    async def _play(self, ctx, query, force):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        index = 0 if force else None
        if not query:
            if player.paused:
                await player.set_pause(False)
                return await ctx.send('⏯ | Воспроизведение возобновлено')
            if not player.is_playing and (player.queue or player.current):
                return await player.play()
            else:
                return await ctx.send(f'Использование: {ctx.prefix}[p|play] <ссылка/название>')
        res = await get_track(player, query)
        if not isinstance(res, (Track, Playlist, dict, list)):
            if isinstance(res, Embed):
                return await ctx.send(embed=res)
            return await ctx.send(res)
        color = get_embed_color(query)
        embed = Embed(color=color)
        if isinstance(res, dict):
            embed.title = '✅Трек добавлен'
            embed.description = f'[{res["info"]["title"]}]({res["info"]["uri"]})'
            player.add(requester=ctx.author.id, track=res, index=index)
        elif isinstance(res, Track):
            track = await res.get_track(player)
            embed.title = '✅Трек добавлен'
            embed.description = f'[{res}]({res.show_url})'
            player.add(requester=ctx.author.id, track=track, index=index)
        elif isinstance(res, Playlist):
            if not res.tracks:
                embed.title = '❌Плейлист пустой'
                return await ctx.send(embed=embed)
            embed.title = '✅Плейлист добавлен'
            embed.description = f'{res.title} ({len(res.tracks)} {sform(len(res.tracks), "трек")})'
            procmsg = await ctx.send(embed=Embed(title=f'Плейлист "{res}" загружается...', color=color))
            await res.add(player, ctx.author.id, force)
            await procmsg.delete()
        elif isinstance(res, list):
            embed_value = ''
            for i, track in enumerate(res[:10]):
                embed_value += '{}: {}\n'.format(i + 1, track['info']['title'])
            choice_embed = Embed(title='Выберите трек', description=embed_value, color=Color.red())
            choice_embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
            choice_msg = await ctx.send(embed=choice_embed, delete_after=30)
            canc = False
            prefixes = await self.bot.get_prefix(ctx.message)

            def verify(m):
                nonlocal canc
                if m.content.isdigit():
                    return 0 <= int(m.content) <= min(len(res), 10) and m.channel == ctx.channel and m.author == ctx.author
                canc = m.channel == ctx.channel and m.author == ctx.author and any(m.content.startswith(prefix) and len(m.content) > len(prefix) for prefix in prefixes)
                return canc

            msg = await self.bot.wait_for('message', check=verify, timeout=30)
            if canc or int(msg.content) == 0:
                return await choice_msg.delete()
            track = res[int(msg.content) - 1]
            embed.title = '✅Трек добавлен'
            embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'
            player.add(requester=ctx.author.id, track=track, index=index)
            await choice_msg.delete()
        await ctx.send(embed=embed)
        if not player.is_playing:
            await player.play()

    @command(aliases=['p'], usage='play <ссылка/название>', help='Команда для проигрывания музыки')
    async def play(self, ctx, *, query=''):
        return await self._play(ctx, query, False)

    @command(aliases=['fp'], usage='force <ссылка/название>', help='Команда для добавления трека в начало очереди')
    async def force(self, ctx, *, query=''):
        return await self._play(ctx, query, True)

    @command(usage='gachi [кол-во]', help='Команда для проигрывания правильных версий музыки',
             aliases=['gachi'])
    async def gachibass(self, ctx, amt: int = 1):
        if amt > 100 or amt < 1:
            return await ctx.send('Нет')
        player = self.lavalink.player_manager.get(ctx.guild.id)
        with open('resources/gachi.txt', 'r') as f:
            tracks = load(f)
        tracks = sample(tracks, amt)
        player.add(requester=ctx.author.id, track=tracks.pop(0))
        await ctx.send(choice(gachi_things))
        if not player.is_playing:
            await player.play()
        for track in tracks:
            player.add(requester=ctx.author.id, track=track)

    @command(help='Команда для перемотки музыки', usage='seek <время в секундах>')
    async def seek(self, ctx, *, seconds: int):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        track_time = player.position + (seconds * 1000)
        await player.seek(track_time)
        await ctx.message.add_reaction('👌')

    @command(help='Команда для пропуска трека')
    async def skip(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        await player.skip()
        if player.queue or player.current:
            while not player.is_playing:
                await sleep(0.05)
            embed = Embed(color=get_embed_color(player.current.uri), title='⏩Дальше', description=f'[{player.current.title}]({player.current.uri})')
            await ctx.send(embed=embed)
        await ctx.message.add_reaction('👌')

    @command(help='Команда для остановки плеера и очистки очереди')
    async def stop(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        player.queue.clear()
        await player.stop()
        await self.connect_to(ctx.guild.id, None)
        await ctx.message.add_reaction('👌')

    @command(help='Команда для очистки очереди плеера')
    async def clear(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        player.queue.clear()
        await ctx.message.add_reaction('👌')

    @command(aliases=['n', 'np', 'playing', 'current'], help='Команда для отображения текущего трека')
    async def now(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.current:
            return await ctx.send('Ничего не играет')
        position = format_time(player.position)
        if player.current.stream:
            duration = '🔴 LIVE'
        else:
            duration = format_time(player.current.duration)
        song = f'[{player.current.title}]({player.current.uri})\n({position}/{duration})'
        embed = Embed(color=get_embed_color(player.current.uri), title='Сейчас играет', description=song)
        await ctx.send(embed=embed)

    @command(aliases=['nl', 'npl', 'cl'], help='Команда для отображения текста текущего трека')
    async def currentlyrics(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.current:
            return await ctx.send('Ничего не играет')
        title = player.current.title
        ftitle = re.sub(r'(?:\[([^]]+?)]|\(([^)]+?)\)|lyric video|lyrics video|lyrics)', '', title, flags=re.IGNORECASE).strip()
        params = {
            'q': ftitle
        }
        headers = {
            'Authorization': 'Bearer ' + genius_token
        }
        async with ClientSession() as client:
            req = await client.get('https://api.genius.com/search', params=params, headers=headers)
            res = await req.json()
        results = res['response']['hits']
        if len(results) == 0:
            return await ctx.send('Песня не найдена')
        result = results[0]
        if result['type'] != 'song' or result['result']['lyrics_state'] != 'complete':
            return await ctx.send('Текст песни не найден')
        url = result['result']['url']
        title = f'{result["result"]["primary_artist"]["name"]} - {result["result"]["title"]}'
        async with ClientSession() as client:
            lyrics = await client.get(url)
            lyrics = await lyrics.text()
        soup = BeautifulSoup(lyrics, 'html.parser')
        lyrics = soup.p.get_text()
        if len(lyrics) > 4000:
            return await ctx.send('Слишком длинный текст, скорее всего это не текст песни')
        if len(lyrics) > 2000:
            messages = wrap(lyrics, 2000)
            embed = Embed(color=Color.dark_purple())
            for segment, message in enumerate(messages):
                embed.title = f'Текст {title} ({segment + 1})'
                embed.description = message
                await ctx.send(embed=embed)
        else:
            embed = Embed(color=Color.dark_purple(), title=f'Текст {title}', description=lyrics)
            return await ctx.send(embed=embed)

    @command(aliases=['q', 'list'], help='Команда для отображения очереди воспроизведения')
    async def queue(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        queue = Queue(player, ctx)
        queues.append(queue)
        return await queue.send()

    @command(usage='save <название>', help='Команда для сохранения текущей очереди в плейлист')
    async def save(self, ctx, *, name):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue and not player.current:
            return await ctx.send('Очередь пустая')
        playlists = listdir(path.join('resources', 'playlists'))
        playlist_name = f'{ctx.author.id}_{name.lower()}'
        try:
            validate_filename(playlist_name)
        except ValidationError:
            return await ctx.send('Запрещенные символы в названии плейлиста')
        if playlist_name in playlists:
            return await ctx.send(f'Плейлист с таким названием уже существует\nДля удаления плейлиста используйте {ctx.prefix}delete <название>')
        if len(name) > 100:
            return await ctx.send('Слишком длинное название для плейлиста')
        local_queue = player.queue.copy() if player.queue else []
        if player.current:
            local_queue.insert(0, player.current)
        with open(path.join('resources', 'playlists', playlist_name), 'wb+') as queue_file:
            pdump(local_queue, queue_file)
        ln = len(local_queue)
        return await ctx.send(f'Плейлист {name} [{ln} {sform(ln, "трек")}] сохранен')

    @command(usage='load <название>', help='Команда для загрузки плейлиста в очередь')
    async def load(self, ctx, *, name):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        playlists = listdir(path.join('resources', 'playlists'))
        playlist_name = f'{ctx.author.id}_{name.lower()}'
        try:
            validate_filename(playlist_name)
        except ValidationError:
            return await ctx.send('Запрещенные символы в названии плейлиста')
        if playlist_name not in playlists:
            return await ctx.send(f'Нет плейлиста с таким названием\nДля просмотра своих плейлистов используйте {ctx.prefix}playlists')
        with open(path.join('resources', 'playlists', playlist_name), 'rb') as queue_file:
            queue = pload(queue_file)
        for track in queue:
            player.add(requester=ctx.author.id, track=track)
        ln = len(queue)
        await ctx.send(f'Плейлист {name} [{ln} {sform(ln, "трек")}] добавлен в очередь')
        if not player.is_playing:
            await player.play()

    @command(usage='delete <название>', help='Команда для удаления сохраненного плейлиста')
    async def delete(self, ctx, *, name):
        playlists = listdir(path.join('resources', 'playlists'))
        playlist_name = f'{ctx.author.id}_{name.lower()}'
        try:
            validate_filename(playlist_name)
        except ValidationError:
            return await ctx.send('Запрещенные символы в названии плейлиста')
        if playlist_name not in playlists:
            return await ctx.send(f'Нет плейлиста с таким названием\nДля просмотра своих плейлистов используйте {ctx.prefix}playlists')
        remove(path.join('resources', 'playlists', playlist_name))
        return await ctx.send(f'Плейлист {name} удален!')

    @command(help='Команда для просмотра списка сохраненных плейлистов')
    async def playlists(self, ctx):
        playlists = listdir(path.join('resources', 'playlists'))
        personal = []
        for playlist in playlists:
            user_id, name = playlist.split('_', 1)
            if int(user_id) == ctx.author.id:
                personal.append(name)
        if not personal:
            return await ctx.send('У вас нет сохраненных плейлистов!')
        embed = Embed(color=Color.dark_purple(), title='Сохраненные плейлисты',
                      description='\n'.join([f'{i + 1}. {name}' for i, name in enumerate(personal)]))
        return await ctx.send(embed=embed)

    @command(aliases=['resume'],
             help='Команда для приостановки или продолжения поспроизведения воспроизведения')
    async def pause(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        await player.set_pause(not player.paused)
        await ctx.message.add_reaction('⏸' if player.paused else '▶')

    @command(aliases=['vol'], help='Команда для изменения громкости плеера',
             usage='volume <громкость(1-1000)>')
    async def volume(self, ctx, volume: int = None):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if volume is None:
            return await ctx.send(f'🔈 | {player.volume}%')
        await player.set_volume(volume)
        await ctx.message.add_reaction('👌')
        vols = load(open('resources/saved.json', 'r'))
        vols[str(ctx.guild.id)]['volume'] = player.volume
        dump(vols, open('resources/saved.json', 'w'))

    @command(help='Команда для включения/выключения перемешивания очереди')
    async def shuffle(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        player.shuffle = not player.shuffle
        shffl = load(open('resources/saved.json', 'r'))
        shffl[str(ctx.guild.id)]['shuffle'] = player.shuffle
        dump(shffl, open('resources/saved.json', 'w'))
        await ctx.send('🔀 | Перемешивание ' + ('включено' if player.shuffle else 'выключено'))

    @command(help='Команда для перемешивания текущей очереди', aliases=['qs'])
    async def qshuffle(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        shuffle(player.queue)
        await ctx.message.add_reaction('👌')

    @command(aliases=['loop'], help='Команда для включения/выключения зацикливания очереди')
    async def repeat(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        player.repeat = not player.repeat
        await ctx.send('🔁 | Циклическое воспроизведение ' + ('включено' if player.repeat else 'выключено'))

    @command(help='Команда для удаления трека из очереди', usage='remove <индекс>')
    async def remove(self, ctx, index: int):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        if index > len(player.queue) or index < 1:
            return await ctx.send(f'Индекс дожен быть **между** 1 и {len(player.queue)}')
        removed = player.queue.pop(index - 1)
        embed = Embed(color=Color.dark_purple(), title='❌Трек удален', description=f'[{removed.title}]({removed.uri})')
        await ctx.send(embed=embed)
        await update_queues(player)

    @command(aliases=['dc', 'leave'], help='Команда для отключения бота от голосового канала')
    async def disconnect(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_connected:
            return await ctx.send('Не подключен к голосовому каналу')
        player.queue.clear()
        await player.stop()
        await self.connect_to(ctx.guild.id, None)
        await ctx.message.add_reaction('👌')

    @command(aliases=['connect', 'c'], help='Команда для подключения бота к голосовому каналу')
    async def join(self, ctx):
        player = self.lavalink.player_manager.get(ctx.guild.id)
        if player.channel_id:
            if ctx.author.voice.channel.id == int(player.channel_id):
                return await ctx.send('Уже подключен к голосовому каналу')
        await self.connect_to(ctx.guild.id, ctx.author.voice.channel.id)
        await ctx.message.add_reaction('👌')

    async def ensure_voice(self, ctx):
        player = self.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        should_connect = ctx.command.name in ('play', 'force', 'join', 'join', 'gachibass', 'move', 'load')
        ignored = ctx.command.name in ['volume', 'shuffle', 'playlists', 'delete', 'queue', 'now']
        if ignored:
            return
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise MusicCommandError('Сначала подключитесь к голосовому каналу')
        if not player.is_connected:
            if not should_connect:
                raise MusicCommandError('Я не подключен к каналу')
            me = await ctx.guild.fetch_member(ctx.bot.user.id)
            permissions = ctx.author.voice.channel.permissions_for(me)
            if not permissions.connect or not permissions.speak:
                raise MusicCommandError('Мне нужны разрешения подключаться к каналу и говорить!')
            player.store('channel', ctx.channel.id)
            await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
        else:
            if int(player.channel_id) == ctx.author.voice.channel.id and should_connect:
                return
            if should_connect:
                return await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise MusicCommandError('Мы в разных голосовых каналах')


def music_setup(bot):
    bot.add_cog(Music(bot))
