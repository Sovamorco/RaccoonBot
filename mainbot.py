import discord
from discord.ext import commands

import time
import asyncio
import os
from tts import *
from check import *
from music import *

bot = commands.Bot(command_prefix=commands.when_mentioned_or('?'), description='Test bot')

queue = []


@bot.event
async def on_ready():
    # Смена состояния(просто ради красоты)
    activity = discord.Streaming(name='Я живой OwO', url='https://twitch.tv/mrdandycorn')
    await bot.change_presence(activity=activity)
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


@bot.command(name='update')
async def update(message):
    async with message.channel.typing():
        check()
        await message.channel.send('Updated roles!')


@bot.command(name='tts', pass_context=True)
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
    if voice_channel is not None:
        try:
            vc = await voice_channel.connect()
            queue.append((name, discord.FFmpegPCMAudio(name)))
        except discord.errors.ClientException:
            queue.append((name, discord.FFmpegPCMAudio(name)))
            return
        while queue:
            name, sound = queue[0]
            vc.play(sound)
            while vc.is_playing():
                await asyncio.sleep(1)
            if name:
                os.remove(name)
            del queue[0]
        vc.stop()
        await vc.disconnect()
    else:
        await text_channel.send('User is not in a channel.')


@bot.command(name='why', pass_context=True)
async def tts_(context, amt):
    global queue
    user = context.message.author
    text_channel = context.message.channel
    voice_channel = user.voice.channel
    if not amt.isdigit():
        return await text_channel.send('Использование: ?why <кол-во раз>')
    if int(amt) > 20:
        return await text_channel.send('Нет')
    if voice_channel is not None:
        try:
            vc = await voice_channel.connect()
            for i in range(int(amt)):
                queue.append(('', discord.FFmpegPCMAudio('why.mp3')))
        except discord.errors.ClientException:
            for i in range(int(amt)):
                queue.append(('', discord.FFmpegPCMAudio('why.mp3')))
            return
        while queue:
            name, sound = queue[0]
            vc.play(sound)
            while vc.is_playing():
                await asyncio.sleep(1)
            if name:
                os.remove(name)
            del queue[0]
        vc.stop()
        await vc.disconnect()
    else:
        await text_channel.send('User is not in a channel.')


@bot.command(name='music', pass_context=True)
async def music_(context, *, text):
    global queue
    user = context.message.author
    text_channel = context.message.channel
    voice_channel = user.voice.channel
    if not text:
        return await text_channel.send('Использование: ?music <запрос>')
    searchresults = searchyt(text)
    embed = discord.Embed(title="Choose song")
    embedValue = ''
    for i in range(len(searchresults)):
        title = searchresults[i]['title']
        embedValue += '{}: {}\n'.format(i+1, title)
    embed.add_field(name='Search results', value=embedValue, inline=False)
    await text_channel.send(embed=embed)

    def check(m):
        if m.content.isdigit():
            return (0 < int(m.content) < 11) and (m.channel == text_channel)
        return False

    msg = await bot.wait_for('message', check=check, timeout=60)
    videoID = searchresults[int(msg.content)-1]['id']
    url = searchresults[int(msg.content)-1]['url']
    name = '{}.mp3'.format(videoID)
    title = searchresults[int(msg.content)-1]['title']
    download_video(url)
    if voice_channel is not None:
        try:
            vc = await voice_channel.connect()
            queue.append({
                'name': name,
                'player': discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(name), 0.2),
                'title': title
            })
            await text_channel.send('Added {} to the queue'.format(title))
        except discord.errors.ClientException:
            queue.append({
                'name': name,
                'player': discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(name), 0.2),
                'title': title
            })
            await text_channel.send('Added {} to the queue'.format(title))
            return
        while queue:
            name = queue[0].get('name')
            sound = queue[0].get('player')
            title = queue[0].get('title')
            vc.play(sound)
            await text_channel.send('Now playing: {}'.format(title))
            while vc.is_playing():
                await asyncio.sleep(1)
            if name:
                os.remove(name)
            del queue[0]
        vc.stop()
        await vc.disconnect()
    else:
        await text_channel.send('User is not in a channel.')


@bot.command(name='leave', pass_context=True)
async def leave_(context):
    for vc in bot.voice_clients:
        await vc.disconnect()


bot.run(discord_bot_token)
