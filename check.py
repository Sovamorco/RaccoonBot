# Импорт нужных библиотек
import requests
from credentials import discord_message_id, discord_channel_id, discord_guild_id, discord_bot_token, emojitorole
import json

# Базовая ссылка на API дискорда
base = 'https://discordapp.com/api/v6'
# Авторизация бота в API
headers = {'Authorization': 'Bot '+discord_bot_token}


# Функция для получения роли по названию
def get_role(guild, samplerole):
    # Отправляет запрос для получения всех ролей на сервере, после чего парсит полученную информацию из строки в dict
    r = requests.get(base+'/guilds/'+guild+'/roles', headers=headers)
    roles = json.loads(r.text)
    # Сравнивает имя каждой роли с заданным и возвращает роль, если оно совпало
    for role in roles:
        if role['name'] == samplerole:
            return role


# Функция для получения всех пользователей сервера. Возвращает лист пользователей
def get_members(guild_id):
    # Получает список пользователей запросом и парсит его в лист, который и возвращает
    r = requests.get(base+'/guilds/'+guild_id+'/members?limit=100', headers=headers)
    print(r.text)
    members = json.loads(r.text)
    return members


# Функция для удаления роли у пользователя
def remove_role(guild_id, user_id, role_id):
    # Отправляет запрос на удаление роли. Выводит сообщение, если API возвращает код успешной операции, иначе выводит
    # текст ошибки, отправленный API
    r = requests.delete(base+'/guilds/'+guild_id+'/members/'+user_id+'/roles/'+role_id, headers=headers)
    if r.status_code == 204:
        print('Роль успешно удалена')
    else:
        print(r.text)


# Функция для добавления роли пользователю
def add_role(guild_id, user_id, role_id):
    # Отправляет запрос на добавление роли. Выводит сообщение, если API возвращает код успешной операции, иначе выводит
    # текст ошибки, отправленный API
    r = requests.put(base+'/guilds/'+guild_id+'/members/'+user_id+'/roles/'+role_id, headers=headers)
    if r.status_code == 204:
        print('Роль успешно добавлена')
    else:
        print(r.text)


# Функция для удаления реакции к сообщению
def delete_reaction(channel_id, message_id, emoji, user_id):
    # Отправляет запрос на удаление реакции. Выводит сообщение, если API возвращает код успешной операции, иначе выводит
    # текст ошибки, отправленный API
    r = requests.delete(base + '/channels/' + channel_id + '/messages/' + message_id + '/reactions/' + emoji + '/' + user_id,
                        headers=headers)
    if r.status_code == 204:
        print('Реакция удалена')
    else:
        print(r.text)


# Основная функция проверки обновлений
def check():
    try:
        # Получает список реакций к сообщению и парсит его в лист
        r = requests.get(base + '/channels/' + discord_channel_id + '/messages/' + discord_message_id, headers=headers)
        reactions = json.loads(r.text)['reactions']
        # Получает список пользователей сервера
        members = get_members(discord_guild_id)
        for l in reactions:
            # Для каждой реакции получает ее id
            emoji = l['emoji']
            print('Роль ' + emoji['name'])
            if emoji['id'] is None:
                emoji_id = emoji['name']
            else:
                emoji_id = '<:'+emoji['name']+':'+emoji['id']
            # Возвращает список пользователей, отреагировавших этой реакцией и парсит его в list
            r = requests.get(base + '/channels/' + discord_channel_id + '/messages/' + discord_message_id + '/reactions/' + emoji_id,
                             headers=headers)
            users = json.loads(r.text)
            # Если реакция является одним из смайликов ролей, то
            if emoji['name'] in emojitorole.keys():
                # Получает id нужной роли по имени из emojitorole, описанного в credentials
                role = get_role(discord_guild_id, emojitorole[emoji['name']])['id']
                # Для каждого пользователя сервера
                for member in members:
                    # Если это не бот, то
                    if 'bot' not in member['user'].keys():
                        # Если пользователь не оставил реакцию
                        if member['user'] not in users:
                            # И если у него есть соответствующая роль
                            if role in member['roles']:
                                # Удаляет ее
                                print(member['user']['username'])
                                remove_role(discord_guild_id, member['user']['id'], role)
                        # Иначе, если пользователь оставил реакцию
                        else:
                            # И при этом у него нет соответствующей роли
                            if role not in member['roles']:
                                # Добавляет ему эту роль
                                print(member['user']['username'])
                                add_role(discord_guild_id, member['user']['id'], role)
            # Иначе удаляет все ненужные реакции
            else:
                for user in users:
                    delete_reaction(discord_channel_id, discord_message_id, emoji_id, user['id'])
    # В случае ошибки игнорирует ее и выводит текст этой ошибки
    except Exception as e:
        print('Ignored exception in check(): '+str(e))
