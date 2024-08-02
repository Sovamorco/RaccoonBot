import logging
from asyncio import run, sleep
from random import choice
from traceback import print_exception

from common import AsyncSQLClient, AsyncVaultClient, async_load_config
from discord import ClientException, Color, Embed, Intents, Streaming
from discord.ext.commands import (
    BadArgument,
    Bot,
    MissingPermissions,
    MissingRequiredArgument,
    when_mentioned_or,
)
from discord.utils import setup_logging

from cookies import cookies_setup
from games import games_setup
from migrate import migrate
from misc import misc_setup
from moderation import mod_setup
from music import music_setup
from utils import dev

default_prefix = "?"


async def prefix(dbot, msg):
    if not msg.guild:
        return ""
    prefix_d = await dbot.sql_client.sql_req(
        "SELECT prefix FROM server_data WHERE id=%s", msg.guild.id, fetch_one=True
    )
    prefix_s = default_prefix if prefix_d is None else prefix_d["prefix"]
    return when_mentioned_or(prefix_s)(dbot, msg)


bot = Bot(
    command_prefix=prefix,
    description="Cutest bot on Discord (subjective)",
    case_insensitive=True,
    intents=Intents.all(),
)
bot.remove_command("help")


async def change_status():
    while True:
        try:
            status = "?help | {}".format(choice(bot.config["discord"]["status"]))
            activity = Streaming(name=status, url="https://twitch.tv/twitch")
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f"Got Exception in change_status: {e}")
        finally:
            await sleep(300)


@bot.event
async def on_ready():
    bot.loop.create_task(change_status())
    try:
        await misc_setup(bot)
        await music_setup(bot)
        await cookies_setup(bot)
        await games_setup(bot)
        await mod_setup(bot)
    except ClientException:
        pass

    await bot.tree.sync()

    print("Logged on as", bot.user)


@bot.hybrid_command(
    name="help",
    pass_context=True,
    help="Команда для вывода этого сообщения",
    usage="help [команда]",
)
async def help_(ctx, request=None):
    commandlist = {}
    try:
        if request is None:
            embed = Embed(color=Color.dark_purple(), title="Команды")
            for comm in bot.commands:
                if not comm.hidden:
                    if comm.cog_name is not None:
                        cog = comm.cog_name
                    else:
                        cog = "Main"
                    if cog not in commandlist:
                        commandlist[cog] = [comm.name]
                    else:
                        commandlist[cog].append(comm.name)
            for cog in sorted(commandlist.keys()):
                commandlist[cog] = ", ".join(sorted(commandlist[cog]))
                embed.add_field(name=cog, value=commandlist[cog], inline=False)
            embed.set_footer(text=f"Более подробно: {ctx.prefix}help <команда>")
            return await ctx.send(embed=embed)
        for comm in bot.commands:
            if request.lower() in [comm.name] + comm.aliases and not comm.hidden:
                embed = Embed(color=Color.dark_purple(), title=request.lower())
                embed.add_field(name="Описание", value=comm.help, inline=False)
                embed.add_field(
                    name="Использование",
                    value=ctx.prefix + (comm.usage or comm.name),
                    inline=False,
                )
                return await ctx.send(embed=embed)
        return await ctx.send("Нет команды {}".format(request))
    except Exception as e:
        await ctx.send("Ошибка: \n {}".format(e))


@bot.listen()
async def on_command_error(ctx, error):
    if isinstance(error, MissingRequiredArgument):
        return await ctx.send(
            f"Использование: {ctx.prefix}{ctx.command.usage or ctx.command.name}"
        )
    elif isinstance(error, BadArgument):
        return await ctx.send(
            f"Неверный тип аргумента\nИспользование: {ctx.prefix}{ctx.command.usage or ctx.command.name}"
        )
    elif isinstance(error, MissingPermissions):
        return await ctx.send(
            f"У вас нет прав для использования этой команды\nНеобходимые права: {','.join(error.missing_permissions)}"
        )

    print_exception(type(error), error, error.__traceback__)


async def main():
    vault_client = AsyncVaultClient.from_env() if not dev else None
    config = await async_load_config(
        "config.dev.yaml" if dev else "config.yaml", vault_client=vault_client
    )
    sql_client = AsyncSQLClient(config["db"], vault_client)
    await sql_client.refresh()
    # not async but can only be done once so whatever tbh
    migrate(sql_client.config)

    bot.config = config
    bot.sql_client = sql_client

    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )

    setup_logging(
        handler=logging.StreamHandler(),
        formatter=formatter,
        level=logging.INFO,
    )

    try:
        async with bot:
            await bot.start(config["discord"]["token"])
    except KeyboardInterrupt:
        # nothing to do here
        # `asyncio.run` handles the loop cleanup
        # and `self.start` closes all sockets and the HTTPClient instance.
        return


if __name__ == "__main__":
    run(main())
