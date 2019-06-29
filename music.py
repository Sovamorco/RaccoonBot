import requests
import youtube_dl
from credentials import googleServiceKey
import json
from html import unescape


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
