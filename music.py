import math
import re
import random
import json

from tts import *
from time import time
import discord
import lavalink
from discord.ext import commands
from credentials import main_password, main_nickname, main_web_addr,gachi_things

url_rx = re.compile('https?://(?:www\\.)?.+')


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node('127.0.0.1', 2333, main_password, 'ru', 'default-node')
            bot.add_listener(bot.lavalink.voice_update_handler, 'on_socket_response')

    def cog_unload(self):
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        guild_check = ctx.guild is not None

        if guild_check:
            await self.ensure_voice(ctx)

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)

    async def connect_to(self, guild_id: int, channel_id):
        ws = self.bot._connection._get_websocket(guild_id)
        await ws.voice_state(str(guild_id), channel_id)

    @commands.command(aliases=['p'], usage='?[p|play] <ссылка/название>', help='Команда для проигрывания музыки')
    async def play(self, ctx, *, query: str):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        query = query.strip('<>')
        if not url_rx.match(query):
            query = f'ytsearch:{query}'
        results = await player.node.get_tracks(query)
        if not results or not results['tracks']:
            return await ctx.send('Ничего не найдено')
        embed = discord.Embed(color=discord.Color.blurple())
        if results['loadType'] == 'PLAYLIST_LOADED':
            tracks = results['tracks']
            for track in tracks:
                player.add(requester=ctx.author.id, track=track)
            embed.title = 'Плейлист добавлен'
            embed.description = f'{results["playlistInfo"]["name"]} - {len(tracks)}'
        else:
            if url_rx.match(query):
                track = results['tracks'][0]
            else:
                text_channel = ctx.message.channel
                user = ctx.message.author
                tracks = results['tracks']
                embedValue = ''
                length = 10 if len(tracks) > 10 else len(tracks)
                for i in range(length):
                    title = tracks[i]['info']['title']
                    embedValue += '{}: {}\n'.format(i + 1, title)
                choiceEmbed = discord.Embed(title="Выберите песню", description=embedValue,
                                            color=discord.Color.blurple())
                choiceEmbed.set_footer(text='Автоматическая отмена через 30 секунд\nОтправьте 0 для отмены')
                choice = await ctx.send(embed=choiceEmbed, delete_after=30)

                def verify(m):
                    if m.content.isdigit():
                        return (0 <= int(m.content) < 11) and (m.channel == text_channel) and (m.author == user)
                    return False

                msg = await self.bot.wait_for('message', check=verify, timeout=30)
                if int(msg.content) == 0:
                    return await choice.delete()
                track = tracks[int(msg.content) - 1]
                await choice.delete()
            embed.title = 'Трек добавлен'
            embed.description = f'[{track["info"]["title"]}]({track["info"]["uri"]})'
            player.add(requester=ctx.author.id, track=track)
        await ctx.send(embed=embed)
        if not player.is_playing:
            await player.play()

    @commands.command(usage='?[gachi|gachibass]', help='Команда для проигрывания правильных версий музыки',
                      aliases=['gachi'])
    async def gachibass(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        with open('resources/gachi.txt', 'r') as f:
            tracks = json.load(f)
        track = random.choice(tracks)
        player.add(requester=ctx.author.id, track=track)
        await ctx.send(random.choice(gachi_things))
        if not player.is_playing:
            await player.play()

    @commands.command(help='Зачем', usage='?why <кол-во повторений> (Не используйте, пожалуйста)')
    async def why(self, ctx, amt: int = 1):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if (int(amt) > 20) and (ctx.author.name != main_nickname):
            return await ctx.send('Нет')
        query = 'why.mp3'
        results = await player.node.get_tracks(query)
        track = results['tracks'][0]
        for i in range(int(amt)):
            player.add(requester=ctx.author.id, track=track)
        if not player.is_playing:
            await player.play()

    @commands.command(help='Команда для преобразования текста в голос', usage='?tts <текст>')
    async def tts(self, ctx, *, text):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not text:
            return await ctx.send('Использование: ?tts <сообщение>')
        ts = time()
        name = 'output{}.mp3'.format(ts)
        await create_mp3(text, name)
        query = 'outputs/'+name
        results = await player.node.get_tracks(query)
        track = results['tracks'][0]
        player.add(requester=ctx.author.id, track=track)
        if not player.is_playing:
            await player.play()

    @commands.command(help='Команда для перемотки музыки', usage='?seek <время в секундах>')
    async def seek(self, ctx, *, seconds: int):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        track_time = player.position + (seconds * 1000)
        await player.seek(track_time)

        await ctx.send(f'Переместился на **{lavalink.utils.format_time(track_time)}**')

    @commands.command(help='Команда для пропуска трека', usage='?skip')
    async def skip(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Ничего не играет')

        await player.skip()
        await ctx.send('⏭ | Трек пропущен')

    @commands.command(help='Команда для остановки плеера и очистки очереди', usage='?stop')
    async def stop(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Ничего не играет')

        player.queue.clear()
        await player.stop()
        await self.connect_to(ctx.guild.id, None)
        await ctx.send('⏹ | Плеер остановлен')

    @commands.command(help='Команда для очистки очереди плеера', usage='?clear')
    async def clear(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.queue:
            return await ctx.send('Очередь пустая')

        player.queue.clear()
        await ctx.send('⭕ | Очередь очищена')

    @commands.command(aliases=['n', 'np', 'playing', 'current'], usage='?[np|now|playing|current]',
                      help='Команда для отображения текущего трека')
    async def now(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.current:
            return await ctx.send('Ничего не играет')
        position = lavalink.utils.format_time(player.position)
        if player.current.stream:
            duration = '🔴 LIVE'
        else:
            duration = lavalink.utils.format_time(player.current.duration)
        song = f'**[{player.current.title}]({player.current.uri})**\n({position}/{duration})'

        embed = discord.Embed(color=discord.Color.blurple(),
                              title='Сейчас играет', description=song)
        await ctx.send(embed=embed)

    @commands.command(aliases=['q'], help='Команда для отображения очереди воспроизведения',
                      usage='?[q|queue]')
    async def queue(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        items_per_page = 10
        local_queue = player.queue.copy()
        pages = math.ceil(len(player.queue) / items_per_page)
        queue_list = ''
        for index, track in enumerate(local_queue[0:10], start=0):
            queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
        embed = discord.Embed(colour=discord.Color.blurple(),
                              description=f'**{len(player.queue)} tracks**\n\n{queue_list}')
        msg = await ctx.send(embed=embed)
        if pages > 1:
            def verify(react, member):
                return (react.message.id == msg.id) and (member != self.bot.user)

            page = 1
            await msg.add_reaction('▶')
            await msg.add_reaction('⏭')
            await msg.add_reaction('❌')
            while True:
                reaction, user = await self.bot.wait_for('reaction_add', check=verify)
                if str(reaction.emoji) == '▶':
                    page += 1
                    start = (page - 1) * items_per_page
                    end = start + items_per_page
                    queue_list = ''
                    for index, track in enumerate(local_queue[start:end], start=start):
                        queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                    embed = discord.Embed(colour=discord.Color.blurple(),
                                          description=f'**{len(player.queue)} tracks**\n\n{queue_list}')
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()
                    await msg.add_reaction('⏮')
                    await msg.add_reaction('◀')
                    if page != pages:
                        await msg.add_reaction('▶')
                        await msg.add_reaction('⏭')
                    await msg.add_reaction('❌')
                elif str(reaction.emoji) == '⏭':
                    page = pages
                    start = (page - 1) * items_per_page
                    end = start + items_per_page
                    queue_list = ''
                    for index, track in enumerate(local_queue[start:end], start=start):
                        queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                    embed = discord.Embed(colour=discord.Color.blurple(),
                                          description=f'**{len(player.queue)} tracks**\n\n{queue_list}')
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()
                    await msg.add_reaction('⏮')
                    await msg.add_reaction('◀')
                    await msg.add_reaction('❌')
                elif str(reaction.emoji) == '◀':
                    page -= 1
                    start = (page - 1) * items_per_page
                    end = start + items_per_page
                    queue_list = ''
                    for index, track in enumerate(local_queue[start:end], start=start):
                        queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                    embed = discord.Embed(colour=discord.Color.blurple(),
                                          description=f'**{len(player.queue)} tracks**\n\n{queue_list}')
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()
                    if page != 1:
                        await msg.add_reaction('⏮')
                        await msg.add_reaction('◀')
                    await msg.add_reaction('▶')
                    await msg.add_reaction('⏭')
                    await msg.add_reaction('❌')
                elif str(reaction.emoji) == '⏮':
                    page = 1
                    start = (page - 1) * items_per_page
                    end = start + items_per_page
                    queue_list = ''
                    for index, track in enumerate(local_queue[start:end], start=start):
                        queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'
                    embed = discord.Embed(colour=discord.Color.blurple(),
                                          description=f'**{len(player.queue)} tracks**\n\n{queue_list}')
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()
                    await msg.add_reaction('▶')
                    await msg.add_reaction('⏭')
                    await msg.add_reaction('❌')
                elif str(reaction.emoji) == '❌':
                    return await msg.delete()
                else:
                    await reaction.remove(user)

    @commands.command(aliases=['resume'], usage='?[pause|resume]',
                      help='Команда для приостановки или продолжения поспроизведения воспроизведения')
    async def pause(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        if player.paused:
            await player.set_pause(False)
            await ctx.send('⏯ | Воспроизведение возобновлено')
        else:
            await player.set_pause(True)
            await ctx.send('⏯ | Воспроизведение приостановлено')

    @commands.command(aliases=['vol'], help='Команда для изменения громкости плеера',
                      usage='?[vol|volume] <громкость(1-1000)>')
    async def volume(self, ctx, volume: int = None):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not volume:
            return await ctx.send(f'🔈 | {player.volume}%')
        await player.set_volume(volume)
        await ctx.send(f'🔈 | Звук установлен на {player.volume}%')

    @commands.command(help='Команда для включения/выключения перемешивания очереди', usage='?shuffle')
    async def shuffle(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        player.shuffle = not player.shuffle
        await ctx.send('🔀 | Перемешивание ' + ('включено' if player.shuffle else 'выключено'))

    @commands.command(aliases=['loop'], usage='?[loop/repeat]',
                      help='Команда для включения/выключения зацикливания очереди')
    async def repeat(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send('Ничего не играет')
        player.repeat = not player.repeat
        await ctx.send('🔁 | Циклическое воспроизведение ' + ('включено' if player.repeat else 'выключено'))

    @commands.command(help='Команда для удаления трека из очереди', usage='?remove <индекс>')
    async def remove(self, ctx, index: int):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.queue:
            return await ctx.send('Очередь пустая')
        if index > len(player.queue) or index < 1:
            return await ctx.send(f'Индекс дожен быть **между** 1 и {len(player.queue)}')
        removed = player.queue.pop(index - 1)
        await ctx.send(f'**{removed.title}** удален из очереди')

    @commands.command(aliases=['dc', 'leave'], help='Команда для отключения бота от голосового канала',
                      usage='?[dc|disconnect|leave]')
    async def disconnect(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.is_connected:
            return await ctx.send('Не подключен к голосовому каналу')
        player.queue.clear()
        await player.stop()
        await self.connect_to(ctx.guild.id, None)
        await ctx.send('*⃣ | Отключен')

    @commands.command(aliases=['connect', 'c'], usage='?[c|connect|join]',
                      help='Команда для подключения бота к голосовому каналу')
    async def join(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not ctx.author.voice:
            return await ctx.send('Пользователь не подключен к каналу')
        if player.channel_id:
            if ctx.author.voice.channel.id == int(player.channel_id):
                return await ctx.send('Уже подключен к голосовому каналу')
        await self.connect_to(ctx.guild.id, ctx.author.voice.channel.id)
        await ctx.send('*⃣ | Подключен к {}'.format(ctx.author.voice.channel))

    async def ensure_voice(self, ctx):
        player = self.bot.lavalink.players.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        should_connect = ctx.command.name in ('play', 'join', 'why', 'tts', 'join', 'gachibass')
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandInvokeError('Сначала подключитесь к голосовому каналу')
        if not player.is_connected:
            if not should_connect:
                raise commands.CommandInvokeError('Я не подключен к каналу')
            permissions = ctx.author.voice.channel.permissions_for(ctx.me)
            if not permissions.connect or not permissions.speak:
                raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions.')
            player.store('channel', ctx.channel.id)
            await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
        else:
            if int(player.channel_id) == ctx.author.voice.channel.id and should_connect:
                return
            if should_connect:
                return await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError('Мы в разных голосовых каналах')


def music_setup(bot):
    bot.add_cog(Music(bot))
