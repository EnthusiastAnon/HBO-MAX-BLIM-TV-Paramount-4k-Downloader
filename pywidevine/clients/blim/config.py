from shutil import which
from os.path import dirname, realpath, join
from os import pathsep, environ

ENDPOINTS = {
    'login': 'https://api.blim.com/account/login',
    'seasons': 'https://api.blim.com/asset/',
    'content': 'https://api.blim.com/play/resume/',
    'config': 'https://www.blim.com/secure/play/resume/configuration?config_token=portal-config'
}

protection_keys = {
    '094af042a17556c5b28a176deffdd4a7:14319c175eb145071fe189d2b1da8634',
    '4ae10c2357e250e088bb8a5ab044dd50:e7f47e2b948e9222cf4d24b51881ec04',
    'b6e16839eebd4ff6ab768d482d8d2b6a:ad6c675e0810741538f7f2f0b4099d9e'
}

init_files = {
    '1080p': 'https://cdn.discordapp.com/attachments/686581369249333291/857062526856200252/video_init_1920x1080.bin',
    '480p': 'https://cdn.discordapp.com/attachments/686581369249333291/857062525421092944/video_640x480.bin',
    'audio': 'https://cdn.discordapp.com/attachments/686581369249333291/857104327742193735/audio_init.bin'
}

SCRIPT_PATH = dirname(realpath('blimtv'))

BINARIES_FOLDER = join(SCRIPT_PATH, 'binaries')
COOKIES_FOLDER = join(SCRIPT_PATH, 'cookies')

MP4DECRYPT_BINARY = 'mp4decrypt'
MP4DUMP_BINARY = 'mp4dump'
MKVMERGE_BINARY = 'mkvmerge'
FFMPEG_BINARY = 'ffmpeg'
ARIA2C_BINARY = 'aria2c'

# Add binaries folder to PATH as the first item
environ['PATH'] = pathsep.join([BINARIES_FOLDER, environ['PATH']])

MP4DECRYPT = which(MP4DECRYPT_BINARY)
MP4DUMP = which(MP4DUMP_BINARY)
MKVMERGE = which(MKVMERGE_BINARY)
FFMPEG = which(FFMPEG_BINARY)
ARIA2C = which(ARIA2C_BINARY)

class PrDownloaderConfig(object):
    def __init__(self, ism, base_url, output_file, bitrate, init_url, file_type):
        self.ism = ism
        self.base_url = base_url
        self.output_file = output_file
        self.bitrate = bitrate
        self.init_url = init_url
        self.file_type = file_type

class WvDownloaderConfig(object):
    def __init__(self, mpd, base_url, output_file, format_id, file_type):
        self.mpd = mpd
        self.base_url = base_url
        self.output_file = output_file
        self.format_id = format_id
        self.file_type = file_type