from discord import Color
import aiomysql
from json import loads, dumps
from credentials import dev, SQLHost, SQLUser, SQLPass

host = SQLHost if dev else '127.0.0.1'
config = {'host': host, 'port': 3306, 'user': SQLUser, 'password': SQLPass, 'db': 'via', 'autocommit': True}


def form(num, arr):
    if 15 > abs(num) % 100 > 10:
        return arr[2]
    if abs(num) % 10 == 1:
        return arr[0]
    if abs(num) % 10 > 4 or abs(num) % 10 == 0:
        return arr[2]
    return arr[1]


async def get_prefix(bot, msg):
    pref = await bot.get_prefix(msg)
    for pr in pref:
        if str(bot.user.id) not in pr:
            return pr


def get_color(track):
    if 'youtube' in track:
        return Color.red()
    if 'soundcloud' in track:
        return Color.orange()
    if 'twitch' in track:
        return Color.purple()
    if 'bandcamp' in track:
        return Color.blue()
    if 'vimeo' in track:
        return Color.dark_blue()
    if 'mixer' in track or 'beam' in track:
        return Color.blurple()
    if 'vkuseraudio' in track:
        return Color.blue()
    return Color.greyple()


async def load_profiles():
    pool = await aiomysql.create_pool(**config)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT `user_id`, `profile` FROM `profiles`")
            profiles = await cur.fetchall()
    pool.close()
    await pool.wait_closed()
    new_profiles = {}
    for profile in profiles:
        new_profiles[profile[0]] = loads(profile[1])
    return new_profiles


async def load_profile(uid):
    pool = await aiomysql.create_pool(**config)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT `profile` FROM `profiles` WHERE `user_id`=%s", [uid])
            try:
                (r,) = await cur.fetchone()
            except TypeError:
                r = None
    pool.close()
    await pool.wait_closed()
    result = loads(r) if r else None
    return result


async def dump_profile(uid, profile):
    pool = await aiomysql.create_pool(**config)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            profile = dumps(profile, ensure_ascii=False)
            await cur.execute("INSERT INTO `profiles` (user_id, profile) VALUES (%s, %s) ON DUPLICATE KEY UPDATE profile=%s", [uid, profile, profile])
    pool.close()
    await pool.wait_closed()
