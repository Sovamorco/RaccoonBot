from math import ceil

import regex as re
from discord import Embed, Color
from discord.ext.commands import CommandInvokeError

from orca_pb2 import TrackData

spotify_rx = re.compile(
    r'(?:spotify:|(?:https?:\/\/)?(?:www\.)?open\.spotify\.com\/)(playlist|track|album)(?:\:|\/)([a-zA-Z0-9]+)(.*)$')
url_rx = re.compile(r'https?://(?:www\.)?.+')

embed_colors = {
    'youtube.com': Color.red(),
    'youtu.be': Color.red(),
    'open.spotify.com': Color.green(),
    'soundcloud.com': Color.orange(),
    'twitch.tv': Color.purple(),
    'bandcamp.com': Color.blue(),
    'vk.com': Color.blue(),
    'vimeo.com': Color.dark_blue()
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

    return '%02d:%02d:%02d' % (hours, minutes, seconds)


class MusicCommandError(CommandInvokeError):
    pass


queues = []


class Queue:
    def __init__(self, current: TrackData, tracks: list[TrackData], looping: bool, page: int, total: int, remaining: int):
        self.current = current
        self.tracks = tracks
        self.looping = looping
        self.page = page
        self.start = (page - 1) * 10 + 1
        self.total = total
        self.remaining = remaining

    @property
    def color(self):
        return get_embed_color(self.current.displayURL)

    @property
    def _to_embed_content(self):
        if self.current.live:
            poss = '🔴 LIVE'
        else:
            poss = f'{format_time(self.current.position.ToSeconds())}/{format_time(self.current.duration.ToSeconds())}'
        result = f'\n`Сейчас играет:` [**{self.current.title}**]({self.current.displayURL}) ({poss})\n\n\n'
        for index, track in enumerate(self.tracks):
            result += f'`{self.start + index}.` [**{track.title}**]({track.displayURL})\n'
        return result

    @property
    def embed(self):
        embed = Embed(color=self.color, description=self._to_embed_content)
        embed.set_footer(text=f'Страница: {self.page}/{ceil((self.total - 1) / 10)}\n'
                              f'Всего треков: {self.total} ({format_time(self.remaining)})\n'
                              f'Повторение: {"вкл." if self.looping else "выкл."}')
        return embed
