from traceback import print_exception

from credentials import discord_status, discord_bot_token, discord_alpha_token
from discord import ClientException
from discord.ext.commands import when_mentioned_or, MissingRequiredArgument, BadArgument

from check import *
from cookies import *
from games import *
from misc import *
from moderation import *
from music import *

default_prefix = '?'


def prefix(dbot, msg):
    servid = str(msg.guild.id)
    prefixes = load(open('resources/prefixes.json', 'r'))
    pr = 'r?' if dev else prefixes.get(servid, default_prefix)
    return when_mentioned_or(pr)(dbot, msg)


bot = Bot(command_prefix=prefix, description='Cutest bot on Discord (subjective)', case_insensitive=True)
bot.remove_command('help')


async def change_status():
    while True:
        try:
            if dev:
                status = 'In Development'
            else:
                status = '?help | {}'.format(choice(discord_status))
            activity = Streaming(name=status, url='https://twitch.tv/mrdandycorn')
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f'Got Exception in change_status: {e}')
        finally:
            await sleep(300)


@bot.event
async def on_ready():
    bot.loop.create_task(change_status())
    try:
        misc_setup(bot)
        music_setup(bot)
        cookies_setup(bot)
        await games_setup(bot)
        mod_setup(bot)
    except ClientException:
        pass
    if not dev:
        await check(bot)
    print('Logged on as', bot.user)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == discord_message_id and payload.channel_id == discord_channel_id:
        print('Added ' + str(payload.emoji.name))
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if payload.emoji.name in emoji_to_role.keys():
            role = guild.get_role(emoji_to_role[payload.emoji.name])
            print(str(guild) + ' / ' + str(member) + ' / ' + str(role))
            await member.add_roles(role)
        else:
            channel = guild.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            print(str(guild) + ' / ' + str(member) + ' / ' + str(payload.emoji.name))
            await message.remove_reaction(payload.emoji, member)


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id == discord_message_id and payload.channel_id == discord_channel_id:
        print('Removed ' + str(payload.emoji.name))
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if payload.emoji.name in emoji_to_role.keys():
            role = guild.get_role(emoji_to_role[payload.emoji.name])
            print(str(guild) + ' / ' + str(member) + ' / ' + str(role))
            await member.remove_roles(role)
        else:
            pass


@bot.command(name='update', pass_context=True, hidden=True)
async def update(ctx):
    try:
        if ctx.author.id == discord_pers_id:
            await check(bot)
            await ctx.message.add_reaction('👌')
    except Exception as e:
        await ctx.send('Ошибка: \n {}'.format(e))


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
    bot.run(discord_alpha_token)
else:
    bot.run(discord_bot_token)
