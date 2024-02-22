import os

from discord.ext.commands import Context
from pymorphy3 import MorphAnalyzer
from pymorphy3.shapes import restore_capitalization

dev = os.getenv("PRODUCTION") != "true"

morph = MorphAnalyzer()

broken = {"печенька": ["печенька", "печеньки", "печенек"]}


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


async def ok(ctx: Context, msg: str):
    if ctx.interaction is None:
        return await ctx.message.add_reaction("👌")

    return await ctx.send(msg + " 👌")
