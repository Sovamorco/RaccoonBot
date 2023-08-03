from collections import ChainMap
from typing import Optional

import grpc
from discord.ext.commands import Cog, command, Bot
from discord.ext.commands import Context
# noinspection PyPackageRequirements
from google.protobuf.duration_pb2 import Duration
from grpc.aio import UnaryUnaryClientInterceptor, UnaryStreamClientInterceptor, StreamStreamClientInterceptor, \
    StreamUnaryClientInterceptor
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

from music_funcs import *
from orca_pb2 import PlayRequest, PlayReply, GuildOnlyRequest, SeekRequest, \
    GetTracksRequest, GetTracksReply, JoinRequest, RemoveRequest, SavePlaylistRequest, ListPlaylistsRequest, \
    ListPlaylistsReply, LoadPlaylistRequest
from orca_pb2_grpc import OrcaStub
from utils import sform


class SessionInterceptor(
    StreamStreamClientInterceptor,
    StreamUnaryClientInterceptor,
    UnaryStreamClientInterceptor,
    UnaryUnaryClientInterceptor,
):
    def __init__(self, token):
        self.token = token

    async def intercept(self, continuation, client_call_details, request):
        client_call_details.metadata.add("token", self.token)
        return await continuation(client_call_details, request)

    async def intercept_stream_stream(self, continuation, client_call_details, request):
        return await self.intercept(continuation, client_call_details, request)

    async def intercept_stream_unary(self, continuation, client_call_details, request):
        return await self.intercept(continuation, client_call_details, request)

    async def intercept_unary_stream(self, continuation, client_call_details, request):
        return await self.intercept(continuation, client_call_details, request)

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        return await self.intercept(continuation, client_call_details, request)


class Music(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        if not hasattr(bot, 'orca'):
            print('Creating orca connection')
            sess_interceptor = SessionInterceptor(self.bot.config['discord']['token'])
            channel = grpc.aio.insecure_channel(
                bot.config['orca']['address'],
                interceptors=[sess_interceptor],
            )
            bot.orca = OrcaStub(channel)

    async def stop_playing(self, guild_id):
        return await self.bot.orca.Stop(GuildOnlyRequest(
            guildID=guild_id
        ))

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

    async def _do_search(self, ctx: Context, query: str) -> Optional[str]:
        tracks = []

        def match_filter(info_dict, *_, **__):
            nonlocal tracks

            if not isinstance(info_dict, ChainMap):
                return None

            if info_dict.get('duration') is None or 'youtube.com/watch?v' not in info_dict.get('url', ''):
                return 'not a video'

            tracks.append(info_dict)

            if len(tracks) >= 10:
                raise DownloadCancelled('matched 10')

            return None

        ytdl = YoutubeDL(params={
            'extract_flat': True,
            'match_filter': match_filter,
            'lazy_playlist': True,
            'quiet': True,
        })

        try:
            ytdl.extract_info(f'ytsearch1000:{query}', download=False)
        except DownloadCancelled:
            pass

        embed_value = ''

        for i, track in enumerate(tracks):
            embed_value += '{}: **{}** ({})\n'.format(
                i + 1,
                track['title'],
                format_time(track['duration']),
            )

        choice_embed = Embed(title='Выберите трек', description=embed_value, color=Color.red())
        choice_embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
        choice_msg = await ctx.send(embed=choice_embed, delete_after=30)
        canc = False

        prefixes = await self.bot.get_prefix(ctx.message)

        def verify(m):
            nonlocal canc
            if m.content.isdigit():
                return 0 <= int(m.content) <= min(len(tracks),
                                                  10) and m.channel == ctx.channel and m.author == ctx.author
            canc = m.channel == ctx.channel and m.author == ctx.author and any(
                m.content.startswith(prefix) and len(m.content) > len(prefix) for prefix in prefixes)
            return canc

        msg = await self.bot.wait_for('message', check=verify, timeout=30)
        if canc or int(msg.content) == 0:
            await choice_msg.delete()
            return None

        track = tracks[int(msg.content) - 1]
        await choice_msg.delete()

        return track['url']

    async def _play(self, ctx: Context, query, pos=None):
        if ctx.author.voice is None:
            return await ctx.send('Не в голосовом канале')

        if query == '':
            return await ctx.send('Запрос трека не может быть пустым')

        if not url_rx.match(query):
            query = await self._do_search(ctx, query)
            if query is None:
                return

        req = PlayRequest(
            guildID=str(ctx.guild.id),
            channelID=str(ctx.author.voice.channel.id),
            url=query,
        )
        if pos is not None:
            req.position = pos
        res: PlayReply = await self.bot.orca.Play(req)

        color = get_embed_color(query)
        embed = Embed(color=color)

        if len(res.tracks) == 1:
            embed.title = '✅Трек добавлен'
            embed.description = f'[{res.tracks[0].title}]({res.tracks[0].displayURL})'
        else:
            embed.title = '✅Треки добавлены'
            embed.description = '\n'.join([f'[{track.title}]({track.displayURL})' for track in res.tracks[:10]])
            if len(res.tracks) > 10:
                embed.description += f'\n... и еще {len(res.tracks) - 10}'

        return await ctx.send(embed=embed)

    @command(aliases=['p'], usage='play <ссылка/название>', help='Команда для проигрывания музыки')
    async def play(self, ctx: Context, *, query=''):
        return await self._play(ctx, query, -1)

    @command(aliases=['fp'], usage='force <ссылка/название>', help='Команда для добавления трека в начало очереди')
    async def force(self, ctx, *, query=''):
        return await self._play(ctx, query, 1)

    @command(aliases=['ip'], usage='insert <место в очереди> <ссылка/название>',
             help='Команда для добавления трека в определенное место в очереди\n'
                  'insert 0 - прервать текущий трек и поставить вместо него\n'
                  'insert 1 - аналогично force\n'
                  'insert 2 - поставить после следующего трека')
    async def insert(self, ctx, pos: int, *, query=''):
        return await self._play(ctx, query, pos)

    @command(help='Команда для перемотки музыки', usage='seek <время в секундах>')
    async def seek(self, ctx: Context, *, seconds: float):
        pos = Duration()
        pos.FromNanoseconds(int(seconds * 10 ** 9))
        await self.bot.orca.Seek(SeekRequest(
            guildID=str(ctx.guild.id),
            position=pos,
        ))
        await ctx.message.add_reaction('👌')

    @command(help='Команда для пропуска трека')
    async def skip(self, ctx: Context):
        self.bot.orca.Skip(GuildOnlyRequest(
            guildID=str(ctx.guild.id),
        ))
        await ctx.message.add_reaction('👌')

    @command(help='Команда для постановки трека на паузу')
    async def pause(self, ctx: Context):
        self.bot.orca.Pause(GuildOnlyRequest(
            guildID=str(ctx.guild.id),
        ))
        await ctx.message.add_reaction('👌')

    @command(help='Команда для продолжения трека')
    async def resume(self, ctx: Context):
        self.bot.orca.Resume(GuildOnlyRequest(
            guildID=str(ctx.guild.id),
        ))
        await ctx.message.add_reaction('👌')

    @command(help='Команда для включения/выключения повторения очереди')
    async def loop(self, ctx: Context):
        self.bot.orca.Loop(GuildOnlyRequest(
            guildID=str(ctx.guild.id),
        ))
        await ctx.message.add_reaction('👌')

    @command(aliases=['qs'], help='Команда для перемешивания текущей очереди')
    async def qshuffle(self, ctx: Context):
        self.bot.orca.ShuffleQueue(GuildOnlyRequest(
            guildID=str(ctx.guild.id),
        ))
        await ctx.message.add_reaction('👌')

    @command(help='Команда для остановки плеера и очистки очереди')
    async def stop(self, ctx: Context):
        await self.stop_playing(str(ctx.guild.id))
        await ctx.message.add_reaction('👌')

    @command(aliases=['dc', 'disconnect'], help='Команда для отключения от голосового канала')
    async def leave(self, ctx: Context):
        await self.bot.orca.Leave(GuildOnlyRequest(
            guildID=str(ctx.guild.id)
        ))
        await ctx.message.add_reaction('👌')

    @command(aliases=['c', 'connect'], help='Команда для подключения к голосовому каналу')
    async def join(self, ctx: Context):
        if ctx.author.voice is None:
            return await ctx.send('Не в голосовом канале')

        await self.bot.orca.Join(JoinRequest(
            guildID=str(ctx.guild.id),
            channelID=str(ctx.author.voice.channel.id),
        ))
        await ctx.message.add_reaction('👌')

    @command(aliases=['n', 'np', 'playing', 'current'], help='Команда для отображения текущего трека')
    async def now(self, ctx):
        res: GetTracksReply = await self.bot.orca.GetTracks(GetTracksRequest(
            guildID=str(ctx.guild.id),
            start=0,
            end=1,
        ))
        if len(res.tracks) < 1:
            return await ctx.send('Ничего не играет')
        current = res.tracks[0]
        if current.live:
            poss = '🔴 LIVE'
        else:
            poss = f'{format_time(current.position.ToSeconds())}/{format_time(current.duration.ToSeconds())}'
        song = f'[{current.title}]({current.displayURL})\n({poss})'
        embed = Embed(color=get_embed_color(current.displayURL), title='Сейчас играет', description=song)
        await ctx.send(embed=embed)

    @command(aliases=['q', 'list'], usage='queue [страница]',
             help='Команда для отображения очереди воспроизведения')
    async def queue(self, ctx, page: int = 1):
        if page < 1:
            return await ctx.send('Страница не может быть отрицательной')

        currentres: GetTracksReply = await self.bot.orca.GetTracks(GetTracksRequest(
            guildID=str(ctx.guild.id),
            start=0,
            end=1,
        ))
        if len(currentres.tracks) < 1:
            return await ctx.send('Ничего не играет')
        current = currentres.tracks[0]
        res: GetTracksReply = await self.bot.orca.GetTracks(GetTracksRequest(
            guildID=str(ctx.guild.id),
            start=1 + 10 * (page - 1),
            end=1 + 10 * page,
        ))
        q = Queue(current, res.tracks, res.looping, page, res.totalTracks, res.remaining.ToSeconds())
        return await ctx.send(embed=q.embed)

    @command(aliases=['r', 'delete'], usage='remove <номер трека>',
             help='Команда для удаления трека из очереди')
    async def remove(self, ctx, pos: int):
        if pos < 0:
            return await ctx.send('Номер не может быть отрицательным')

        await self.bot.orca.Remove(RemoveRequest(
            guildID=str(ctx.guild.id),
            position=pos,
        ))
        await ctx.message.add_reaction('👌')

    @command(usage='save <название>',
             help='Команда для сохранения очереди в плейлист')
    async def save(self, ctx: Context, *, name: str):
        await self.bot.orca.SavePlaylist(SavePlaylistRequest(
            guildID=str(ctx.guild.id),
            userID=str(ctx.author.id),
            name=name,
        ))
        await ctx.message.add_reaction('👌')

    @command(aliases=['pls'], help='Команда для просмотра сохраненных плейлистов')
    async def playlists(self, ctx: Context):
        res: ListPlaylistsReply = await self.bot.orca.ListPlaylists(ListPlaylistsRequest(
            guildID=str(ctx.guild.id),
            userID=str(ctx.author.id),
        ))

        embed_lines = []
        for i, playlist in enumerate(res.playlists):
            embed_lines.append(f'{i + 1}. **{playlist.name}** - '
                               f'{playlist.totalTracks} {sform(playlist.totalTracks, "трек")} '
                               f'({format_time(playlist.totalDuration.ToSeconds())})')

        embed = Embed(color=Color.dark_purple(), title='Сохраненные плейлисты', description='\n'.join(embed_lines))

        return await ctx.send(embed=embed)

    @command(help='Команда для добавления сохраненного плейлиста в очередь')
    async def load(self, ctx: Context):
        if ctx.author.voice is None:
            return await ctx.send('Не в голосовом канале')

        res: ListPlaylistsReply = await self.bot.orca.ListPlaylists(ListPlaylistsRequest(
            guildID=str(ctx.guild.id),
            userID=str(ctx.author.id),
        ))

        embed_lines = []
        for i, playlist in enumerate(res.playlists):
            embed_lines.append(f'{i + 1}. **{playlist.name}** - '
                               f'{playlist.totalTracks} {sform(playlist.totalTracks, "трек")} '
                               f'({format_time(playlist.totalDuration.ToSeconds())})')

        embed = Embed(color=Color.dark_purple(), title='Выберите плейлист', description='\n'.join(embed_lines))
        embed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')

        choicemsg = await ctx.send(embed=embed)

        canc = False

        prefixes = await self.bot.get_prefix(ctx.message)

        def verify(m):
            nonlocal canc

            if m.content.isdigit():
                return 0 <= int(m.content) <= len(res.playlists) and m.channel == ctx.channel and m.author == ctx.author

            canc = m.channel == ctx.channel and m.author == ctx.author and any(
                m.content.startswith(prefix) and len(m.content) > len(prefix) for prefix in prefixes)
            return canc

        msg = await self.bot.wait_for('message', check=verify, timeout=30)
        if canc or int(msg.content) == 0:
            await choicemsg.delete()
            return None

        chosen = res.playlists[int(msg.content) - 1].id

        res: PlayReply = await self.bot.orca.LoadPlaylist(LoadPlaylistRequest(
            guildID=str(ctx.guild.id),
            playlistID=chosen,
            channelID=str(ctx.author.voice.channel.id),
        ))

        embed = Embed(color=Color.dark_purple())

        if len(res.tracks) == 1:
            embed.title = '✅Трек добавлен'
            embed.description = f'[{res.tracks[0].title}]({res.tracks[0].displayURL})'
        else:
            embed.title = '✅Треки добавлены'
            embed.description = '\n'.join([f'[{track.title}]({track.displayURL})' for track in res.tracks[:10]])
            if len(res.tracks) > 10:
                embed.description += f'\n... и еще {len(res.tracks) - 10}'

        return await ctx.send(embed=embed)


async def music_setup(bot):
    cog = Music(bot)
    await bot.add_cog(cog)
