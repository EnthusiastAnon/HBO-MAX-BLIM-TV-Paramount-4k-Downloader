import uuid, sys
import configparser

from shutil import which
from os.path import dirname, realpath, join
from os import pathsep, environ

def generate_device():
    return str(uuid.uuid4())
_uuid = generate_device() #traceid

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'
config = {}

config['la'] = {
    'tokens': 'https://gateway-latam.api.hbo.com/auth/tokens',
    'content': 'https://comet-latam.api.hbo.com/content',
    'license_wv': 'https://comet-latam.api.hbo.com/drm/license/widevine?keygen=playready&drmKeyVersion=2'
}

config['us'] = {
    'tokens': 'https://gateway.api.hbo.com/auth/tokens',
    'content': 'https://comet.api.hbo.com/content',
    'license_wv': 'https://comet.api.hbo.com/drm/license/widevine?keygen=playready&drmKeyVersion=2'
}

metadata_language = 'en-US'

UA = 'Mozilla/5.0 (Linux; Android 7.1.1; SHIELD Android TV Build/LMY47D) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/84.0.4147.135 Safari/537.36'

login_headers = {
    "accept": "application/vnd.hbo.v9.full+json",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": metadata_language,
    "user-agent": UA,
    "x-hbo-client-version": "Hadron/50.40.0.111 desktop (DESKTOP)",
    "x-hbo-device-name": "desktop",
    "x-hbo-device-os-version": "undefined",
}

login_json = {
    "client_id": '24fa5e36-3dc4-4ed0-b3f1-29909271b63d',
    "client_secret": '24fa5e36-3dc4-4ed0-b3f1-29909271b63d',
    "scope":"browse video_playback_free",
    "grant_type":"client_credentials",
    "deviceSerialNumber": 'b394a2da-b3a7-429d-8f70-5c4eae50a678',
    "clientDeviceData":{
        "paymentProviderCode":"apple"
    }
}

payload = {
    'x-hbo-device-model':user_agent,
    'x-hbo-video-features':'server-stitched-playlist,mlp',
    'x-hbo-session-id':_uuid,
    'x-hbo-video-player-version':'QUANTUM_BROWSER/50.30.0.249',
    'x-hbo-device-code-override':'ANDROIDTV',
    'x-hbo-video-mlp':True,
}

SCRIPT_PATH = dirname(realpath('hbomax'))

BINARIES_FOLDER = join(SCRIPT_PATH, 'binaries')
COOKIES_FOLDER = join(SCRIPT_PATH, 'cookies')

MP4DECRYPT_BINARY = 'mp4decrypt'
MEDIAINFO_BINARY = 'mediainfo'
MP4DUMP_BINARY = 'mp4dump'
MKVMERGE_BINARY = 'mkvmerge'
FFMPEG_BINARY = 'ffmpeg'
FFMPEG_BINARY = 'ffmpeg'
ARIA2C_BINARY = 'aria2c'
SUBTITLE_EDIT_BINARY = 'subtitleedit'

# Add binaries folder to PATH as the first item
environ['PATH'] = pathsep.join([BINARIES_FOLDER, environ['PATH']])

MP4DECRYPT = which(MP4DECRYPT_BINARY)
MEDIAINFO = which(MEDIAINFO_BINARY)
MP4DUMP = which(MP4DUMP_BINARY)
MKVMERGE = which(MKVMERGE_BINARY)
FFMPEG = which(FFMPEG_BINARY)
ARIA2C = which(ARIA2C_BINARY)
SUBTITLE_EDIT = which(SUBTITLE_EDIT_BINARY)

def get_token_info():
    return {'headers': login_headers, 'data': login_json}

def get_user_headers():
    headers = {
        'origin': 'https://play.hbomax.com',
        'referer': 'https://play.hbomax.com/',
        'x-b3-traceid': f'{_uuid}-{_uuid}',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'accept': 'application/vnd.hbo.v9.full+json',
        'content-type': 'application/json; charset=utf-8',
        'x-hbo-client-version': 'Hadron/50.50.0.85 desktop (DESKTOP)',
        'x-hbo-device-name': 'desktop',
        'x-hbo-device-os-version': 'undefined'}
    return {'headers': headers}
    
def get_auth_token_info(cfg):
    data = {
        "grant_type": "user_name_password",
        "scope": "browse video_playback device elevated_account_management",
        "username": cfg['username'],
        "password": cfg['password'],
    }
    return {'headers': login_headers, 'data': data, 'device_id': _uuid}

def generate_payload():
    return {"headers": payload}

class HMAXRegion(object):
    def configHBOMaxLatam():
        tokens = config['la']['tokens']
        content = config['la']['content']
        license_wv = config['la']['license_wv']
        return tokens, content, license_wv

    def configHBOMaxUS():
        tokens = config['us']['tokens']
        content = config['us']['content']
        license_wv = config['us']['license_wv']
        return tokens, content, license_wv
