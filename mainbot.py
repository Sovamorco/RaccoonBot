import discord
from discord.ext import commands

from random import shuffle
import time
import asyncio
import os
from tts import *
from check import *
from music import *

bot = commands.Bot(command_prefix=commands.when_mentioned_or('?'), description='Test bot')
bot.remove_command('help')

queue = []
current = {}
queue_exists = False
queue_msg = ''


@bot.event
async def on_ready():
    # Смена состояния(просто ради красоты)
    activity = discord.Streaming(name='Я живой OwO', url='https://twitch.tv/mrdandycorn')
    await bot.change_presence(activity=activity)
    # Проверка обновлений на сообщении, в случае, если что-то изменилось, пока бот был оффлайн
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


@bot.command(name='update', hidden=True)
async def update(message):
    async with message.channel.typing():
        check()
        await message.channel.send('Обновил роли!')


@bot.command(name='tts', pass_context=True, help='Команда для преобразования текста в голос', usage='?tts <текст>',
             brief='Синтез голоса')
async def tts_(context, *, text):
    global queue
    user = context.message.author
    text_channel = context.message.channel
    voice_channel = user.voice.channel
    if not text:
        return await text_channel.send('Использование: ?tts <сообщение>')
    ts = time.time()
    name = 'output{}.mp3'.format(ts)
    create_mp3(text, name)
    if len(text) < 16:
        title = text
    else:
        title = '{}...'.format(text[:15])
    if voice_channel is not None:
        queue.append({
            'name': name,
            'player': discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(name), 5),
            'title': title
        })
        return await play(context, ignore=True)
    else:
        await text_channel.send('Пользователь не подключен к каналу')


@bot.command(name='why', pass_context=True, help='Зачем', brief='Зачем', usage='?why <кол-во повторений>')
async def why_(context, amt):
    global queue
    user = context.message.author
    text_channel = context.message.channel
    voice_channel = user.voice.channel
    if not amt.isdigit():
        return await text_channel.send('Использование: ?why <кол-во раз>')
    if int(amt) > 20:
        return await text_channel.send('Нет')
    if voice_channel is not None:
        for i in range(int(amt)):
            queue.append({
                'name': '',
                'player': discord.PCMVolumeTransformer(discord.FFmpegPCMAudio('why.mp3'), 5),
                'title': 'Why'
            })
        return await play(context, ignore=True)
    else:
        await text_channel.send('Пользователь не подключен к каналу')


# @bot.command(name='preload', pass_context=True)
# async def preload_(context, *, text):
#     global queue
#     user = context.message.author
#     text_channel = context.message.channel
#     voice_channel = user.voice.channel
#     if voice_channel is not None:
#         if not text:
#             return await play(context)
#         if ('youtube.com' in text) or ('youtu.be' in text):
#             searchresult = searchyt(text)[0]
#             videoID = searchresult['id']
#             name = '{}.mp3'.format(videoID)
#             title = searchresult['title']
#             queue.append({
#                 'name': name,
#                 'player': discord.FFmpegPCMAudio(name),
#                 'title': title
#             })
#             return await play(context, ignore=True)
#         else:
#             searchresults = searchyt(text)
#             embed = discord.Embed(title="Choose song")
#             embedValue = ''
#             for i in range(len(searchresults)):
#                 title = searchresults[i]['title']
#                 embedValue += '{}: {}\n'.format(i + 1, title)
#             embed.add_field(name='Search results', value=embedValue, inline=False)
#             await text_channel.send(embed=embed)
#
#             def check(m):
#                 if m.content.isdigit():
#                     return (0 < int(m.content) < 11) and (m.channel == text_channel)
#                 return False
#
#             msg = await bot.wait_for('message', check=check, timeout=60)
#             videoID = searchresults[int(msg.content) - 1]['id']
#             name = '{}.mp3'.format(videoID)
#             title = searchresults[int(msg.content) - 1]['title']
#             queue.append({
#                 'name': name,
#                 'player': discord.FFmpegPCMAudio(name),
#                 'title': title
#             })
#             return await play(context, ignore=True)
#         download_video(url)
#         try:
#             vc = await voice_channel.connect()
#             queue.append({
#                 'name': name,
#                 'player': discord.FFmpegPCMAudio(name),
#                 'title': title
#             })
#             await text_channel.send('Added {} to the queue'.format(title))
#         except discord.errors.ClientException:
#             queue.append({
#                 'name': name,
#                 'player': discord.FFmpegPCMAudio(name),
#                 'title': title
#             })
#             await text_channel.send('Added {} to the queue'.format(title))
#             return
#         while queue:
#             name = queue[0].get('name')
#             sound = queue[0].get('player')
#             title = queue[0].get('title')
#             vc.play(sound)
#             await text_channel.send('Now playing: {}'.format(title))
#             while vc.is_playing():
#                 await asyncio.sleep(1)
#             if name:
#                 os.remove(name)
#             del queue[0]
#         vc.stop()
#         await vc.disconnect()
#     else:
#         await text_channel.send('User is not in a channel.')


async def play(context, ignore=False):
    global queue
    global current
    user = context.message.author
    text_channel = context.message.channel
    voice_channel = user.voice.channel
    beforeArgs = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    genericArgs = "-loglevel 'quiet'"
    if voice_channel is None:
        return await text_channel.send('Пользователь не подключен к каналу')
    if not queue:
        return await text_channel.send('Нет песен в очереди')
    try:
        vc = await voice_channel.connect()
    except discord.errors.ClientException:
        vc = context.voice_client
    if vc.is_playing():
        if not ignore:
            return await text_channel.send('Использование ?play <запрос/ссылка>')
    while queue:
        current = queue.pop(0)
        name = current.get('name')
        sound = current.get('player')
        title = current.get('title')
        if sound.__class__ == str:
            streamUrl = await get_stream_url(sound)
            sound = discord.FFmpegPCMAudio(streamUrl, before_options=beforeArgs, options=genericArgs)
        vc.play(sound)
        await text_channel.send('Сейчас играет: {}'.format(title))
        while vc.is_playing():
            await asyncio.sleep(1)
        if name:
            os.remove(name)
        current = {}
    if queue_exists:
        await queue_msg.delete()
    vc.stop()


@bot.command(name='stream', aliases=['play'], pass_context=True, brief='Добавить трек',
             help='Команда для добавления трека в очередь и/или начала проигрывания очереди',
             usage='?[stream|play] [ссылка/название]')
async def stream_(context, *, text=''):
    global queue
    user = context.message.author
    text_channel = context.message.channel
    voice_channel = user.voice.channel
    if voice_channel is not None:
        if not text:
            return await play(context)
        if 'youtube.com/playlist' in text:
            searchresults = searchplaylist(text)
            for video in searchresults:
                queue.append({
                    'name': '',
                    'player': video['url'],
                    'title': video['title']
                })
            await text_channel.send('Добавил в очередь {} песен'.format(len(searchresults)))
            return await play(context, ignore=True)
        if ('youtube.com' in text) or ('youtu.be' in text):
            searchresult = searchyt(text)[0]
            queue.append({
                'name': '',
                'player': searchresult['url'],
                'title': searchresult['title']
            })
            await text_channel.send('Добавил в очередь: {}'.format(searchresult['title']))
            return await play(context, ignore=True)
        else:
            searchresults = searchyt(text)
            embedValue = ''
            for i in range(len(searchresults)):
                title = searchresults[i]['title']
                embedValue += '{}: {}\n'.format(i + 1, title)
            embed = discord.Embed(title="Выберите песню", description=embedValue)
            embed.set_footer(text='Автоматическая отмена через 30 секунд')
            await text_channel.send(embed=embed, delete_after=30)

            def verify(m):
                if m.content.isdigit():
                    return (0 < int(m.content) < 11) and (m.channel == text_channel) and (m.author == user)
                return False

            try:
                msg = await bot.wait_for('message', check=verify, timeout=30)
                searchresult = searchresults[int(msg.content) - 1]
                queue.append({
                    'name': '',
                    'player': searchresult['url'],
                    'title': searchresult['title']
                })
                await text_channel.send('Добавил в очередь: {}'.format(searchresult['title']))
                return await play(context, ignore=True)
            except Exception as e:
                return e
    else:
        await text_channel.send('Пользователь не подключен к каналу')


@bot.command(name='leave', pass_context=True, help='Команда для выхода из голосового канала', brief='Покинуть',
             usage='?leave')
async def leave_(context):
    vc = context.voice_client
    text_channel = context.message.channel
    if vc is None:
        return await text_channel.send('Я не подключен к каналу')
    await vc.disconnect()
    return await text_channel.send('Отключен от канала')


@bot.command(name='join', aliases=['connect'], pass_context=True, help='Команда для подключения к голосовому каналу',
             brief='Подключиться', usage='?[join|connect]')
async def join_(context):
    user = context.message.author
    text_channel = context.message.channel
    voice_channel = user.voice.channel
    vc = context.voice_client
    if voice_channel is None:
        return await text_channel.send('Пользователь не подключен к каналу')
    if vc is None:
        await voice_channel.connect()
        return await text_channel.send('Подключен к каналу {}'.format(voice_channel))
    if vc.channel == voice_channel:
        return await text_channel.send('Уже подключен')
    await vc.move_to(voice_channel)
    return await text_channel.send('Подключен к каналу {}'.format(voice_channel))


@bot.command(name='np', aliases=['current', 'nowplaying'], pass_context=True, brief='Текущий трек',
             help='Команда для показа текущей плеера', usage='?[np|current|nowplaying]')
async def np_(context):
    global current
    vc = context.voice_client
    text_channel = context.message.channel
    if vc is None:
        return await text_channel.send('Я не подключен к каналу')
    if not current:
        return await text_channel.send('Сейчас ничего не играет')
    return await text_channel.send('Сейчас играет: {}'.format(current['title']))


@bot.command(name='queue', aliases=['q', 'playlist'], pass_context=True, brief='Очередь',
             help='Команда для показа очереди плеера', usage='?[queue|q|playlist]')
async def queue_(context):
    global queue
    global queue_msg
    global queue_exists
    local_queue = queue
    vc = context.voice_client
    text_channel = context.message.channel
    if vc is None:
        return await text_channel.send('Я не подключен к каналу')
    if not local_queue:
        return await text_channel.send('Очередь пустая')
    embedValue = ''
    length = 10
    if len(local_queue) < 10:
        length = len(local_queue)
    for i in range(length):
        embedValue += '{}: {}\n'.format(i + 1, local_queue[i]['title'])
    embed = discord.Embed(title="Очередь", description=embedValue)
    msg = await text_channel.send(embed=embed)
    if queue_exists:
        await queue_msg.delete()
    queue_exists = True
    queue_msg = msg
    if len(local_queue) > 10:
        page_num = 0

        def verify(reaction, user):
            return (reaction.message.id == msg.id) and (user != bot.user)

        await msg.add_reaction('▶')
        await msg.add_reaction('⏭')
        while True:
            reaction, user = await bot.wait_for('reaction_add', check=verify)
            if str(reaction.emoji) == '▶':
                page_num += 1
                length = 10
                if (len(local_queue)-10*page_num) < 10:
                    length = (len(local_queue)-10*page_num)
                embedValue = ''
                for i in range(page_num*10, page_num*10+length):
                    embedValue += '{}: {}\n'.format(i + 1, local_queue[i]['title'])
                embed = discord.Embed(title="Очередь", description=embedValue)
                await msg.edit(embed=embed)
                await msg.clear_reactions()
                await msg.add_reaction('⏮')
                await msg.add_reaction('◀')
                if page_num != (len(local_queue)//10):
                    await msg.add_reaction('▶')
                    await msg.add_reaction('⏭')
            elif str(reaction.emoji) == '⏭':
                page_num = len(local_queue) // 10
                embedValue = ''
                for i in range(page_num * 10, len(queue)):
                    embedValue += '{}: {}\n'.format(i + 1, local_queue[i]['title'])
                embed = discord.Embed(title="Очередь", description=embedValue)
                await msg.edit(embed=embed)
                await msg.clear_reactions()
                await msg.add_reaction('⏮')
                await msg.add_reaction('◀')
            elif str(reaction.emoji) == '◀':
                page_num -= 1
                length = 10
                embedValue = ''
                for i in range(page_num * 10, page_num * 10 + length):
                    embedValue += '{}: {}\n'.format(i + 1, local_queue[i]['title'])
                embed = discord.Embed(title="Очередь", description=embedValue)
                await msg.edit(embed=embed)
                await msg.clear_reactions()
                if page_num != 0:
                    await msg.add_reaction('⏮')
                    await msg.add_reaction('◀')
                await msg.add_reaction('▶')
                await msg.add_reaction('⏭')
            elif str(reaction.emoji) == '⏮':
                page_num = 0
                embedValue = ''
                for i in range(0, 10):
                    embedValue += '{}: {}\n'.format(i + 1, local_queue[i]['title'])
                embed = discord.Embed(title="Очередь", description=embedValue)
                await msg.edit(embed=embed)
                await msg.clear_reactions()
                await msg.add_reaction('▶')
                await msg.add_reaction('⏭')
            else:
                await reaction.remove(user)


@bot.command(name='shuffle', pass_context=True, help='Команда для перемешивания очереди плеера',
             brief='Перемешать', usage='?shuffle')
async def shuffle_(context):
    global queue
    vc = context.voice_client
    text_channel = context.message.channel
    if vc is None:
        return await text_channel.send('Я не подключен к каналу')
    if not queue:
        return await text_channel.send('Очередь пустая')
    shuffle(queue)
    return await text_channel.send('Очередь перемешана')


@bot.command(name='stop', pass_context=True, help='Команда для остановки плеера и очистки очереди',
             brief='Остановка плеера', usage='?stop')
async def stop_(context):
    global queue_exists
    global current
    vc = context.voice_client
    text_channel = context.message.channel
    if vc is None:
        return await text_channel.send('Я не подключен к каналу')
    if not current:
        return await text_channel.send('Сейчас ничего не играет')
    if vc.is_playing():
        queue.clear()
        if queue_exists:
            queue_exists = False
            await queue_msg.delete()
        vc.stop()
        await vc.disconnect()


@bot.command(name='skip', pass_context=True, help='Команда для пропуска текущего трека',
             brief='Пропуск трека', usage='?skip')
async def skip_(context):
    global current
    vc = context.voice_client
    text_channel = context.message.channel
    if vc is None:
        return await text_channel.send('Я не подключен к каналу')
    if not current:
        return await text_channel.send('Сейчас ничего не играет')
    if vc.is_playing():
        vc.stop()
        return await text_channel.send('{} пропущена')


@bot.command(name='help', pass_context=True, help='Команда для показа этого сообщения',
             brief='Помощь', usage='?help [команда]')
async def help_(context, request=None):
    text_channel = context.message.channel
    if request is None:
        embed = discord.Embed(title='Команды')
        for command in bot.commands:
            if not command.hidden:
                if command.aliases:
                    embed.add_field(name='[{}|{}]'.format(command.name, '|'.join(command.aliases)), value=command.brief)
                else:
                    embed.add_field(name=command.name, value=command.brief)
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


bot.run(discord_bot_token)
