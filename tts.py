from google.cloud import texttospeech
from google.oauth2 import service_account
from google.cloud import translate_v3beta1 as translate

import io
from credentials import google_project_id

credentials = service_account.Credentials.from_service_account_file('service.json')
ttsClient = texttospeech.TextToSpeechClient(credentials=credentials)
translateClient = translate.TranslationServiceClient(credentials=credentials)


async def detect_language(text):
    location = 'global'
    parent = translateClient.location_path(google_project_id, location)
    response = translateClient.detect_language(parent=parent, content=text)
    lang_code = response.languages[0].language_code
    if lang_code == 'und':
        lang_code = 'ru'
    return lang_code


async def tts(text):
    lang_code = await detect_language(text)
    voice_name = get_voice(lang_code)
    if not voice_name:
        lang_code = 'ru'
        voice_name = get_voice(lang_code)
    synthesis_input = texttospeech.types.SynthesisInput(text=text)
    voice = texttospeech.types.VoiceSelectionParams(
        language_code=lang_code,
        name=voice_name)
    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)
    response = ttsClient.synthesize_speech(synthesis_input, voice, audio_config)
    return response.audio_content


def get_voice(lang_code):
    response = ttsClient.list_voices(language_code=lang_code)
    for voice in response.voices:
        if ('Wavenet' in voice.name) and (voice.ssml_gender == 2):
            return voice.name


async def create_mp3(text, name):
    mp3bytes = await tts(text)
    with io.open('lavalink/outputs/'+name, 'wb') as out:
        out.write(mp3bytes)
