from shutil import which
from os.path import dirname, realpath, join
from os import pathsep, environ

SCRIPT_PATH = dirname(realpath('paramountplus'))

BINARIES_FOLDER = join(SCRIPT_PATH, 'binaries')

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

class WvDownloaderConfig(object):
    def __init__(self, xml, base_url, output_file, track_id, format_id):
        self.xml = xml
        self.base_url = base_url
        self.output_file = output_file
        self.track_id = track_id
        self.format_id = format_id
