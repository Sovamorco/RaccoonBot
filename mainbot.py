from check import *
from music import *
from misc import *

bot = commands.Bot(command_prefix=commands.when_mentioned_or('?'), description='Test bot')
bot.remove_command('help')

queue_exists = False
queue_msg = ''
volume = 0.1


@bot.event
async def on_ready():
    # Смена состояния(просто ради красоты)
    activity = discord.Streaming(name='Я живой OwO', url='https://twitch.tv/mrdandycorn',
                                 timestamps={'start': time()})
    await bot.change_presence(activity=activity)
    misc_setup(bot)
    music_setup(bot)
    # Проверка обновлений на сообщении, в случае, если что-то изменилось, пока бот был оффлайн
    # check()
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
async def update(context):
    text_channel = context.message.channel
    try:
        user = context.message.author
        if user.name == main_nickname:
            async with text_channel.typing():
                check()
                await text_channel.send('Обновил роли!')
    except Exception as e:
        await text_channel.send('Ошибка: \n {}'.format(e))


@bot.command(name='help', pass_context=True, help='Команда для показа этого сообщения', usage='?help [команда]')
async def help_(context, request=None):
    text_channel = context.message.channel
    commandlist = {}
    try:
        if request is None:
            embed = discord.Embed(title='Команды')
            for command in bot.commands:
                if not command.hidden:
                    if command.cog_name is not None:
                        cog = command.cog_name
                    else:
                        cog = 'Main'
                    if cog not in commandlist.keys():
                        commandlist[cog] = command.name
                    else:
                        commandlist[cog] += ', {}'.format(command.name)
            for cog in commandlist.keys():
                embed.add_field(name=cog, value=commandlist[cog])
            return await text_channel.send(embed=embed)
        for command in bot.commands:
            if ((command.name == request.lower()) or (request.lower() in command.aliases)) and not command.hidden:
                if command.aliases:
                    embed = discord.Embed(title='[{}|{}]'.format(command.name, '|'.join(command.aliases)))
                else:
                    embed = discord.Embed(title=command.name)
                embed.add_field(name='Описание', value=command.help)
                embed.add_field(name='Использование', value=command.usage)
                return await text_channel.send(embed=embed)
        return await text_channel.send('Нет команды {}'.format(request))
    except Exception as e:
        await text_channel.send('Ошибка: \n {}'.format(e))


bot.run(discord_bot_token)
