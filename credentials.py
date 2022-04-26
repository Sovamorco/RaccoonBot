from pathlib import Path

from hvac import Client

_client = Client(url='https://vault.sovamor.co')
_creds = Path('/run/secrets/raccoonbot_vault').read_text().strip().split(':', 1)
_client.auth.userpass.login(
    username=_creds[0],
    password=_creds[1],
)


def get_secret(key):
    read_response = _client.secrets.kv.v2.read_secret_version(path=key)
    data = read_response['data']['data']
    if len(data) == 1 and list(data.keys())[0] == 'value':
        data = data['value']
    return data


_secrets = [
    'osu_key',
    'vk_personal_audio_token',
    'spotify_client_id',
    'spotify_client_secret',
    'discord_status',
    'discord_bot_token',
    'discord_alpha_token',
    'genius_token',
    'discord_pers_id',
    'main_password',
    'main_web_addr',
    'gachi_things',
    'genius_token',
]

secrets = {}
for item in _secrets:
    secrets[item] = get_secret(item)
