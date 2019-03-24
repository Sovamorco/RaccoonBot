# Импорт единственной библиотеки 'discord' и двух модулей, которые идут с этой программой
import discord

import check
from credentials import *


# Клиент для обработки обновлений
class MyClient(discord.Client):
    # Когда бот подключается
    async def on_ready(self):
        # Смена состояния(просто ради красоты)
        activity = discord.Streaming(name='Я живой OwO', url='https://twitch.tv/mrdandycorn')
        await self.change_presence(activity=activity)
        # Проверка обновлений на сообщении, в случае, если что-то изменилось, пока бот был оффлайн
        check.check()
        print('Logged on as', self.user)

    async def on_message(self, message):
        # Сообщения от себя самого бот игнорирует
        if message.author == self.user:
            return

        # Если команда - '?update', то проверяет обновления на сообщении(на случай каких-то ошибок)
        if message.content == '?update':
            async with message.channel.typing():
                check.check()
                await message.channel.send('Updated roles!')

    # Когда появляется реакция(смайлик под сообщением), триггерит эту функцию
    async def on_raw_reaction_add(self, payload):
        # Если реакция под нужным нам сообщением(message_id и channel_id описаны в credentials), то
        if payload.message_id == int(message_id) and payload.channel_id == int(channel_id):
            print('Added ' + str(payload.emoji.name))
            # Получает пару объектов классов, описанных в модуле discord. Guild - сервер,
            #           member - участник сервера, отправивший реакцию
            guild = discord.utils.get(self.guilds, id=payload.guild_id)
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

    # Когда удаляется реакция(смайлик под сообщением), триггерит эту функцию
    async def on_raw_reaction_remove(self, payload):
        # Если реакция под нужным нам сообщением(message_id и channel_id описаны в credentials), то
        if payload.message_id == int(message_id) and payload.channel_id == int(channel_id):
            print('Removed ' + str(payload.emoji.name))
            # Получает пару объектов классов, описанных в модуле discord. Guild - сервер,
            #           member - участник сервера, отправивший реакцию
            guild = discord.utils.get(self.guilds, id=payload.guild_id)
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


# Создание клиента - объекта класса MyClient, описанного выше
client = MyClient()
# Запуск клиента с помощью токена
client.run(bottoken)
