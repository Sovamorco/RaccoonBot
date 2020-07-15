from discord import Color


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
