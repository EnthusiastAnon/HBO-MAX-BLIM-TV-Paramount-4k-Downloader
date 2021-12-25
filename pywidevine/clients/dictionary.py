import re
from unidecode import unidecode

def get_release_tag(default_filename, vcodec, video_height, acodec, channels, bitrate, module, tag, isDual):
    video_codec = ''

    if 'avc' in vcodec:
        video_codec = 'H.264'
    if 'hvc' in vcodec:
        video_codec = 'H.265'
    elif 'dvh' in vcodec:
        video_codec = 'HDR'

    if isDual==False:
        audio_codec = ''
        if 'mp4a' in acodec:
            audio_codec = 'AAC'
        if acodec == 'ac-3':
            audio_codec = 'DD'
        if acodec == 'ec-3':
            audio_codec = 'DDP'
        elif acodec == 'ec-3' and bitrate > 700000:
            audio_codec = 'Atmos'
        
        audio_channels = ''
        if channels == '2':
            audio_channels = '2.0'
        elif channels == '6':
            audio_channels = '5.1'
        audio_format = audio_codec + audio_channels
    else:
        audio_format = 'DUAL'
    

    default_filename = default_filename.replace('&', '.and.')
    default_filename = re.sub(r'[]!"#$%\'()*+,:;<=>?@\\^_`{|}~[-]', '', default_filename)
    default_filename = default_filename.replace(' ', '.')
    default_filename = re.sub(r'\.{2,}', '.', default_filename)
    default_filename = unidecode(default_filename)

    output_name = '{}.{}p.{}.WEB-DL.{}.{}-{}'.format(default_filename, video_height, str(module), audio_format, video_codec, tag)
    return output_name