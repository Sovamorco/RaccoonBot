import asyncio
import sys
from code import interact
from collections import ChainMap
from typing import Optional

import grpc
from common import AsyncSQLClient
from discord import Message
from discord.ext.commands import Bot, Cog, Context, hybrid_command
from google.protobuf.duration_pb2 import Duration
from google.protobuf.empty_pb2 import Empty
from grpc.aio import UnaryStreamClientInterceptor, UnaryUnaryClientInterceptor
from regex import E
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

from music_funcs import *
from orca_pb2 import (
    GetTracksReply,
    GetTracksRequest,
    GuildOnlyRequest,
    JoinRequest,
    ListPlaylistsReply,
    ListPlaylistsRequest,
    LoadPlaylistRequest,
    PlayReply,
    PlayRequest,
    QueueChangeNotification,
    RemoveRequest,
    SavePlaylistRequest,
    SeekRequest,
)
from orca_pb2_grpc import OrcaStub
from utils import ok, sform


async def token_intercept(token, continuation, client_call_details, request):
    client_call_details.metadata.add("token", token)
    return await continuation(client_call_details, request)


class SessionUUInterceptor(UnaryUnaryClientInterceptor):
    def __init__(self, token):
        self.token = token

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        return await token_intercept(
            self.token, continuation, client_call_details, request
        )


class SessionUSInterceptor(UnaryStreamClientInterceptor):
    def __init__(self, token):
        self.token = token

    async def intercept_unary_stream(self, continuation, client_call_details, request):
        return await token_intercept(
            self.token, continuation, client_call_details, request
        )


class Music(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        if not hasattr(bot, "orca"):
            print("Creating orca connection")
            # see https://github.com/grpc/grpc/issues/31442
            sess_interceptors = [
                SessionUUInterceptor(self.bot.config["discord"]["token"]),
                SessionUSInterceptor(self.bot.config["discord"]["token"]),
            ]

            channel = grpc.aio.insecure_channel(
                bot.config["orca"]["address"],
                interceptors=sess_interceptors,
            )

            bot.orca = OrcaStub(channel)

            bot.loop.create_task(self._watch_queues())

        self.orca: OrcaStub = self.bot.orca
        self.sql_client: AsyncSQLClient = self.bot.sql_client
        self.queues: map[Queue] = {}

        self.bot.loop.create_task(self._init_queues())

    async def _init_queues(self):
        stored = await self.sql_client.sql_req(
            "SELECT guild_id, channel_id, message_id, page FROM queues", fetch_all=True
        )

        for row in stored:
            guild_id = row["guild_id"]
            channel_id = row["channel_id"]
            message_id = row["message_id"]
            page = row["page"]

            q = Queue(self.orca, guild_id, page)

            try:
                msg = self.bot.get_channel(channel_id).get_partial_message(message_id)
            except Exception as e:
                print(
                    f"Error while fetching message {message_id} in channel {channel_id}: {e}",
                    file=sys.stderr,
                )

                continue

            q.message = msg

            self.queues[guild_id] = q

            self.bot.loop.create_task(self.on_queue_update(guild_id))

    async def _watch_queues(self):
        await asyncio.gather(
            self._queue_notifications(), self._periodic_queue_refresh()
        )

    async def _queue_notifications(self):
        while True:
            try:
                async for msg in self.orca.Subscribe(Empty()):
                    msg: QueueChangeNotification

                    self.bot.loop.create_task(self.on_queue_update(int(msg.guild)))
            except Exception as e:
                print(
                    f"Exception occurred while listening to queue change notifications: {e}",
                    file=sys.stderr,
                )

            # means error happened or connection was lost, try to restore after delay
            await asyncio.sleep(5)

    async def _periodic_queue_refresh(self):
        while True:
            for guild_id in self.queues:
                self.bot.loop.create_task(self.on_queue_update(guild_id))

            await asyncio.sleep(30)

    async def stop_playing(self, guild_id):
        return await self.orca.Stop(GuildOnlyRequest(guildID=guild_id))

    async def on_queue_update(self, guild_id):
        if guild_id not in self.queues:
            return

        q: Queue = self.queues[guild_id]
        keep = await q.update()

        if not keep:
            self.queues.pop(guild_id, None)

            await self.sql_client.sql_req(
                "DELETE FROM queues WHERE guild_id=%s",
                guild_id,
            )

    async def _do_search(
        self, ctx: Context, query: str
    ) -> Optional[tuple[Message, str]]:
        tracks = []

        def match_filter(info_dict, *_, **__):
            nonlocal tracks

            if not isinstance(info_dict, ChainMap):
                return None

            if info_dict.get(
                "duration"
            ) is None or "youtube.com/watch?v" not in info_dict.get("url", ""):
                return "not a video"

            tracks.append(info_dict)

            if len(tracks) >= 10:
                raise DownloadCancelled("matched 10")

            return None

        ytdl = YoutubeDL(
            params={
                "extract_flat": True,
                "match_filter": match_filter,
                "lazy_playlist": True,
                "quiet": True,
            }
        )

        try:
            ytdl.extract_info(f"ytsearch1000:{query}", download=False)
        except DownloadCancelled:
            pass

        embed_value = ""

        for i, track in enumerate(tracks):
            embed_value += "{}: **{}** ({})\n".format(
                i + 1,
                track["title"],
                format_time(track["duration"]),
            )

        choice_embed = Embed(
            title="Выберите трек", description=embed_value, color=Color.red()
        )
        choice_embed.set_footer(
            text="Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены"
        )
        choice_msg = await ctx.send(embed=choice_embed)
        canc = False

        prefixes = await self.bot.get_prefix(ctx.message)

        def verify(m):
            nonlocal canc

            if m.content.isdigit():
                return (
                    0 <= int(m.content) <= min(len(tracks), 10)
                    and m.channel == ctx.channel
                    and m.author == ctx.author
                )
            canc = (
                m.channel == ctx.channel
                and m.author == ctx.author
                and any(
                    m.content.startswith(prefix) and len(m.content) > len(prefix)
                    for prefix in prefixes
                )
            )

            return canc

        try:
            msg = await self.bot.wait_for("message", check=verify, timeout=5)
        except asyncio.TimeoutError:
            canc = True

        if canc or int(msg.content) == 0:
            await choice_msg.delete()

            return

        track = tracks[int(msg.content) - 1]

        loading_embed = Embed(
            title="⏳Загрузка трека...",
            description=f"[{track['title']}]({track['url']})",
            color=Color.red(),
        )

        await choice_msg.edit(embed=loading_embed)

        return choice_msg, track["url"]

    async def _play(self, ctx: Context, query, pos=None):
        if ctx.author.voice is None:
            return await ctx.send("Не в голосовом канале")

        if query == "":
            return await ctx.send("Запрос трека не может быть пустым")

        to_edit = None

        if not url_rx.match(query):
            to_edit, query = await self._do_search(ctx, query)

            if query is None:
                await to_edit.delete()

                return

        req = PlayRequest(
            guildID=str(ctx.guild.id),
            channelID=str(ctx.author.voice.channel.id),
            url=query,
        )
        if pos is not None:
            req.position = pos
        res: PlayReply = await self.orca.Play(req)

        color = get_embed_color(query)
        embed = Embed(color=color)

        if res.total == 1:
            embed.title = "✅Трек добавлен"
            embed.description = f"[{res.tracks[0].title}]({res.tracks[0].displayURL})"
        else:
            embed.title = "✅Треки добавлены"
            embed.description = "\n".join(
                [f"[{track.title}]({track.displayURL})" for track in res.tracks[:10]]
            )
            if res.total > 10:
                embed.description += f"\n... и еще {res.total - 10}"

        if to_edit is not None:
            return await to_edit.edit(embed=embed)

        return await ctx.send(embed=embed)

    @hybrid_command(
        aliases=["p"],
        usage="play <ссылка/название>",
        help="Команда для проигрывания музыки",
    )
    async def play(self, ctx: Context, *, query=""):
        return await self._play(ctx, query, -1)

    @hybrid_command(
        aliases=["fp"],
        usage="force <ссылка/название>",
        help="Команда для добавления трека в начало очереди",
    )
    async def force(self, ctx, *, query=""):
        return await self._play(ctx, query, 1)

    @hybrid_command(
        aliases=["ip"],
        usage="insert <место в очереди> <ссылка/название>",
        help="Команда для добавления трека в определенное место в очереди\n"
        "insert 0 - прервать текущий трек и поставить вместо него\n"
        "insert 1 - аналогично force\n"
        "insert 2 - поставить после следующего трека",
    )
    async def insert(self, ctx, pos: int, *, query=""):
        return await self._play(ctx, query, pos)

    @hybrid_command(
        help="Команда для перемотки музыки", usage="seek <время в секундах>"
    )
    async def seek(self, ctx: Context, *, seconds: float):
        pos = Duration()
        pos.FromNanoseconds(int(seconds * 10**9))
        await self.orca.Seek(
            SeekRequest(
                guildID=str(ctx.guild.id),
                position=pos,
            )
        )

        return await ok(ctx, "Трек перемотан")

    @hybrid_command(help="Команда для пропуска трека")
    async def skip(self, ctx: Context):
        await self.orca.Skip(
            GuildOnlyRequest(
                guildID=str(ctx.guild.id),
            )
        )

        return await ok(ctx, "Трек пропущен")

    @hybrid_command(help="Команда для постановки трека на паузу")
    async def pause(self, ctx: Context):
        await self.orca.Pause(
            GuildOnlyRequest(
                guildID=str(ctx.guild.id),
            )
        )

        return await ok(ctx, "Трек поставлен на паузу")

    @hybrid_command(help="Команда для продолжения трека")
    async def resume(self, ctx: Context):
        await self.orca.Resume(
            GuildOnlyRequest(
                guildID=str(ctx.guild.id),
            )
        )

        return await ok(ctx, "Трек продолжен")

    @hybrid_command(help="Команда для включения/выключения повторения очереди")
    async def loop(self, ctx: Context):
        await self.orca.Loop(
            GuildOnlyRequest(
                guildID=str(ctx.guild.id),
            )
        )

        queue_state: GetTracksReply = await self.orca.GetTracks(
            GetTracksRequest(
                guildID=str(ctx.guild.id),
                start=0,
                end=0,
            )
        )

        return await ok(
            ctx, "Повторение " + ("включено" if queue_state.looping else "выключено")
        )

    @hybrid_command(aliases=["qs"], help="Команда для перемешивания текущей очереди")
    async def qshuffle(self, ctx: Context):
        await self.orca.ShuffleQueue(
            GuildOnlyRequest(
                guildID=str(ctx.guild.id),
            )
        )

        return await ok(ctx, "Очередь перемешана")

    @hybrid_command(help="Команда для остановки плеера и очистки очереди")
    async def stop(self, ctx: Context):
        cemb = Embed(
            title="Вы уверены?",
            description="Это действие остановит плеер и очистит очередь\nОтправьте `да` для подтверждения или `нет` для отмены",
            color=Color.red(),
        )

        cemb.set_footer(text="Автоматическая отмена через 30 секунд")

        choicemsg = await ctx.send(
            embed=cemb,
        )

        canc = False
        prefixes = await self.bot.get_prefix(ctx.message)

        def verify(m):
            nonlocal canc

            canc = (
                m.channel == ctx.message.channel
                and m.author == ctx.message.author
                and any(
                    m.content.startswith(prefix) and len(m.content) > len(prefix)
                    for prefix in prefixes
                )
            )

            return canc or m.content.lower() in ["да", "yes", "нет", "no"]

        try:
            msg = await self.bot.wait_for("message", check=verify, timeout=30)
        except asyncio.TimeoutError:
            return await choicemsg.delete()

        if canc or msg.content.lower() in ["нет", "no"]:
            return await choicemsg.delete()

        await self.stop_playing(str(ctx.guild.id))

        return await choicemsg.edit(
            embed=Embed(title="✅Плеер остановлен", color=Color.red())
        )

    @hybrid_command(
        aliases=["dc", "disconnect"], help="Команда для отключения от голосового канала"
    )
    async def leave(self, ctx: Context):
        await self.orca.Leave(GuildOnlyRequest(guildID=str(ctx.guild.id)))

        return await ok(ctx, "Отключен от голосового канала")

    @hybrid_command(
        aliases=["c", "connect"], help="Команда для подключения к голосовому каналу"
    )
    async def join(self, ctx: Context):
        if ctx.author.voice is None:
            return await ctx.send("Не в голосовом канале")

        await self.orca.Join(
            JoinRequest(
                guildID=str(ctx.guild.id),
                channelID=str(ctx.author.voice.channel.id),
            )
        )

        return await ok(ctx, "Подключен к голосовому каналу")

    @hybrid_command(
        aliases=["n", "np", "playing", "current"],
        help="Команда для отображения текущего трека",
    )
    async def now(self, ctx):
        res: GetTracksReply = await self.orca.GetTracks(
            GetTracksRequest(
                guildID=str(ctx.guild.id),
                start=0,
                end=1,
            )
        )
        if len(res.tracks) < 1:
            return await ctx.send("Ничего не играет")
        current = res.tracks[0]
        if current.live:
            poss = "🔴 LIVE"
        else:
            poss = f"{format_time(current.position.ToSeconds())}/{format_time(current.duration.ToSeconds())}"
        song = f"[{current.title}]({current.displayURL})\n({poss})"
        embed = Embed(
            color=get_embed_color(current.displayURL),
            title="Сейчас играет",
            description=song,
        )
        await ctx.send(embed=embed)

    @hybrid_command(
        aliases=["q", "list"],
        usage="queue [страница]",
        help="Команда для отображения очереди воспроизведения",
    )
    async def queue(self, ctx: Context, page: int = 1):
        if page < 1:
            return await ctx.send("Страница не может быть отрицательной")

        q = Queue(
            self.orca,
            ctx.guild.id,
            page,
        )

        try:
            await q.get()
        except QueueEmpty:
            return await ctx.send("Ничего не играет")

        if ctx.interaction is not None:
            await ctx.interaction.response.send_message(
                "Очередь отправлена отдельным сообщением",
                ephemeral=True,
                delete_after=60,
            )

            msg = await ctx.channel.send(embed=q.embed)
        else:
            msg = await ctx.reply(embed=q.embed)

        q.message = msg

        if ctx.guild.id in self.queues:
            old: Queue = self.queues[ctx.guild.id]
            if old.message is not None:
                try:
                    await old.message.delete()
                except Exception as e:
                    print(
                        f"Error while deleting old queue message: {e}", file=sys.stderr
                    )

        self.queues[ctx.guild.id] = q

        return await self.sql_client.sql_req(
            "INSERT INTO queues (guild_id, channel_id, message_id, page) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE channel_id = %s, message_id = %s, page = %s",
            ctx.guild.id,
            ctx.channel.id,
            msg.id,
            page,
            ctx.channel.id,
            msg.id,
            page,
        )

    @hybrid_command(
        aliases=["r", "delete"],
        usage="remove <номер трека>",
        help="Команда для удаления трека из очереди",
    )
    async def remove(self, ctx, pos: int):
        if pos < 0:
            return await ctx.send("Номер не может быть отрицательным")

        await self.orca.Remove(
            RemoveRequest(
                guildID=str(ctx.guild.id),
                position=pos,
            )
        )

        return await ok(ctx, "Трек удален")

    @hybrid_command(
        usage="save <название>", help="Команда для сохранения очереди в плейлист"
    )
    async def save(self, ctx: Context, *, name: str):
        await self.orca.SavePlaylist(
            SavePlaylistRequest(
                guildID=str(ctx.guild.id),
                userID=str(ctx.author.id),
                name=name,
            )
        )

        return await ok(ctx, "Плейлист создан")

    @hybrid_command(
        aliases=["pls"], help="Команда для просмотра сохраненных плейлистов"
    )
    async def playlists(self, ctx: Context):
        res: ListPlaylistsReply = await self.orca.ListPlaylists(
            ListPlaylistsRequest(
                guildID=str(ctx.guild.id),
                userID=str(ctx.author.id),
            )
        )

        embed_lines = []
        for i, playlist in enumerate(res.playlists):
            embed_lines.append(
                f"{i + 1}. **{playlist.name}** - "
                f'{playlist.totalTracks} {sform(playlist.totalTracks, "трек")} '
                f"({format_time(playlist.totalDuration.ToSeconds())})"
            )

        embed = Embed(
            color=Color.dark_purple(),
            title="Сохраненные плейлисты",
            description="\n".join(embed_lines),
        )

        return await ctx.send(embed=embed)

    @hybrid_command(help="Команда для добавления сохраненного плейлиста в очередь")
    async def load(self, ctx: Context):
        if ctx.author.voice is None:
            return await ctx.send("Не в голосовом канале")

        res: ListPlaylistsReply = await self.orca.ListPlaylists(
            ListPlaylistsRequest(
                guildID=str(ctx.guild.id),
                userID=str(ctx.author.id),
            )
        )

        embed_lines = []
        for i, playlist in enumerate(res.playlists):
            embed_lines.append(
                f"{i + 1}. **{playlist.name}** - "
                f'{playlist.totalTracks} {sform(playlist.totalTracks, "трек")} '
                f"({format_time(playlist.totalDuration.ToSeconds())})"
            )

        embed = Embed(
            color=Color.dark_purple(),
            title="Выберите плейлист",
            description="\n".join(embed_lines),
        )
        embed.set_footer(
            text="Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены"
        )

        choicemsg = await ctx.send(embed=embed)

        canc = False

        prefixes = await self.bot.get_prefix(ctx.message)

        def verify(m):
            nonlocal canc

            if m.content.isdigit():
                return (
                    0 <= int(m.content) <= len(res.playlists)
                    and m.channel == ctx.channel
                    and m.author == ctx.author
                )

            canc = (
                m.channel == ctx.channel
                and m.author == ctx.author
                and any(
                    m.content.startswith(prefix) and len(m.content) > len(prefix)
                    for prefix in prefixes
                )
            )
            return canc

        msg = await self.bot.wait_for("message", check=verify, timeout=30)
        if canc or int(msg.content) == 0:
            await choicemsg.delete()

            return

        chosen = res.playlists[int(msg.content) - 1].id

        res: PlayReply = await self.orca.LoadPlaylist(
            LoadPlaylistRequest(
                guildID=str(ctx.guild.id),
                playlistID=chosen,
                channelID=str(ctx.author.voice.channel.id),
            )
        )

        embed = Embed(color=Color.dark_purple())

        if res.total == 1:
            embed.title = "✅Трек добавлен"
            embed.description = f"[{res.tracks[0].title}]({res.tracks[0].displayURL})"
        else:
            embed.title = "✅Треки добавлены"
            embed.description = "\n".join(
                [f"[{track.title}]({track.displayURL})" for track in res.tracks[:10]]
            )
            if res.total > 10:
                embed.description += f"\n... и еще {res.total - 10}"

        return await ctx.send(embed=embed)


async def music_setup(bot):
    cog = Music(bot)
    await bot.add_cog(cog)
