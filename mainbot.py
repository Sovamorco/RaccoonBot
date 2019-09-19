from check import *
from music import *
from misc import *
from games import *
from cookies import *
from moderation import *
from credentials import discord_status, discord_alpha_token, dev
from utils import get_prefix

default_prefix = '?'


def prefix(dbot, msg):
    servid = str(msg.guild.id)
    prefixes = json.load(open('resources/prefixes.json', 'r'))
    pr = 'r?' if dev else prefixes.get(servid, default_prefix)
    return commands.when_mentioned_or(pr)(dbot, msg)


bot = commands.Bot(command_prefix=prefix, description='Cutest bot on Discord (subjective)')
bot.remove_command('help')


async def change_status():
    while True:
        # Смена состояния(просто ради красоты)
        if dev:
            status = 'In Development'
        else:
            status = '?help | {}'.format(random.choice(discord_status))
        activity = discord.Streaming(name=status, url='https://twitch.tv/mrdandycorn')
        await bot.change_presence(activity=activity)
        await asyncio.sleep(300)


@bot.event
async def on_ready():
    bot.loop.create_task(change_status())
    try:
        misc_setup(bot)
        music_setup(bot)
        cookies_setup(bot)
        games_setup(bot)
        mod_setup(bot)
    except discord.errors.ClientException:
        pass
    # Проверка обновлений на сообщении, в случае, если что-то изменилось, пока бот был оффлайн
    if not dev:
        check()
    print('Logged on as', bot.user)


@bot.event
async def on_raw_reaction_add(payload):
    # Если реакция под нужным нам сообщением(message_id и channel_id описаны в credentials), то
    if payload.message_id == int(discord_message_id) and payload.channel_id == int(discord_channel_id):
        print('Added ' + str(payload.emoji.name))
        # Получает пару объектов классов, описанных в модуле discord. Guild - сервер,
        #           member - участник сервера, отправивший реакцию
        guild = discord.utils.get(bot.guilds, id=payload.guild_id)
        member = guild.get_member(payload.user_id)
        # Если реакция является одним из смайликов ролей, то
        if payload.emoji.name in emojitorole.keys():
            # Получает объект класса role, описанного в discord, по названию роли
            # emojitorole - конвертер из названия эмодзи в название роли, описан в credentials
            role = discord.utils.get(guild.roles, name=emojitorole[payload.emoji.name])
            print(str(guild) + ' / ' + str(member) + ' / ' + str(role))
            # Добавляет нужную роль нужному пользователю
            await member.add_roles(role)
        # Иначе
        else:
            # Получает пару объектов классов, описанных в модуле discord. Channel - канал,
            #           message - сообщение в этом канале, на котором висят реакции
            channel = discord.utils.get(guild.channels, id=payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            print(str(guild) + ' / ' + str(member) + ' / ' + str(payload.emoji.name))
            # Удаляет ненужную реакцию
            await message.remove_reaction(payload.emoji, member)


@bot.event
async def on_raw_reaction_remove(payload):
    # Если реакция под нужным нам сообщением(message_id и channel_id описаны в credentials), то
    if payload.message_id == int(discord_message_id) and payload.channel_id == int(discord_channel_id):
        print('Removed ' + str(payload.emoji.name))
        # Получает пару объектов классов, описанных в модуле discord. Guild - сервер,
        #           member - участник сервера, отправивший реакцию
        guild = discord.utils.get(bot.guilds, id=payload.guild_id)
        member = guild.get_member(payload.user_id)
        # Если реакция является одним из смайликов ролей, то
        if payload.emoji.name in emojitorole.keys():
            # Получает объект класса role, описанного в discord, по названию роли
            # emojitorole - конвертер из названия эмодзи в название роли, описан в credentials
            role = discord.utils.get(guild.roles, name=emojitorole[payload.emoji.name])
            print(str(guild) + ' / ' + str(member) + ' / ' + str(role))
            # Удаляет соответствующую роль у соответствующего пользователя
            await member.remove_roles(role)
        # Иначе просто игнорирует удаление ненужной реакции
        else:
            pass


@bot.command(name='update', pass_context=True, hidden=True)
async def update(ctx):
    try:
        if ctx.author.id == discord_pers_id:
            async with ctx.channel.typing():
                check()
                await ctx.send('Обновил роли!')
    except Exception as e:
        await ctx.send('Ошибка: \n {}'.format(e))


@bot.command(name='help', pass_context=True, help='Команда для вывода этого сообщения', usage='{}help [команда]')
async def help_(ctx, request=None):
    commandlist = {}
    try:
        pref = await get_prefix(bot, ctx.message)
        if request is None:
            embed = discord.Embed(title='Команды')
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
                embed.add_field(name=cog, value=commandlist[cog])
            embed.set_footer(text=f'Более подробно: {pref}help <команда>')
            return await ctx.send(embed=embed)
        for command in bot.commands:
            if ((command.name == request.lower()) or (request.lower() in command.aliases)) and not command.hidden:
                if command.aliases:
                    embed = discord.Embed(title='[{}|{}]'.format(command.name, '|'.join(command.aliases)))
                else:
                    embed = discord.Embed(title=command.name)
                embed.add_field(name='Описание', value=command.help)
                embed.add_field(name='Использование', value=command.usage.format(pref))
                return await ctx.send(embed=embed)
        return await ctx.send('Нет команды {}'.format(request))
    except Exception as e:
        await ctx.send('Ошибка: \n {}'.format(e))


if dev:
    bot.run(discord_alpha_token)
else:
    bot.run(discord_bot_token)
