from math import ceil
from time import time

import regex as re
from discord import ButtonStyle, Color, Embed, Interaction, Message
from discord.ext.commands import Bot
from discord.ui import Button, View

from orca_pb2 import (
    GetCurrentReply,
    GetTracksReply,
    GetTracksRequest,
    GuildOnlyRequest,
    TrackData,
)
from orca_pb2_grpc import OrcaStub


class QueueEmpty(Exception):
    pass


PAGE_SIZE = 5

spotify_rx = re.compile(
    r"(?:spotify:|(?:https?:\/\/)?(?:www\.)?open\.spotify\.com\/)(playlist|track|album)(?:\:|\/)([a-zA-Z0-9]+)(.*)$"
)
url_rx = re.compile(r"https?://(?:www\.)?.+")

embed_colors = {
    "youtube.com": Color.red(),
    "youtu.be": Color.red(),
    "open.spotify.com": Color.green(),
    "soundcloud.com": Color.orange(),
    "twitch.tv": Color.purple(),
    "bandcamp.com": Color.blue(),
    "vk.com": Color.blue(),
    "vimeo.com": Color.dark_blue(),
}


def get_embed_color(query):
    if spotify_rx.match(query):
        return Color.green()
    if url_rx.match(query):
        for service in embed_colors:
            if service in query:
                return embed_colors[service]
        return Color.blurple()
    return Color.red()


def format_time(t):
    hours, remainder = divmod(t, 3600)
    minutes, seconds = divmod(remainder, 60)

    return "%02d:%02d:%02d" % (hours, minutes, seconds)


async def voice_check(bot: Bot, interaction: Interaction):
    my_voice = bot.get_guild(interaction.guild_id).me.voice
    author_voice = interaction.user.voice

    return (
        my_voice is None
        or author_voice is None
        or my_voice.channel != author_voice.channel
    )


class UpdateRateLimiter:
    def __init__(self, rate: int):
        # rate is in seconds
        self.rate = rate
        self.last_update = 0

    @property
    def can_update(self):
        now = time()
        if (now - self.last_update) < self.rate:
            return False

        self.last_update = now

        return True


class PauseButton(Button):
    pause_id = 1211315174816874506
    pause = f"<:pause:{pause_id}>"
    resume_id = 1211315886179483688
    resume = f"<:play:{resume_id}>"
    choice = {
        True: resume,
        False: pause,
    }

    def __init__(self, bot: Bot, queue: "Queue"):
        super().__init__(
            label="",
            emoji=self.choice[queue.paused],
            style=ButtonStyle.grey if queue.paused else ButtonStyle.blurple,
        )

        self.bot = bot
        self.queue = queue
        self.orca = queue.orca

    async def callback(self, interaction: Interaction):
        if await voice_check(self.bot, interaction):
            action = (
                "приостановить" if self.emoji.id == self.pause_id else "возобновить"
            )

            return await interaction.response.send_message(
                f"Вы должны находиться в одном голосовом канале с ботом, чтобы {action} воспроизведение.",
                ephemeral=True,
                delete_after=30,
            )

        if self.emoji.id == self.pause_id:
            await self.orca.Pause(
                GuildOnlyRequest(
                    guildID=str(self.queue.guild_id),
                )
            )
        else:
            await self.orca.Resume(
                GuildOnlyRequest(
                    guildID=str(self.queue.guild_id),
                )
            )

        await interaction.response.defer()

    async def update(self):
        self.emoji = self.choice[self.queue.paused]
        self.style = ButtonStyle.grey if self.queue.paused else ButtonStyle.blurple


class LoopButton(Button):
    loop_emoji = "<:loop:1211318976286560318>"

    def __init__(self, queue: "Queue"):
        super().__init__(
            label="",
            emoji=self.loop_emoji,
            style=ButtonStyle.blurple if queue.looping else ButtonStyle.grey,
        )

        self.queue = queue
        self.orca = queue.orca

    async def callback(self, interaction: Interaction):
        await self.orca.Loop(
            GuildOnlyRequest(
                guildID=str(self.queue.guild_id),
            )
        )

        await interaction.response.defer()

    async def update(self):
        self.style = ButtonStyle.blurple if self.queue.looping else ButtonStyle.grey


class SkipButton(Button):
    skip_emoji = "<:skip:1211320197219090463>"

    def __init__(self, bot: Bot, queue: "Queue"):
        super().__init__(
            label="",
            emoji=self.skip_emoji,
            style=ButtonStyle.blurple,
        )

        self.bot = bot
        self.queue = queue
        self.orca = queue.orca

    async def callback(self, interaction: Interaction):
        if await voice_check(self.bot, interaction):
            return await interaction.response.send_message(
                "Вы должны находиться в одном голосовом канале с ботом, чтобы пропустить трек.",
                ephemeral=True,
                delete_after=30,
            )

        await self.orca.Skip(
            GuildOnlyRequest(
                guildID=str(self.queue.guild_id),
            )
        )

        await interaction.response.defer()


class ShuffleButton(Button):
    shuffle_emoji = "<:shuffle:1211326244965064754>"

    def __init__(self, bot: Bot, queue: "Queue"):
        super().__init__(
            label="",
            emoji=self.shuffle_emoji,
            style=ButtonStyle.blurple,
        )

        self.bot = bot
        self.queue = queue
        self.orca = queue.orca

    async def callback(self, interaction: Interaction):
        if await voice_check(self.bot, interaction):
            return await interaction.response.send_message(
                "Вы должны находиться в одном голосовом канале с ботом, чтобы перемешать очередь.",
                ephemeral=True,
                delete_after=30,
            )

        await self.orca.ShuffleQueue(
            GuildOnlyRequest(
                guildID=str(self.queue.guild_id),
            )
        )

        await interaction.response.defer()


class PrevButton(Button):
    prev_emoji = "<:prev:1211338083371450368>"

    def __init__(self, queue: "Queue"):
        super().__init__(
            label="",
            emoji=self.prev_emoji,
            style=ButtonStyle.blurple,
            row=1,
            disabled=queue.page <= 1,
        )

        self.queue = queue
        self.orca = queue.orca

    async def callback(self, interaction: Interaction):
        self.queue.page -= 1
        await self.queue.update()

        await interaction.response.defer()

    async def update(self):
        self.disabled = self.queue.page <= 1


class NextButton(Button):
    next_emoji = "<:next:1211338081102471219>"

    def __init__(self, queue: "Queue"):
        super().__init__(
            label="",
            emoji=self.next_emoji,
            style=ButtonStyle.blurple,
            row=1,
            disabled=queue.page >= queue.pages,
        )

        self.queue = queue
        self.orca = queue.orca

    async def callback(self, interaction: Interaction):
        self.queue.page += 1
        await self.queue.update()

        await interaction.response.defer()

    async def update(self):
        self.disabled = self.queue.page >= self.queue.pages


class FirstButton(Button):
    first_emoji = "<:first:1211344347463942214>"

    def __init__(self, queue: "Queue"):
        super().__init__(
            label="",
            emoji=self.first_emoji,
            style=ButtonStyle.blurple,
            row=1,
            disabled=queue.page <= 1,
        )

        self.queue = queue
        self.orca = queue.orca

    async def callback(self, interaction: Interaction):
        self.queue.page = 1
        await self.queue.update()

        await interaction.response.defer()

    async def update(self):
        self.disabled = self.queue.page <= 1


class LastButton(Button):
    last_emoji = "<:last:1211344345580703884>"

    def __init__(self, queue: "Queue"):
        super().__init__(
            label="",
            emoji=self.last_emoji,
            style=ButtonStyle.blurple,
            row=1,
            disabled=queue.page >= queue.pages,
        )

        self.queue = queue
        self.orca = queue.orca

    async def callback(self, interaction: Interaction):
        self.queue.page = self.queue.pages
        await self.queue.update()

        await interaction.response.defer()

    async def update(self):
        self.disabled = self.queue.page >= self.queue.pages


class QueueControl(View):

    def __init__(self, queue: "Queue", bot: Bot):
        self.queue = queue

        # no timeout for interactions
        super().__init__(timeout=None)

        self.add_item(PauseButton(bot, queue))
        self.add_item(LoopButton(queue))
        self.add_item(SkipButton(bot, queue))
        self.add_item(ShuffleButton(bot, queue))

        self.add_item(FirstButton(queue))
        self.add_item(PrevButton(queue))
        self.add_item(NextButton(queue))
        self.add_item(LastButton(queue))

    async def update(self):
        for child in self.children:
            if hasattr(child, "update"):
                await child.update()


class Queue:

    def __init__(
        self,
        bot: Bot,
        orca: OrcaStub,
        guild_id: int,
        page: int,
    ):
        self.bot = bot
        self.orca = orca
        self.guild_id: int = guild_id
        self.message: Message = None
        self._view: QueueControl = None

        self.update_rl = UpdateRateLimiter(2.5)

        self.current: TrackData = None
        self.tracks: list[TrackData] = []
        self.looping = False
        self.paused = False
        self.page = page
        self.total = 0
        self.remaining = 0

    async def get(self):
        currentres: GetTracksReply = await self.orca.GetTracks(
            GetTracksRequest(
                guildID=str(self.guild_id),
                start=0,
                end=1,
            )
        )
        if len(currentres.tracks) < 1:
            raise QueueEmpty

        current = currentres.tracks[0]

        res: GetTracksReply = await self.orca.GetTracks(
            GetTracksRequest(
                guildID=str(self.guild_id),
                start=self.start,
                end=self.start + PAGE_SIZE,
            )
        )

        self.current = current
        self.tracks = res.tracks
        self.looping = res.looping
        self.paused = res.paused
        self.total = res.totalTracks
        self.remaining = res.remaining

    async def get_current(self):
        currentres: GetCurrentReply = await self.orca.GetCurrent(
            GuildOnlyRequest(
                guildID=str(self.guild_id),
            )
        )
        if currentres.track is None:
            raise QueueEmpty

        self.current = currentres.track
        self.looping = currentres.looping
        self.paused = currentres.paused

    @property
    def start(self):
        return 1 + PAGE_SIZE * (self.page - 1)

    @property
    def pages(self):
        return ceil((self.total - 1) / PAGE_SIZE)

    @property
    def color(self):
        return get_embed_color(self.current.displayURL)

    @property
    def _to_embed_content(self):
        if self.current.live:
            poss = "🔴 LIVE"
        else:
            poss = f"{format_time(self.current.position.ToSeconds())}/{format_time(self.current.duration.ToSeconds())}"

        playstate = "⏸️`На паузе:`" if self.paused else "▶️`Сейчас играет:`"
        result = f"\n{playstate} [**{self.current.title}**]({self.current.displayURL}) ({poss})\n\n\n"

        for index, track in enumerate(self.tracks):
            result += (
                f"`{self.start + index}.` [**{track.title}**]({track.displayURL})\n"
            )

        return result

    @property
    def embed(self):
        embed = Embed(color=self.color, description=self._to_embed_content)
        embed.set_footer(
            text=f"Страница: {self.page}/{self.pages}\n"
            f"Всего треков: {self.total} ({format_time(self.remaining.ToSeconds())})\n"
            f'Повторение: {"вкл." if self.looping else "выкл."}'
        )
        return embed

    @property
    def view(self):
        if self._view is None:
            self._view = QueueControl(self, self.bot)

        return self._view

    # return value indicates whether to keep the queue in the queue map
    async def update(self, *, only_current=False) -> bool:
        if self.message is None:
            return True

        if not self.update_rl.can_update:
            return True

        if self.page < 1:
            self.page = 1
        elif self.page > self.pages > 0:
            self.page = self.pages

        try:
            if only_current:
                await self.get_current()
            else:
                await self.get()
        except QueueEmpty:
            await self.message.delete()

            return False

        if self.page > self.pages > 0:
            self.page = self.pages

        await self.view.update()
        await self.message.edit(embed=self.embed, view=self.view)

        return True
