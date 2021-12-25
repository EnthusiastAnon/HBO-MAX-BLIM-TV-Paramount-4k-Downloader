import isodate

def get_mpd_list(mpd):
    def get_height(width, height):
        if width == '1920':
            return '1080'
        elif width in ('1280', '1248'):
            return '720'
        else:
            return height

    length = isodate.parse_duration(mpd['MPD']['@mediaPresentationDuration']).total_seconds()
    period = mpd['MPD']['Period']
    base_url = period['BaseURL']
    tracks = period['AdaptationSet']
                    
    video_list = []
    for video_tracks in tracks:
        if video_tracks['@mimeType'] == 'video/mp4':
            for x in video_tracks['Representation']:
                try:
                    codecs = x['@codecs']
                except KeyError:
                    codecs = video_tracks['@codecs']

                videoDict = {
                        'Height':get_height(x['@width'], x['@height']), 
                        'Width':x['@width'], 
                        'Bandwidth':x['@bandwidth'], 
                        'ID':x['@id'], 
                        'Codec':codecs}
                video_list.append(videoDict)

    def list_representation(x):
        if isinstance(x['Representation'], list):
            X = x['Representation']
        else:
            X = [x['Representation']]
        return X

    def replace_code_lang(x):
        X = x.replace('es', 'es-la').replace('en', 'es-la')
        return X

    audio_list = []
    for audio_tracks in tracks:
        if audio_tracks['@mimeType'] == 'audio/mp4':
            for x in list_representation(audio_tracks):
                try:
                    codecs = x['@codecs']
                except KeyError:
                    codecs = audio_tracks['@codecs']
                audio_dict = {
                        'Bandwidth':x['@bandwidth'],  
                        'ID':x['@id'], 
                        'Language':audio_tracks["@lang"], 
                        'Codec':codecs}
                audio_list.append(audio_dict)

    subs_list = []
    for subs_tracks in tracks:
        if subs_tracks['@mimeType'] == 'text/vtt':
            for x in list_representation(subs_tracks):
                subs_dict = {
                        'ID':x['@id'], 
                        'Language':replace_code_lang(subs_tracks["@lang"]), 
                        'Codec':subs_tracks['@mimeType'],
                        'File_URL':base_url + x['BaseURL'].replace('../', '')}
                subs_list.append(subs_dict)

    return length, video_list, audio_list, subs_list

def get_ism_list(ism):
    length = float(ism['SmoothStreamingMedia']['@Duration'][:-7])
    tracks = ism['SmoothStreamingMedia']["StreamIndex"]

    video_list = []
    for video_tracks in tracks:
        if video_tracks['@Type'] == 'video':
            for x in video_tracks['QualityLevel']:
                videoDict = {
                        'Height':x['@MaxHeight'], 
                        'Width':x['@MaxWidth'],
                        'ID':'0',
                        'Bandwidth':x['@Bitrate'], 
                        'Codec':x["@FourCC"]}
                video_list.append(videoDict)

    def replace_code_lang(x):
        X = x.replace('255', 'es-la')
        return X

    audio_list = []
    for audio_tracks in tracks:
        if audio_tracks['@Type'] == 'audio':
            for x in audio_tracks["QualityLevel"]:
                audio_dict = {
                        'Bandwidth':x['@Bitrate'],
                        'ID':'0', 
                        'Language':replace_code_lang(x["@AudioTag"]), 
                        'Codec':x["@FourCC"]}
                audio_list.append(audio_dict)

    return length, video_list, audio_list, []
