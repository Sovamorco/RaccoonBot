import requests
from credentials import discord_message_id, discord_channel_id, discord_guild_id, discord_bot_token, emojitorole
import json

base = 'https://discordapp.com/api/v6'
headers = {'Authorization': 'Bot '+discord_bot_token}


def get_role(guild, samplerole):
    r = requests.get(base+'/guilds/'+guild+'/roles', headers=headers)
    roles = json.loads(r.text)
    for role in roles:
        if role['name'] == samplerole:
            return role


def get_members(guild_id):
    r = requests.get(base+'/guilds/'+guild_id+'/members?limit=100', headers=headers)
    members = json.loads(r.text)
    return members


def remove_role(guild_id, user_id, role_id):
    r = requests.delete(base+'/guilds/'+guild_id+'/members/'+user_id+'/roles/'+role_id, headers=headers)
    if r.status_code == 204:
        print('Роль успешно удалена')
    else:
        print(r.text)


def add_role(guild_id, user_id, role_id):
    r = requests.put(base+'/guilds/'+guild_id+'/members/'+user_id+'/roles/'+role_id, headers=headers)
    if r.status_code == 204:
        print('Роль успешно добавлена')
    else:
        print(r.text)


def delete_reaction(channel_id, message_id, emoji, user_id):
    r = requests.delete(base + '/channels/' + channel_id + '/messages/' + message_id + '/reactions/' + emoji + '/' + user_id,
                        headers=headers)
    if r.status_code == 204:
        print('Реакция удалена')
    else:
        print(r.text)


def check():
    try:
        r = requests.get(base + '/channels/' + discord_channel_id + '/messages/' + discord_message_id, headers=headers)
        reactions = json.loads(r.text)['reactions']
        members = get_members(discord_guild_id)
        for l in reactions:
            emoji = l['emoji']
            if emoji['id'] is None:
                emoji_id = emoji['name']
            else:
                emoji_id = '<:'+emoji['name']+':'+emoji['id']
            r = requests.get(base + '/channels/' + discord_channel_id + '/messages/' + discord_message_id + '/reactions/' + emoji_id,
                             headers=headers)
            users = json.loads(r.text)
            if emoji['name'] in emojitorole.keys():
                role = get_role(discord_guild_id, emojitorole[emoji['name']])['id']
                for member in members:
                    if 'bot' not in member['user'].keys():
                        if member['user'] not in users:
                            if role in member['roles']:
                                print(member['user']['username'])
                                remove_role(discord_guild_id, member['user']['id'], role)
                        else:
                            if role not in member['roles']:
                                print(member['user']['username'])
                                add_role(discord_guild_id, member['user']['id'], role)
            else:
                for user in users:
                    delete_reaction(discord_channel_id, discord_message_id, emoji_id, user['id'])
    except Exception as e:
        print('Ignored exception in check(): '+str(e))

# TODO: Переписать полностью эту часть с использованием discord.py
