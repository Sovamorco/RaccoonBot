from check import *
from music import *
from misc import *
from games import *
from cookies import *
from moderation import *
from credentials import discord_status, discord_bot_token, discord_alpha_token, dev
from utils import get_prefix

default_prefix = '?'


def prefix(dbot, msg):
    servid = str(msg.guild.id)
    prefixes = json.load(open('resources/prefixes.json', 'r'))
    pr = 'r?' if dev else prefixes.get(servid, default_prefix)
    return commands.when_mentioned_or(pr)(dbot, msg)


bot = commands.Bot(command_prefix=prefix, description='Cutest bot on Discord (subjective)', case_insensitive=True)
bot.remove_command('help')


async def change_status():
    while True:
        try:
            if dev:
                status = 'In Development'
            else:
                status = '?help | {}'.format(random.choice(discord_status))
            activity = discord.Streaming(name=status, url='https://twitch.tv/mrdandycorn')
            await bot.change_presence(activity=activity)
        except Exception as e:
            print(f'Got Exception in change_status: {e}')
        finally:
            await asyncio.sleep(300)


@bot.event
async def on_ready():
    bot.loop.create_task(change_status())
    try:
        misc_setup(bot)
        music_setup(bot)
        cookies_setup(bot)
        await games_setup(bot)
        mod_setup(bot)
    except discord.errors.ClientException:
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


@bot.command(name='help', pass_context=True, help='Команда для вывода этого сообщения', usage='{}help [команда]')
async def help_(ctx, request=None):
    commandlist = {}
    try:
        pref = await get_prefix(bot, ctx.message)
        if request is None:
            embed = discord.Embed(color=discord.Color.dark_purple(), title='Команды')
            for command in bot.commands:
                if not command.hidden:
                    if command.cog_name is not None:
                        cog = command.cog_name
                    else:
                        cog = 'Main'
                    if cog not in commandlist.keys():
                        commandlist[cog] = [command.name]
                    else:
                        commandlist[cog].append(command.name)
            for cog in sorted(commandlist.keys()):
                commandlist[cog] = ', '.join(sorted(commandlist[cog]))
                embed.add_field(name=cog, value=commandlist[cog], inline=False)
            embed.set_footer(text=f'Более подробно: {pref}help <команда>')
            return await ctx.send(embed=embed)
        for command in bot.commands:
            if ((command.name == request.lower()) or (request.lower() in command.aliases)) and not command.hidden:
                if command.aliases:
                    embed = discord.Embed(color=discord.Color.dark_purple(), title='[{}|{}]'.format(command.name, '|'.join(command.aliases)))
                else:
                    embed = discord.Embed(color=discord.Color.dark_purple(), title=command.name)
                embed.add_field(name='Описание', value=command.help, inline=False)
                embed.add_field(name='Использование', value=command.usage.format(pref), inline=False)
                return await ctx.send(embed=embed)
        return await ctx.send('Нет команды {}'.format(request))
    except Exception as e:
        await ctx.send('Ошибка: \n {}'.format(e))


if dev:
    bot.run(discord_alpha_token)
else:
    bot.run(discord_bot_token)
