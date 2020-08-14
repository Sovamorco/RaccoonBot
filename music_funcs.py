from asyncio import get_event_loop
from base64 import b64encode
from time import time

import regex as re
from aiohttp import ClientSession
from credentials import vk_audio_token, spotify_client_id, spotify_client_secret
from discord import Embed, Color

agent = 'KateMobileAndroid/52.1 lite-445 (Android 4.4.2; SDK 19; x86; unknown Android SDK built for x86; en)'

vk_album_rx = re.compile(r'(?:https?://)?(?:www\.)?vk.com/(audios-?[0-9]+\?(?:section=playlists&)?z=audio_playlist-?[0-9]+_[0-9]+|music/album/-?[0-9]+_[0-9]+|music/playlist/-?[0-9]+_[0-9]+)')
vk_pers_rx = re.compile(r'(?:https?://)?(?:www\.)?vk.com/audios-?[0-9]+')
spotify_rx = re.compile(r'(?:spotify:|(?:https?:\/\/)?(?:www\.)?open\.spotify\.com\/)(playlist|track|album)(?:\:|\/)([a-zA-Z0-9]+)(.*)$')
url_rx = re.compile(r'https?://(?:www\.)?.+')


class Track:
    def __init__(self, author, title, url=None, show_url=None):
        self.author = author
        self.title = title
        self.url = url
        self._show_url = show_url

    def __str__(self):
        return f'{self.author} - {self.title}'

    @property
    def show_url(self):
        return self._show_url or self.url

    @property
    def uri(self):
        return self.url or str(self)

    async def get_track(self, player):
        track = await get_track(player, self.uri, True)
        track['info']['author'] = self.author
        track['info']['title'] = str(self)
        track['info']['uri'] = self.show_url
        return track


class Playlist:
    def __init__(self, title, tracks):
        self.title = title
        self.tracks = tracks

    def __str__(self):
        return self.title

    async def add(self, player, requester, force=False):
        if not self.tracks:
            return
        simple = isinstance(self.tracks[0], dict)
        tracks = reversed(self.tracks) if force else self.tracks
        index = 0 if force else None
        first = True
        for track in tracks:
            if simple:
                player.add(requester=requester, track=track, index=index)
            else:
                audiotrack = await track.get_track(player)
                player.add(requester=requester, track=audiotrack, index=index)
            if first:
                await player.play()
                first = False


async def get_vk_album(url):
    album = re.search(r'-?[0-9]+_[0-9]+', url)
    if album:
        album = album.group()
    else:
        return Embed(color=Color.blue(), title='❌Плейлист не найден')
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
    async with ClientSession() as client:
        res = await client.get('https://api.vk.com/method/audio.get', headers=headers, params=params)
        playlist = await client.get('https://api.vk.com/method/audio.getPlaylistById', headers=headers, params=params)
        res = await res.json()
        playlist = await playlist.json()
    if 'error' in res.keys():
        if res['error']['error_code'] == 201:
            return Embed(color=Color.blue(), title='❌Нет доступа к аудио пользователя')
        elif res['error']['error_code'] == 15:
            return Embed(color=Color.blue(), title='❌Нет доступа к аудио сообщества')
        else:
            print(res)
            return Embed(color=Color.blue(), title='❌Ошибка при добавлении плейлиста')
    res = res['response']
    playlist = playlist['response']
    return Playlist(playlist['title'],
                    [Track(item['artist'], item['title'], item['url'], f'https://vk.com/music/album/{album}') for item in res['items'] if item['url']])


async def get_vk_personal(url):
    user = re.search(r'-?[0-9]+', url)
    if user:
        user = user.group()
    else:
        return Embed(color=Color.blue(), title='❌Плейлист не найден')
    headers = {
        'User-Agent': agent
    }
    params = {
        'access_token': vk_audio_token,
        'v': '5.999',
        'owner_id': user,
        'need_user': 1
    }
    async with ClientSession() as client:
        ans = await client.get('https://api.vk.com/method/audio.get', headers=headers, params=params)
        res = await ans.json()
    if 'error' in res.keys():
        if res['error']['error_code'] == 201:
            return Embed(color=Color.blue(), title='❌Нет доступа к аудио пользователя')
        else:
            return Embed(color=Color.blue(), title='❌Ошибка при добавлении плейлиста')
    playlist = res['response']
    items = playlist['items']
    user_info = items.pop(0)
    return Playlist(f'Аудиозаписи {user_info["name_gen"]}',
                    [Track(item['artist'], item['title'], item['url'], f'https://vk.com/audios/{user}') for item in items if item['url']])


class Spotify:
    """
    Класс, нагло спизженный из Just-Some-Bots/MusicBot
    """
    OAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'
    API_BASE = 'https://api.spotify.com/v1/'

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.aiosession = ClientSession()
        self.loop = get_event_loop()

        self.token = None

        self.loop.run_until_complete(self.get_token())

    @staticmethod
    def _make_token_auth(client_id, client_secret):
        auth_header = b64encode((client_id + ':' + client_secret).encode('ascii'))
        return {'Authorization': 'Basic %s' % auth_header.decode('ascii')}

    async def get_track(self, uri):
        return await self.make_spotify_req(self.API_BASE + f'tracks/{uri}')

    async def get_album(self, uri):
        return await self.make_spotify_req(self.API_BASE + f'albums/{uri}')

    async def get_playlist(self, uri):
        return await self.make_spotify_req(self.API_BASE + f'playlists/{uri}')

    async def get_playlist_tracks(self, uri):
        return await self.make_spotify_req(self.API_BASE + f'playlists/{uri}/tracks')

    async def make_spotify_req(self, url):
        token = await self.get_token()
        return await self.make_get(url, headers={'Authorization': f'Bearer {token}'})

    async def make_get(self, url, headers=None):
        async with self.aiosession.get(url, headers=headers) as r:
            return await r.json()

    async def make_post(self, url, payload, headers=None):
        async with self.aiosession.post(url, data=payload, headers=headers) as r:
            return await r.json()

    async def get_token(self):
        if self.token and not await self.check_token(self.token):
            return self.token['access_token']

        token = await self.request_token()
        token['expires_at'] = int(time()) + token['expires_in']
        self.token = token
        return self.token['access_token']

    @staticmethod
    async def check_token(token):
        now = int(time())
        return token['expires_at'] - now < 60

    async def request_token(self):
        payload = {'grant_type': 'client_credentials'}
        headers = self._make_token_auth(self.client_id, self.client_secret)
        r = await self.make_post(self.OAUTH_TOKEN_URL, payload=payload, headers=headers)
        return r


spotify = Spotify(spotify_client_id, spotify_client_secret)


async def get_spotify_track(uri):
    res = await spotify.get_track(uri)
    return Track(res["artists"][0]["name"], res["name"], show_url=res['external_urls']['spotify'])


async def get_spotify_album(uri):
    res = await spotify.get_album(uri)
    tracks = [Track(item['artists'][0]['name'], item['name'], show_url=item['external_urls']['spotify']) for item in res['tracks']['items']]
    return Playlist(res['name'], tracks)


async def get_spotify_playlist(uri):
    res = []
    r = await spotify.get_playlist_tracks(uri)
    while True:
        res.extend(r['items'])
        if r['next'] is None:
            break
        r = await spotify.make_spotify_req(r['next'])
    tracks = [Track(item['track']['artists'][0]['name'], item['track']['name'], show_url=item['track']['external_urls']['spotify']) for item in res if not item['is_local']]
    playlist = await spotify.get_playlist(uri)
    return Playlist(playlist['name'], tracks)


async def get_track(player, query, force_first=False):
    query = query.strip('<>')
    spm = spotify_rx.match(query)
    if spm:
        typ = spm.group(1)
        iden = spm.group(2)
        if typ == 'track':
            return await get_spotify_track(iden)
        elif typ == 'album':
            return await get_spotify_album(iden)
        elif typ == 'playlist':
            return await get_spotify_playlist(iden)
    elif vk_album_rx.match(query):
        return await get_vk_album(query)
    elif vk_pers_rx.match(query):
        return await get_vk_personal(query)
    is_url = True
    if not url_rx.match(query):
        is_url = False
        query = f'ytsearch:{query}'
    results = await player.node.get_tracks(query)
    if not results or not results['tracks']:
        return 'Ничего не найдено'
    if results['loadType'] == 'PLAYLIST_LOADED':
        return Playlist(results['playlistInfo']['name'], results['tracks'])
    if is_url or force_first or len(results['tracks']) == 1:
        return results['tracks'][0]
    return results['tracks']


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
