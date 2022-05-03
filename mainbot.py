from traceback import print_exception

from discord import ClientException, Streaming, Intents
from discord.ext.commands import when_mentioned_or, MissingRequiredArgument, BadArgument

from cookies import *
from games import *
from misc import *
from moderation import *
from music import *
from utils import dev

default_prefix = '?'


def prefix(dbot, msg):
    destid = str(msg.guild.id) if msg.guild else str(msg.author.id)
    prefixes = load(open('resources/prefixes.json', 'r'))
    pr = 'r?' if dev else prefixes.get(destid, default_prefix)
    return when_mentioned_or(pr)(dbot, msg)


bot = Bot(command_prefix=prefix, description='Cutest bot on Discord (subjective)', case_insensitive=True, intents=Intents.default())
bot.remove_command('help')


async def change_status():
    while True:
        try:
            if dev:
                status = 'In Development'
            else:
                status = '?help | {}'.format(choice(secrets['discord_status']))
            activity = Streaming(name=status, url='https://twitch.tv/twitch')
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f'Got Exception in change_status: {e}')
        finally:
            await sleep(300)


@bot.event
async def on_ready():
    Path('resources').mkdir(exist_ok=True)
    prefixes = Path('resources/prefixes.json')
    if not prefixes.exists():
        prefixes.write_text('{}')
    bot.loop.create_task(change_status())
    try:
        await misc_setup(bot)
        await music_setup(bot)
        await cookies_setup(bot)
        await games_setup(bot)
        await mod_setup(bot)
    except ClientException:
        pass
    print('Logged on as', bot.user)


@bot.command(name='help', pass_context=True, help='Команда для вывода этого сообщения', usage='help [команда]')
async def help_(ctx, request=None):
    commandlist = {}
    try:
        if request is None:
            embed = Embed(color=Color.dark_purple(), title='Команды')
            for comm in bot.commands:
                if not comm.hidden:
                    if comm.cog_name is not None:
                        cog = comm.cog_name
                    else:
                        cog = 'Main'
                    if cog not in commandlist:
                        commandlist[cog] = [comm.name]
                    else:
                        commandlist[cog].append(comm.name)
            for cog in sorted(commandlist.keys()):
                commandlist[cog] = ', '.join(sorted(commandlist[cog]))
                embed.add_field(name=cog, value=commandlist[cog], inline=False)
            embed.set_footer(text=f'Более подробно: {ctx.prefix}help <команда>')
            return await ctx.send(embed=embed)
        for comm in bot.commands:
            if request.lower() in [comm.name] + comm.aliases and not comm.hidden:
                embed = Embed(color=Color.dark_purple(), title=request.lower())
                embed.add_field(name='Описание', value=comm.help, inline=False)
                embed.add_field(name='Использование', value=ctx.prefix + (comm.usage or comm.name), inline=False)
                return await ctx.send(embed=embed)
        return await ctx.send('Нет команды {}'.format(request))
    except Exception as e:
        await ctx.send('Ошибка: \n {}'.format(e))


@bot.listen()
async def on_command_error(ctx, error):
    if isinstance(error, MissingRequiredArgument):
        return await ctx.send(f'Использование: {ctx.prefix}{ctx.command.usage or ctx.command.name}')
    elif isinstance(error, BadArgument):
        return await ctx.send(f'Неверный тип аргумента\nИспользование: {ctx.prefix}{ctx.command.usage or ctx.command.name}')
    elif isinstance(error, MusicCommandError):
        return await ctx.send(error.original)
    elif isinstance(error, CommandInvokeError) and str(error.original):
        print_exception(type(error), error, error.__traceback__)
        return await ctx.send(f'Ошибка:\n{error.original}')


if dev:
    bot.run(secrets['discord_alpha_token'])
else:
    bot.run(secrets['discord_bot_token'])
