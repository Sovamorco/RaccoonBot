from discord import Color
import aiomysql
from credentials import dev, sql_user, sql_password, sql_port

host = '192.168.1.5' if dev else '127.0.0.1'
config = {'host': host, 'port': sql_port, 'user': sql_user, 'password': sql_password, 'db': 'via', 'autocommit': True}


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


async def abstract_fetch(fetch_all, table, keys=None, keys_values=None, fields=None):
    if not fields:
        fields = '*'
    else:
        fields = f'({", ".join(fields)})'
    table = f'`{table}`'
    if keys:
        keys = ', '.join([f'{key}=%s' for key in keys])
        statement = (f"SELECT {fields} FROM {table} WHERE {keys}", keys_values)
    else:
        statement = (f'SELECT {fields} FROM {table}', )
    pool = await aiomysql.create_pool(**config)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(*statement)
            if fetch_all:
                r = await cur.fetchall()
            else:
                r = await cur.fetchone()
    pool.close()
    await pool.wait_closed()
    if r is None:
        return []
    r = list(r)
    if len(r) == 1:
        return r[0]
    return r


async def confirm(uid, username, userid):
    pool = await aiomysql.create_pool(**config)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("INSERT INTO `via_profiles` (user_id, discord_confirmed, discord_name, discord_id) VALUES (%s, 1, %s, %s)"
                              " ON DUPLICATE KEY UPDATE discord_confirmed=1, discord_name=%s, discord_id=%s", [uid] + [username, userid]*2)
    pool.close()
    await pool.wait_closed()
