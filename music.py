import requests
import youtube_dl
from credentials import googleServiceKey
import json
from html import unescape
from urllib.parse import urlparse, parse_qs


def searchyt(text):
    result = []
    payload = {
        'part': 'snippet',
        'maxResults': '10',
        'q': text,
        'key': googleServiceKey,
        'type': 'video'
    }
    searchUrl = 'https://www.googleapis.com/youtube/v3/search'
    videoUrl = 'https://www.youtube.com/watch?v={}'
    r = requests.get(searchUrl, params=payload)
    results = json.loads(r.text)['items']
    for video in results:
        result.append({
            'id': video['id']['videoId'],
            'url': videoUrl.format(video['id']['videoId']),
            'title': unescape(video['snippet']['title'])
        })
    return result


def searchplaylist(url):
    result = []
    parsed = urlparse(url)
    plid = parse_qs(parsed.query)['list'][0]
    payload = {
        'part': 'snippet',
        'maxResults': '50',
        'playlistId': plid,
        'key': googleServiceKey,
        'pageToken': ''
    }
    searchUrl = 'https://www.googleapis.com/youtube/v3/playlistItems'
    videoUrl = 'https://www.youtube.com/watch?v={}'
    r = requests.get(searchUrl, params=payload)
    results = json.loads(r.text)
    videos = results['items']
    for video in videos:
        result.append({
            'id': video['snippet']['resourceId']['videoId'],
            'url': videoUrl.format(video['snippet']['resourceId']['videoId']),
            'title': unescape(video['snippet']['title'])
        })
    while 'nextPageToken' in results.keys():
        payload['pageToken'] = results['nextPageToken']
        r = requests.get(searchUrl, params=payload)
        results = json.loads(r.text)
        videos = results['items']
        for video in videos:
            result.append({
                'id': video['snippet']['resourceId']['videoId'],
                'url': videoUrl.format(video['snippet']['resourceId']['videoId']),
                'title': unescape(video['snippet']['title'])
            })
    return result


def download_video(link):
    ydl_opts = {
        'format': 'worstaudio/worst',
        'outtmpl': '%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128'}]
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
        # return ydl.extract_info(link, download=False)


async def get_stream_url(link):
    ydl_opts = {'quiet': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        formats = ydl.extract_info(link, download=False)['formats']
        for ent in formats:
            if ent['ext'] == 'webm' and ent['format_note'] == 'DASH audio' and ent['acodec'] == 'opus':
                return ent['url']
