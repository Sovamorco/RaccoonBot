import os

from common import get_secrets
from pymorphy2 import MorphAnalyzer
from pymorphy2.shapes import restore_capitalization

secrets = get_secrets(
    'osu_key',
    'vk_personal_audio_token',
    'spotify_client_id',
    'spotify_client_secret',
    'discord_status',
    'discord_bot_token',
    'discord_alpha_token',
    'genius_token',
    'discord_pers_id',
    'main_password',
    'main_web_addr',
    'gachi_things',
    'genius_token',
)

dev = os.getenv('PRODUCTION') != 'true'

morph = MorphAnalyzer()

broken = {
    'печенька': ['печенька', 'печеньки', 'печенек']
}


def form(num, arr):
    if 15 > abs(num) % 100 > 10:
        return arr[2]
    if abs(num) % 10 == 1:
        return arr[0]
    if abs(num) % 10 > 4 or abs(num) % 10 == 0:
        return arr[2]
    return arr[1]


def sform(num, word):
    if word.lower() in broken:
        formed = form(num, broken[word.lower()])
    else:
        parsed = morph.parse(word)[0]
        formed = parsed.make_agree_with_number(num).word
    restored = restore_capitalization(formed, word)
    return restored
