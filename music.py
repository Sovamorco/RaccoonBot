from asyncio import sleep
from random import shuffle
from textwrap import wrap

from bs4 import BeautifulSoup
from discord import VoiceClient
from discord.ext.commands import Cog, command, Bot
from lavalink import Client, format_time, add_event_hook, TrackEndEvent, Node

from music_funcs import *


class LavalinkVoiceClient(VoiceClient):
    # noinspection PyMissingConstructor
    def __init__(self, client, channel):
        self.client = client
        self.channel = channel
        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False,
                      self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that
        # would set channel_id to None doesn't get dispatched after the
        # disconnect
        player.channel_id = None
        self.cleanup()


class Music(Cog):
    def __init__(self, bot: Bot):
        # initialized in initialize()
        self.spotify: Spotify = None
        self.bot = bot

        if not hasattr(bot, 'lavalink'):
            lc = Client(bot.user.id, player=Player)
            addr = self.bot.config['lavalink']['address']
            pw = self.bot.config['lavalink']['password']
            self.bot.lavalink_node = Node(addr, 2333, pw, 'de', 'default-node', 600, 'default-node', -1)
            lc.node_manager.nodes.append(self.bot.lavalink_node)
            self.bot.lavalink = lc

        add_event_hook(update_queues, event=TrackEndEvent)

    async def initialize(self):
        print('Initializing spotify')
        self.spotify = await init_spotify(self.bot.config, self.bot.loop)
        print('Trying to connect to lavalink')
        if not self.bot.lavalink_node.available:
            # noinspection PyProtectedMember
            await self.bot.lavalink_node._ws.connect()
        print('Initializing lavalink')
        saved_settings = await self.bot.sql_client.sql_req(
            'SELECT id, volume, shuffle FROM server_data', fetch_all=True
        )
        for saved in saved_settings:
            player = self.bot.lavalink.player_manager.create(saved['id'])
            await player.set_volume(saved['volume'])
            player.shuffle = saved['shuffle']
        print('Initialized lavalink')

    async def stop_playing(self, guild_id):
        player = self.bot.lavalink.player_manager.get(guild_id)
        player.queue.clear()
        await player.stop()
        guild = self.bot.get_guild(guild_id)
        await guild.voice_client.disconnect(force=True)

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not after.channel and before.channel:
            if any(self.bot.user in channel.members and all(channel_member.bot for channel_member in channel.members)
                   for channel in member.guild.voice_channels):
                await self.stop_playing(member.guild.id)

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user != self.bot.user:
            for queue in queues:
                if queue.message.id == reaction.message.id:
                    return await queue.react(reaction)

    def cog_unload(self):
        # noinspection PyProtectedMember
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        guild_check = ctx.guild is not None
        if guild_check:
            await self.ensure_voice(ctx)
        return guild_check

    async def _play(self, ctx, query, force):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        index = 0 if force else None
        if not query:
            if player.paused:
                await player.set_pause(False)
                return await ctx.send('⏯ | Воспроизведение возобновлено')
            if not player.is_playing and (player.queue or player.current):
                return await player.play()
            else:
                return await ctx.send(f'Использование: {ctx.prefix}[p|play] <ссылка/название>')
        res = await get_track(self.spotify, player, query, self.bot.config)
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
            track = await res.get_track(self.spotify, player, self.bot.config)
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
            await res.add(self.spotify, player, ctx.author.id, procmsg, self.bot.config, force)
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
                    return 0 <= int(m.content) <= min(len(res),
                                                      10) and m.channel == ctx.channel and m.author == ctx.author
                canc = m.channel == ctx.channel and m.author == ctx.author and any(
                    m.content.startswith(prefix) and len(m.content) > len(prefix) for prefix in prefixes)
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

    @command(help='Команда для перемотки музыки', usage='seek <время в секундах>')
    async def seek(self, ctx, *, seconds: int):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        track_time = player.position + (seconds * 1000)
        await player.seek(track_time)
        await ctx.message.add_reaction('👌')

    @command(help='Команда для пропуска трека')
    async def skip(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        await player.skip()
        if player.queue or player.current:
            while not player.is_playing:
                await sleep(0.05)
            embed = Embed(color=get_embed_color(player.current.uri), title='⏩Дальше',
                          description=f'[{player.current.title}]({player.current.uri})')
            await ctx.send(embed=embed)
        await ctx.message.add_reaction('👌')

    @command(aliases=['dc', 'leave', 'disconnect'], help='Команда для остановки плеера и очистки очереди')
    async def stop(self, ctx):
        await self.stop_playing(ctx.guild.id)
        await ctx.message.add_reaction('👌')

    @command(help='Команда для очистки очереди плеера')
    async def clear(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        player.queue.clear()
        await ctx.message.add_reaction('👌')

    @command(aliases=['n', 'np', 'playing', 'current'], help='Команда для отображения текущего трека')
    async def now(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
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
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.current:
            return await ctx.send('Ничего не играет')
        title = player.current.title
        ftitle = re.sub(r'(?:\[([^]]+?)]|\(([^)]+?)\)|lyric video|lyrics video|lyrics)', '', title,
                        flags=re.IGNORECASE).strip()
        params = {
            'q': ftitle
        }
        headers = {
            'Authorization': 'Bearer ' + self.bot.config['genius_token']
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
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        queue = Queue(player, ctx)
        queues.append(queue)
        return await queue.send()

    @command(aliases=['resume'],
             help='Команда для приостановки или продолжения поспроизведения воспроизведения')
    async def pause(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        await player.set_pause(not player.paused)
        await ctx.message.add_reaction('⏸' if player.paused else '▶')

    @command(aliases=['vol'], help='Команда для изменения громкости плеера',
             usage='volume <громкость(1-1000)>')
    async def volume(self, ctx, volume: int = None):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if volume is None:
            return await ctx.send(f'🔈 | {player.volume}%')
        await player.set_volume(volume)
        await ctx.message.add_reaction('👌')
        await self.bot.sql_client.sql_req(
            'INSERT INTO server_data (id, volume) VALUES (%s, %s) ON DUPLICATE KEY UPDATE volume=%s',
            ctx.guild.id, player.volume, player.volume,
        )

    @command(help='Команда для включения/выключения перемешивания очереди')
    async def shuffle(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        player.shuffle = not player.shuffle
        await ctx.send('🔀 | Перемешивание ' + ('включено' if player.shuffle else 'выключено'))
        await self.bot.sql_client.sql_req(
            'INSERT INTO server_data (id, shuffle) VALUES (%s, %s) ON DUPLICATE KEY UPDATE shuffle=%s',
            ctx.guild.id, player.shuffle, player.shuffle,
        )

    @command(help='Команда для перемешивания текущей очереди', aliases=['qs'])
    async def qshuffle(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        shuffle(player.queue)
        await ctx.message.add_reaction('👌')

    @command(aliases=['loop'], help='Команда для включения/выключения зацикливания очереди')
    async def repeat(self, ctx):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        player.repeat = not player.repeat
        await ctx.send('🔁 | Циклическое воспроизведение ' + ('включено' if player.repeat else 'выключено'))

    @command(help='Команда для удаления трека из очереди', usage='remove <индекс>')
    async def remove(self, ctx, index: int):
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        if index > len(player.queue) or index < 1:
            return await ctx.send(f'Индекс дожен быть **между** 1 и {len(player.queue)}')
        removed = player.queue.pop(index - 1)
        embed = Embed(color=Color.dark_purple(), title='❌Трек удален', description=f'[{removed.title}]({removed.uri})')
        await ctx.send(embed=embed)
        await update_queues(player)

    @command(aliases=['connect', 'c'], help='Команда для подключения бота к голосовому каналу')
    async def join(self, ctx):
        await ctx.message.add_reaction('👌')

    async def ensure_voice(self, ctx):
        if not self.bot.lavalink_node.available:
            # noinspection PyProtectedMember
            await self.bot.lavalink_node._ws.connect()
        player = self.bot.lavalink.player_manager.create(ctx.guild.id)
        should_connect = ctx.command.name in ('play', 'force', 'join', 'gachibass', 'move')
        ignored = ctx.command.name in ('volume', 'shuffle', 'delete', 'queue', 'now')
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
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if int(player.channel_id) == ctx.author.voice.channel.id and should_connect:
                return
            if should_connect:
                return await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise MusicCommandError('Мы в разных голосовых каналах')


async def music_setup(bot):
    cog = Music(bot)
    await cog.initialize()
    await bot.add_cog(cog)
