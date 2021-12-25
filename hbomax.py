# -*- coding: utf-8 -*-
# Module: HBO Max Downloader
# Created on: 04-11-2020
# Version: 3.5

import sys, os
import subprocess, re, base64, requests
import xmltodict, isodate
import time, glob, uuid, ffmpy, json
import shutil, urllib.parse

from unidecode import unidecode

import pywidevine.clients.hbomax.config as HMAXConfig
import pywidevine.clients.hbomax.client as HMAXClient

from pywidevine.clients.hbomax.config import HMAXRegion
from pywidevine.clients.proxy_config import ProxyConfig
from pywidevine.muxer.muxer import Muxer
from os.path import join, isfile

currentFile = 'hbomax'
realPath = os.path.realpath(currentFile)
dirPath = os.path.dirname(realPath)
SESSION = requests.session()
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"

def main(args):
    
    proxies = {}
    proxy_meta = args.proxy
    if proxy_meta == 'none':
        proxies['meta'] = {'http': None, 'https': None}
    elif proxy_meta:
        proxies['meta'] = {'http': proxy_meta, 'https': proxy_meta}
    SESSION.proxies = proxies.get('meta')
    proxy_cfg = ProxyConfig(proxies)

    if not os.path.exists(dirPath + '/KEYS'):
        os.makedirs(dirPath + '/KEYS')
    else:
        keys_file = dirPath + '/KEYS/HBOMAX.txt'
        try:
            keys_file_hbomax = open(keys_file, 'r', encoding='utf8')
            keys_file_txt = keys_file_hbomax.readlines()
        except Exception:
            with open(keys_file, 'a', encoding='utf8') as (file):
                file.write('##### One KEY per line. #####\n')
            keys_file_hbomax = open(keys_file, 'r', encoding='utf8')
            keys_file_txt = keys_file_hbomax.readlines()

    global folderdownloader
    if args.output:
        if not os.path.exists(args.output):
            os.makedirs(args.output)
        os.chdir(args.output)
        if ":" in str(args.output):
            folderdownloader = str(args.output).replace('/','\\').replace('.\\','\\')
        else:
            folderdownloader = dirPath + '\\' + str(args.output).replace('/','\\').replace('.\\','\\')
    else:
        folderdownloader = dirPath.replace('/','\\').replace('.\\','\\')
        
    def downloadFile(aria2c_infile):
        aria2c_opts = [
            HMAXConfig.ARIA2C,
            '--allow-overwrite=true',
            '--download-result=hide',
            '--console-log-level=warn',
            '--enable-color=false',
            '-x16', '-s16', '-j16',
            '-i', aria2c_infile]
        subprocess.run(aria2c_opts, check=True)

    def downloadFile2(link, file_name):
        with open(file_name, 'wb') as (f):
            print(file_name)
            response = SESSION.get(link, stream=True)
            total_length = response.headers.get('content-length')
            if total_length is None:
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
            
    def find_str(s, char):
        index = 0

        if char in s:
            c = char[0]
            for ch in s:
                if ch == c:
                    if s[index:index+len(char)] == char:
                        return index

                index += 1

        return -1

    def getKeyId(name):
        mp4dump = subprocess.Popen([HMAXConfig.MP4DUMP, name], stdout=subprocess.PIPE)
        mp4dump = str(mp4dump.stdout.read())
        A=find_str(mp4dump, "default_KID")
        KEY_ID_ORI=mp4dump[A:A+63].replace("default_KID = ", "").replace("[", "").replace("]", "").replace(" ", "")
        if KEY_ID_ORI == "":
            KEY_ID_ORI = "nothing"
        return KEY_ID_ORI

    def mediainfo_(file):
        mediainfo_output = subprocess.Popen([HMAXConfig.MEDIAINFO, '--Output=JSON', '-f', file], stdout=subprocess.PIPE)
        mediainfo_json = json.load(mediainfo_output.stdout)
        return mediainfo_json
        
    def replace_words(x):
        x = re.sub(r'[]¡!"#$%\'()*+,:;<=>¿?@\\^_`{|}~[-]', '', x)
        x = x.replace('\\', '').replace('/', ' & ')
        return unidecode(x)

    def ReplaceCodeLanguages(X):
        X = X.lower()
        X = X.replace('_subtitle_dialog_0', '').replace('_narrative_dialog_0', '').replace('_caption_dialog_0', '').replace('_dialog_0', '').replace('_descriptive_0', '_descriptive').replace('_descriptive', '_descriptive').replace('_sdh', '-sdh').replace('es-es', 'es').replace('SPA', 'es').replace('en-es', 'es').replace('kn-in', 'kn').replace('gu-in', 'gu').replace('ja-jp', 'ja').replace('mni-in', 'mni').replace('si-in', 'si').replace('as-in', 'as').replace('ml-in', 'ml').replace('sv-se', 'sv').replace('hy-hy', 'hy').replace('sv-sv', 'sv').replace('da-da', 'da').replace('fi-fi', 'fi').replace('nb-nb', 'nb').replace('is-is', 'is').replace('uk-uk', 'uk').replace('hu-hu', 'hu').replace('bg-bg', 'bg').replace('hr-hr', 'hr').replace('lt-lt', 'lt').replace('et-et', 'et').replace('el-el', 'el').replace('he-he', 'he').replace('ar-ar', 'ar').replace('fa-fa', 'fa').replace('ENG', 'en').replace('ro-ro', 'ro').replace('sr-sr', 'sr').replace('cs-cs', 'cs').replace('sk-sk', 'sk').replace('mk-mk', 'mk').replace('hi-hi', 'hi').replace('bn-bn', 'bn').replace('ur-ur', 'ur').replace('pa-pa', 'pa').replace('ta-ta', 'ta').replace('te-te', 'te').replace('mr-mr', 'mr').replace('kn-kn', 'kn').replace('gu-gu', 'gu').replace('ml-ml', 'ml').replace('si-si', 'si').replace('as-as', 'as').replace('mni-mni', 'mni').replace('tl-tl', 'tl').replace('id-id', 'id').replace('ms-ms', 'ms').replace('vi-vi', 'vi').replace('th-th', 'th').replace('km-km', 'km').replace('ko-ko', 'ko').replace('zh-zh', 'zh').replace('ja-ja', 'ja').replace('ru-ru', 'ru').replace('tr-tr', 'tr').replace('it-it', 'it').replace('es-mx', 'es-la').replace('ar-sa', 'ar').replace('zh-cn', 'zh').replace('nl-nl', 'nl').replace('pl-pl', 'pl').replace('pt-pt', 'pt').replace('hi-in', 'hi').replace('mr-in', 'mr').replace('bn-in', 'bn').replace('te-in', 'te').replace('POR', 'pt').replace('cmn-hans', 'zh-hans').replace('cmn-hant', 'zh-hant').replace('ko-kr', 'ko').replace('en-au', 'en').replace('es-419', 'es-la').replace('es-us', 'es-la').replace('en-us', 'en').replace('en-gb', 'en').replace('fr-fr', 'fr').replace('de-de', 'de').replace('las-419', 'es-la').replace('ar-ae', 'ar').replace('da-dk', 'da').replace('yue-hant', 'yue').replace('bn-in', 'bn').replace('ur-in', 'ur').replace('ta-in', 'ta').replace('sl-si', 'sl').replace('cs-cz', 'cs').replace('hi-jp', 'hi').replace('-001', '').replace('en-US', 'en').replace('deu', 'de').replace('eng', 'en').replace('ca-es', 'cat').replace('fil-ph', 'fil').replace('en-ca', 'en').replace('eu-es', 'eu').replace('ar-eg', 'ar').replace('he-il', 'he').replace('el-gr', 'he').replace('nb-no', 'nb').replace('es-ar', 'es-la').replace('en-ph', 'en').replace('sq-al', 'sq').replace('bs-ba', 'bs')
        return X

    def alphanumericSort(l):
        def convert(text):
            if text.isdigit():
                return int(text)
            else:
                return text

        def alphanum_key(key):
            return [convert(c) for c in re.split('([0-9]+)', key)]

        return sorted(l, key=alphanum_key)

    def convert_size(size_bytes):
        if size_bytes == 0:
            return '0bps'
        else:
            s = round(size_bytes / 1000, 0)
            return '%ikbps' % s

    def get_size(size):
        power = 1024
        n = 0
        Dic_powerN = {0:'',  1:'K',  2:'M',  3:'G',  4:'T'}
        while size > power:
            size /= power
            n += 1
        return str(round(size, 2)) + Dic_powerN[n] + 'B'

    global auth_url, content_url, license_wv

    if args.region == "la":
        auth_url, content_url, license_wv = HMAXRegion.configHBOMaxLatam()

    if args.region == "us":
        auth_url, content_url, license_wv = HMAXRegion.configHBOMaxUS()

    def get_authorization_header(TOKEN):
        headers = HMAXConfig.get_user_headers()['headers']

        headers = {
            "accept": "application/vnd.hbo.v9.full+json",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": str(args.titlelang),
            "Authorization": f"Bearer {TOKEN}",
            "user-agent": HMAXConfig.UA,
            "x-hbo-client-version": "Hadron/50.40.0.111 desktop (DESKTOP)",
            "x-hbo-device-name": "desktop",
            "x-hbo-device-os-version": "undefined"
        }
        return headers

    os.makedirs(HMAXConfig.COOKIES_FOLDER, exist_ok=True)
    HMAXTOKEN_FILE = join(HMAXConfig.COOKIES_FOLDER, 'hmax_login_data.json')
    if not isfile(HMAXTOKEN_FILE):
        access_token = HMAXClient.login(SESSION, auth_url, content_url)

    def refresh_token():
        content = None
        TOKEN = False
        with open(HMAXTOKEN_FILE,'rb') as f:
            content = f.read().decode('utf-8')
        jso = json.loads(content)
        token_exp = int(time.time()) - jso["EXPIRATION_TIME"]
        if int(token_exp/60) > 15:
            TOKEN = False
        elif int(token_exp/60) < 15:
            TOKEN = True

        if TOKEN:
            access_token = jso['ACCESS_TOKEN']

        if not TOKEN:
            access_token = HMAXClient.login(SESSION, auth_url, content_url)
        return get_authorization_header(access_token)

    def mpd_parse(mpd_url):
        if args.atmos:
            mpd_url = mpd_url.replace('_noatmos', '')
        base_url = mpd_url.rsplit('/', 1)[0] + '/'
        r = SESSION.get(url=mpd_url)
        xml = xmltodict.parse(r.text, force_list={
            'Period', 'AdaptationSet', 'ContentProtection'
        })
        mpd = json.loads(json.dumps(xml))
        period = mpd['MPD']['Period']
        tracks = []
        for pb in period:
            tracks = tracks + pb['AdaptationSet']

        def get_height(width, height):
            if width == '1920':
                return '1080'
            elif width in ('1280', '1248'):
                return '720'
            else:
                return height

        def force_instance(x):
            if isinstance(x['Representation'], list):
                X = x['Representation']
            else:
                X = [x['Representation']]
            return X

        def get_pssh(track):
            pssh = ''
            for t in track.get('ContentProtection', {}):
                if (t['@schemeIdUri'].lower() == 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed'
                        and t.get('pssh', {}).get('#text')):
                    pssh = t.get('pssh', {}).get('#text')
            return pssh

        video_list = []
        for video_tracks in tracks:
            if video_tracks['@contentType'] == 'video':
                for x in video_tracks['Representation']:
                    videoDict = {
                         'Height':get_height(x['@width'], x['@height']), 
                         'Width':x['@width'], 
                         'Bandwidth':x['@bandwidth'], 
                         'ID':x['@id'], 
                         'Codec':x['@codecs'], 
                         'File_URL':x['BaseURL']}
                    video_list.append(videoDict)
        video_list = sorted(video_list, key=(lambda k: int(k['Bandwidth'])))

        if args.videocodec:
            if args.videocodec == 'h264':
                codec_s = 'avc1'
            if args.videocodec == 'hevc':
                codec_s = 'hvc1'
            if args.videocodec == 'hdr':
                codec_s = 'dvh1'
            
            video_list_tmp = []
            for x in video_list:
                if codec_s in x['Codec']:
                    video_list_tmp.append(x)
            video_list = video_list_tmp
        
        while args.customquality != [] and int(video_list[(-1)]['Height']) > int(args.customquality[0]):
            video_list.pop(-1)
        

        audio_list = []
        for audio_tracks in tracks:
            if audio_tracks['@contentType'] == 'audio':
                isAD = False
                pssh = get_pssh(audio_tracks)
                try:
                    if audio_tracks['Role']['@value']:
                        isAD = True
                except KeyError:
                    isAD = False

                if isAD:
                    lang_id = ReplaceCodeLanguages(audio_tracks["@lang"]) + '-ad'
                else:
                    lang_id = ReplaceCodeLanguages(audio_tracks["@lang"])

                for x in force_instance(audio_tracks):
                    audio_dict = {
                         'Bandwidth':x['@bandwidth'],  
                         'ID':x['@id'], 
                         'Language':lang_id, 
                         'Codec':x['@codecs'],
                         'Channels':x['AudioChannelConfiguration']['@value'],
                         'File_URL':x['BaseURL'],
                         'isAD':isAD}
                    audio_list.append(audio_dict)

        audio_list = sorted(audio_list, key=(lambda k: (int(k['Bandwidth']), str(k['Language']))), reverse=True)

        if args.only_2ch_audio:
            c = 0
            while c != len(audio_list):
                if '-3' in audio_list[c]['Codec'].split('=')[0]:
                    audio_list.remove(audio_list[c])
                else:
                    c += 1

        if args.desc_audio:
            c = 0
            while c != len(audio_list):
                if not audio_list[c]['isAD']:
                    audio_list.remove(audio_list[c])
                else:
                    c += 1
        else:
            c = 0
            while c != len(audio_list):
                if audio_list[c]['isAD']:
                    audio_list.remove(audio_list[c])
                else:
                    c += 1

        BitrateList = []
        AudioLanguageList = []
        for x in audio_list:
            BitrateList.append(x['Bandwidth'])
            AudioLanguageList.append(x['Language'])

        BitrateList = alphanumericSort(list(set(BitrateList)))
        AudioLanguageList = alphanumericSort(list(set(AudioLanguageList)))
        audioList_new = []
        audio_Dict_new = {}
        for y in AudioLanguageList:
            counter = 0
            for x in audio_list:
                if x['Language'] == y and counter == 0:
                    audio_Dict_new = {
                        'Language':x['Language'],  
                        'Bandwidth':x['Bandwidth'], 
                        'Codec': x['Codec'],
                        'Channels': x['Channels'],
                        'File_URL':x['File_URL'],
                        'isAD':x['isAD']
                    }
                    audioList_new.append(audio_Dict_new)
                    counter = counter + 1

        audioList = audioList_new
        audio_list = sorted(audioList, key=(lambda k: (int(k['Bandwidth']), str(k['Language']))))

        audioList_new = []
        if args.audiolang:
            for x in audio_list:
                langAbbrev = x['Language']
                if langAbbrev in list(args.audiolang):
                    audioList_new.append(x)
            audio_list = audioList_new

        return (video_list, audio_list, pssh, base_url)

    def get_episodes(ep_str, num_eps):
        eps = ep_str.split(',')
        eps_final = []

        for ep in eps:
            if '-' in ep:
                (start, end) = ep.split('-')
                start = int(start)
                end = int(end or num_eps)
                eps_final += list(range(start, end + 1))
            else:
                eps_final.append(int(ep))

        return eps_final
    
    def get_season(series_id):
        seasons = []
        if args.season:
            if args.season == 'all':
                seasons = 'all'
            elif ',' in args.season:
                seasons = [int(x) for x in args.season.split(',')]
            elif '-' in args.season:
                (start, end) = args.season.split('-')
                seasons = list(range(int(start), int(end) + 1))
            else:
                seasons = [int(args.season)]

        season_req = SESSION.post(url=content_url, headers=refresh_token(), json=[{"id":series_id}], proxies=proxy_cfg.get_proxy('meta')).json()[0]['body']
        try:
            if seasons == 'all':
                seasons = [num for num, season in enumerate(season_req['references']['seasons'], start=1)]
        except KeyError:
            pass

        for season_num in seasons:
            if args.all_season:
                episode_list = season_req['references']['episodes']
            else:
                try:
                    season_id = season_req['references']['seasons'][int(season_num)-1]
                    episode_req = SESSION.post(url=content_url, headers=refresh_token(), json=[{"id":season_id}], proxies=proxy_cfg.get_proxy('meta')).json()[0]['body']
                    episode_list = episode_req['references']['episodes']
                except KeyError:
                    episode_list = season_req['references']['episodes']

            episodes_list_new = []
            for num, ep in enumerate(episode_list, start=1):
                episodes_list_new.insert(num - 0, {
                     'id': ep,
                     'episode_num': num})
                episode_list = sorted(episodes_list_new, key=lambda x: x['episode_num'])

            if args.episodeStart:
                eps = get_episodes(args.episodeStart, len(episode_list))
                episode_list = [x for x in episode_list if x['episode_num'] in eps]

            for episode in episode_list:
                get_metadata(content_id=episode['id'])

    def get_video_id(content_id):
        video_id = 'preview'
        while 'preview' in video_id:
            video_resp = SESSION.post(url=content_url, headers=refresh_token(), json=HMAXClient.get_video_payload(content_id)).json()
            if video_resp[0]["statusCode"] > 200:
                print(video_resp[0]['body']['message'])
                exit(1)
            video_id = [item['body']['references']['video'] for (i, item) in enumerate(video_resp) if 'video' in item['body']['references']][0]
        mpd_url, length, subs_list, chapters = get_infos(video_id)
        return video_resp[0]['body'], mpd_url, length, subs_list, chapters

    def get_infos(video_id):
        video_json = SESSION.post(url=content_url, headers=refresh_token(), json=HMAXClient.get_video_payload(video_id)).json()[0]['body']
        try:
            mpd_url = video_json['fallbackManifest']
        except KeyError:
            mpd_url = video_json['manifest']
        for x in video_json['videos']:
            if x['type'] == 'urn:video:main':
                length = float(x['duration'])
        return mpd_url, length, get_subtitles(video_json), get_chapters(video_json)

    def get_chapters(video_json):
        chapters = []
        for x in video_json['videos']:
            if 'annotations' in x:
                for (i, chapter) in enumerate(x['annotations']):
                    secs, ms = divmod(chapter['start'], 1)
                    mins, secs = divmod(secs, 60)
                    hours, mins = divmod(mins, 60)
                    ms = ms * 10000;
                    chapter_time = '%02d:%02d:%02d.%04d' % (hours, mins, secs, ms)
                    chapters.append({'TEXT':chapter['secondaryType'], 'TIME': chapter_time})
        return chapters

    def get_subtitles(video_json):
        subs_list = []
        for x in video_json['videos']:
            if x['type'] == 'urn:video:main':
                if 'textTracks' in x:
                    for sub in x['textTracks']:
                        
                        isCC = False
                        if 'ClosedCaptions' in sub["type"]:
                            isCC = True
                        isNormal = False
                        if isCC:
                            lang_id = ReplaceCodeLanguages(sub['language']) + '-sdh'
                            trackType = 'SDH'
                        else:
                            lang_id = ReplaceCodeLanguages(sub['language'])
                            isNormal = True
                            trackType = 'NORMAL'
                        isForced = False
                        if sub["type"] == "Forced":
                            isForced = True
                            isNormal = False
                            trackType = 'FORCED'
                            lang_id = ReplaceCodeLanguages(sub['language']) + '-forced'
                        subsDict = {
                         'Language':lang_id, 
                         'URL':sub['url'],
                         'isCC':isCC, 
                         'isForced':isForced, 
                         'isNormal':isNormal, 
                         'Type':trackType}
                        subs_list.append(subsDict)

        subs_list_new = []
        subs_for_list_new = []
        for subs in subs_list:
            isForced = subs['isForced']
            if isForced:
                subs_for_list_new.append(subs)
            else:
                subs_list_new.append(subs)

        subs_for_list = []
        for subs in subs_for_list_new:
            lang = subs['Language']
            if args.forcedlang:
                if lang in args.forcedlang:
                    subs_for_list.append(subs)
            else:
                subs_for_list.append(subs)

        subs_list = []
        for subs in subs_list_new:
            lang = subs['Language']
            if args.sublang:
                if lang in args.sublang:
                    subs_list.append(subs)
            else:
                subs_list.append(subs)

        subs_list_new = []
        subs_list_new = subs_list + subs_for_list
        subs_list = subs_list_new

        return subs_list

    def get_metadata(content_id):
        meta_resp, mpd_url, length, subs_list, chapters = get_video_id(content_id)

        if 'feature' in args.url_season:
            hbomaxType = "movie"
            releaseYear =  meta_resp['releaseYear']
            seriesTitles = meta_resp['titles']['full']
            episodeTitle = meta_resp['titles']['full']

        if 'numberInSeries' in meta_resp:
            hbomaxType = "show"
            numberInSeries = meta_resp['numberInSeries']
            seriesTitles = meta_resp['seriesTitles']['full']
            episodeTitle = meta_resp['titles']['full']

        if 'numberInSeason' in meta_resp:
            hbomaxType = "show"
            seriesTitles = meta_resp['seriesTitles']['full']
            seasonNumber = meta_resp['seasonNumber']
            episodeNumber = meta_resp['numberInSeason']
            episodeTitle = meta_resp['titles']['full']

        if hbomaxType=="movie":
            seriesName = f'{replace_words(episodeTitle)} ({releaseYear})'
            folderName = None

        if hbomaxType=="show":
            try:
                seriesName = f'{replace_words(seriesTitles)} S{seasonNumber:02}E{episodeNumber:02} - {replace_words(episodeTitle)}'
                folderName = f'{replace_words(seriesTitles)} S{seasonNumber:02}'
            except UnboundLocalError:
                seriesName = f'{replace_words(seriesTitles)} E{numberInSeries:02} - {replace_words(episodeTitle)}'
                folderName = f'{replace_words(seriesTitles)}'

        start_process(seriesName, folderName, subs_list, mpd_url, length, chapters, hbomaxType)

    def start_process(seriesName, folderName, subs_list, mpd_url, length, chapters, hbomaxType):
        video_list, audio_list, pssh, base_url = mpd_parse(mpd_url)
        video_bandwidth = dict(video_list[(-1)])['Bandwidth']
        video_height = str(dict(video_list[(-1)])['Height'])
        video_width = str(dict(video_list[(-1)])['Width'])
        video_codec = str(dict(video_list[(-1)])['Codec'])
        if not args.license:
            if not args.novideo:
                print('\nVIDEO - Bitrate: ' + convert_size(int(video_bandwidth)) + ' - Profile: ' + video_codec.split('=')[0] + ' - Size: ' + get_size(length * float(video_bandwidth) * 0.125) + ' - Dimensions: ' + video_width + 'x' + video_height)
            print()
            if not args.noaudio:
                if audio_list != []:
                    for x in audio_list:
                        audio_bandwidth = x['Bandwidth']
                        audio_representation_id = str(x['Codec'])
                        audio_lang = x['Language']
                        print('AUDIO - Bitrate: ' + convert_size(int(audio_bandwidth)) + ' - Profile: ' + audio_representation_id.split('=')[0] + ' - Size: ' + get_size(length * float(audio_bandwidth) * 0.125) + ' - Language: ' + audio_lang)
            print()
            if not args.nosubs:
                if subs_list != []:
                    for z in subs_list:
                        sub_lang = str(dict(z)['Language'])
                        sub_profile = str(dict(z)['Type'])
                        print('SUBTITLE - Profile: '+ sub_profile +' - Language: ' + sub_lang)
            print()
            print('Name: ' + seriesName + '\n')

        if args.license:
            format_mpd = ""
            if 'hvc1' in video_codec:
                format_mpd = "HEVC KEYS"
            keys_all = get_keys(pssh)
            with open(keys_file, 'a', encoding='utf8') as (file):
                file.write(seriesName + format_mpd + '\n')
            for key in keys_all:
                with open(keys_file, 'a', encoding='utf8') as (file):
                    file.write(key + '\n')
            print('\n' + seriesName + ' ' + format_mpd + '\n' + key)

        else:
            '''
            if args.tag:
                from pywidevine.clients.dictionary import get_release_tag
                for x in audio_list:
                    isDual = False
                    audio_total = len(audio_list)
                    if audio_total > 1:
                        isDual = True
                seriesName = get_release_tag(seriesName, video_codec, video_height, x['Codec'], x['Channels'], x['Bandwidth'], 'HMAX', str(args.tag), isDual)
            '''

            if hbomaxType == 'show':
                CurrentName = seriesName
                CurrentHeigh = str(video_height)
                if 'hvc1' in video_codec:
                    VideoOutputName = folderdownloader + '\\' + str(folderName) + str(CurrentName) + ' [' + str(CurrentHeigh) + 'p] [HEVC].mkv'
                if 'dvh1' in video_codec:
                    VideoOutputName = folderdownloader + '\\' + str(folderName) + str(CurrentName) + ' [' + str(CurrentHeigh) + 'p] [HDR].mkv'
                else:
                    VideoOutputName = folderdownloader + '\\' + str(folderName) + str(CurrentName) + ' [' + str(CurrentHeigh) + 'p].mkv'

            else:
                CurrentName = seriesName
                CurrentHeigh = str(video_height)
                if 'hvc1' in video_codec:
                    VideoOutputName = str(CurrentName) + ' [' + str(CurrentHeigh) + 'p] [HEVC].mkv'
                if 'dvh1' in video_codec:
                    VideoOutputName = str(CurrentName) + ' [' + str(CurrentHeigh) + 'p] [HDR].mkv'
                else:
                    VideoOutputName = str(CurrentName) + ' [' + str(CurrentHeigh) + 'p].mkv'

            if not args.novideo or (not args.noaudio):
                print("Getting KEYS...")
                keys_all = get_keys(pssh)
                if not keys_all:
                    print('License request failed, using keys from txt')
                    keys_all = keys_file_txt
                if args.licenses_as_json:
                    with open(keys_file, "a", encoding="utf8") as file:
                        file.write(seriesName + "\n")
                    for key in keys_all:
                        with open(keys_file, "a", encoding="utf8") as file:
                            file.write(key + "\n")
                print("Done!\n")

            if not os.path.isfile(VideoOutputName):
                
                print('Downloading video & audio')
                aria2c_input = ''
                if not args.novideo:
                    if 'hvc1' in video_codec:
                        inputVideo = seriesName + ' [' + str(CurrentHeigh) + 'p] [HEVC].mp4'
                    if 'dvh1' in video_codec:
                        inputVideo = seriesName + ' [' + str(CurrentHeigh) + 'p] [HDR].mp4'
                    else:
                        inputVideo = seriesName + ' [' + str(CurrentHeigh) + 'p].mp4'
                    if os.path.isfile(inputVideo) and not os.path.isfile(inputVideo + '.aria2'):
                        print('\n' + inputVideo + '\nFile has already been successfully downloaded previously.\n')
                    else:
                        url = urllib.parse.urljoin(base_url, video_list[(-1)]['File_URL'])
                        aria2c_input += f'{url}\n'
                        aria2c_input += f'\tdir={folderdownloader}\n'
                        aria2c_input += f'\tout={inputVideo}\n'

                        #downloadFile(base_url + video_list[(-1)]['File_URL'], inputVideo)

                if not args.noaudio:
                    for x in audio_list:
                        langAbbrev = x['Language']
                        inputAudio = seriesName + ' ' + '(' + langAbbrev + ')' + '.mp4'
                        inputAudio_ac3 = seriesName + ' ' + '(' + langAbbrev + ')' + '.ac3'
                        inputAudio_eac3 = seriesName + ' ' + '(' + langAbbrev + ')' + '.eac3'
                        inputAudio_m4a = seriesName + ' ' + '(' + langAbbrev + ')' + '.m4a'
                        if os.path.isfile(inputAudio) and not os.path.isfile(inputAudio + '.aria2') or os.path.isfile(inputAudio_ac3) or os.path.isfile(inputAudio_m4a) or os.path.isfile(inputAudio_eac3):
                            print('\n' + inputAudio + '\nFile has already been successfully downloaded previously.\n')
                        else:
                            url = urllib.parse.urljoin(base_url, x['File_URL'])
                            aria2c_input += f'{url}\n'
                            aria2c_input += f'\tdir={folderdownloader}\n'
                            aria2c_input += f'\tout={inputAudio}\n'

                aria2c_infile = os.path.join(folderdownloader, 'aria2c_infile.txt')
                with open(aria2c_infile, 'w') as fd:
                    fd.write(aria2c_input)
                aria2c_opts = [
                    HMAXConfig.ARIA2C,
                     '--allow-overwrite=true',
                     '--download-result=hide',
                     '--console-log-level=warn',
                     '-x16', '-s16', '-j16',
                     '-i', aria2c_infile]
                subprocess.run(aria2c_opts, check=True)

                if not args.nosubs:
                    if subs_list != []:
                        for z in subs_list:
                            langAbbrev = str(dict(z)['Language'])
                            inputSubtitle = seriesName + " " + "(" + langAbbrev + ")"
                            if os.path.isfile(inputSubtitle + ".xml") or os.path.isfile(inputSubtitle + ".srt"):
                                print("\n" + inputSubtitle + "\nFile has already been successfully downloaded previously.\n")
                            else:
                                downloadFile2(str(dict(z)['URL']), inputSubtitle + ".xml")
                                SubtitleEdit_process = subprocess.Popen([HMAXConfig.SUBTITLE_EDIT, "/convert", inputSubtitle + ".xml", "srt", "/fixcommonerrors", "/encoding:utf-8", "/RemoveLineBreaks"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
                                for f in glob.glob(inputSubtitle + ".xml"):
                                    os.remove(f)
                                print("Done!\n")
                    else:
                        print ("\nNo subtitles available.")

                if not args.nochpaters:
                    if chapters != []:
                        print('\nGenerating chapters file...')
                        if os.path.isfile(seriesName + ' Chapters.txt'):
                            print(seriesName + " Chapters.txt" + " has already been successfully downloaded previously.")
                        else:
                            counter = 1
                            with open(seriesName + ' Chapters.txt', 'a', encoding='utf-8') as f:
                                for x in chapters:
                                    f.write("CHAPTER" + f'{counter:02}' + "=" + x["TIME"] + "\n" + "CHAPTER" + f'{counter:02}' + "NAME=" + x["TEXT"] + "\n")
                                    counter = counter + 1
                        print('Done!\n')
                    else:
                        print("\nNo chapters available.")

                #~NOTE: aqui faz de tudo! Extrai as keys, faz decrypt e muxa os arquivos

                CorrectDecryptVideo = False
                if not args.novideo:
                    if 'hvc1' in video_codec:
                        inputVideo = seriesName + ' [' + str(CurrentHeigh) + 'p] [HEVC].mp4'
                    if 'dvh1' in video_codec:
                        inputVideo = seriesName + ' [' + str(CurrentHeigh) + 'p] [HDR].mp4'
                    else:
                        inputVideo = seriesName + ' [' + str(CurrentHeigh) + 'p].mp4'
                    if os.path.isfile(inputVideo):
                        CorrectDecryptVideo = DecryptVideo(inputVideo=inputVideo, keys_video=keys_all)
                    else:
                        CorrectDecryptVideo = True
                
                CorrectDecryptAudio = False
                if not args.noaudio:
                    for x in audio_list:
                        langAbbrev = x['Language']
                        inputAudio = seriesName + ' ' + '(' + langAbbrev + ')' + '.mp4'
                        if os.path.isfile(inputAudio):
                            CorrectDecryptAudio = DecryptAudio(inputAudio=inputAudio, keys_audio=keys_all)
                        else:
                            CorrectDecryptAudio = True

                if not args.nomux:
                    if not args.novideo:
                        if not args.noaudio:
                            if CorrectDecryptVideo == True:
                                if CorrectDecryptAudio == True:
                                    print('\nMuxing...')

                                    if hbomaxType=="show":
                                        MKV_Muxer=Muxer(CurrentName=CurrentName,
                                                        SeasonFolder=folderName,
                                                        CurrentHeigh=CurrentHeigh,
                                                        Type=hbomaxType,
                                                        mkvmergeexe=HMAXConfig.MKVMERGE)

                                    else:
                                        MKV_Muxer=Muxer(CurrentName=CurrentName,
                                                        SeasonFolder=None,
                                                        CurrentHeigh=CurrentHeigh,
                                                        Type=hbomaxType,
                                                        mkvmergeexe=HMAXConfig.MKVMERGE)

                                    MKV_Muxer.mkvmerge_muxer(lang="English")

                                    if args.tag:
                                        if 'hvc1' in video_codec:
                                            inputName = CurrentName + ' [' + CurrentHeigh + 'p] [HEVC].mkv'
                                        if 'dvh1' in video_codec:
                                            inputName = seriesName + ' [' + str(CurrentHeigh) + 'p] [HDR].mkv'
                                        else:
                                            inputName = CurrentName + ' [' + CurrentHeigh + 'p].mkv'

                                        release_group(base_filename=inputName,
                                                    default_filename=CurrentName,
                                                    folder_name=folderName,
                                                    type=hbomaxType,
                                                    video_height=CurrentHeigh)

                                    if not args.keep:
                                        for f in os.listdir():
                                            if re.fullmatch(re.escape(CurrentName) + r'.*\.(mp4|m4a|h264|h265|eac3|ac3|srt|txt|avs|lwi|mpd)', f):
                                                os.remove(f)
                                    print('Done!')
            else:
                print("File '" + str(VideoOutputName) + "' already exists.")

    def title_parse(x):
        m = re.match(r'https?://(play\.hbomax\.com/|(?:www\.)hbomax\.com/)(?:page|feature|series|episode)/(urn?:hbo?:(?:feature|series|page|episode):.+?$)', x)
        if m:
            if 'type' in m[2] and 'series' in m[2]:
                m = 'urn:hbo:series:{}'.format(m[2].split(':')[-3])
            elif 'type' in m[2] and 'feature' in m[2]:
                m = 'urn:hbo:feature:{}'.format(m[2].split(':')[-3])
            elif 'type' in m[2] and 'episode' in m[2]:
                m = 'urn:hbo:episode:{}'.format(m[2].split(':')[-3])
            else:
                m = m[2]
        return m

    from pywidevine.decrypt.wvdecryptcustom import WvDecrypt
    from pywidevine.cdm import cdm, deviceconfig

    def get_keys(pssh):
        device = deviceconfig.device_android_generic
        wvdecrypt = WvDecrypt(init_data_b64=bytes(pssh.encode()), cert_data_b64=None, device=device)

        license_req = SESSION.post(url=license_wv, headers=refresh_token(), data=wvdecrypt.get_challenge()).content
        license_b64 = base64.b64encode(license_req)

        wvdecrypt.update_license(license_b64)
        status, keys = wvdecrypt.start_process()
        return keys

    def release_group(base_filename, default_filename, folder_name, type, video_height):
        if type=='show':
            video_mkv = os.path.join(folder_name, base_filename)
        else:
            video_mkv = base_filename
        
        mediainfo = mediainfo_(video_mkv)
        for v in mediainfo['media']['track']: # mediainfo do video
            if v['@type'] == 'Video':
                video_format = v['Format']

        video_codec = ''
        if video_format == "AVC":
            video_codec = 'H.264'
        elif video_format == "HEVC":
            video_codec = 'H.265'

        for m in mediainfo['media']['track']: # mediainfo do audio
            if m['@type'] == 'Audio':
                codec_name = m['Format']
                channels_number = m['Channels']

        audio_codec = ''
        audio_channels = ''
        if codec_name == "AAC":
            audio_codec = 'AAC'
        elif codec_name == "AC-3":
            audio_codec = "DD"
        elif codec_name == "E-AC-3":
            audio_codec = "DDP"
        elif codec_name == "E-AC-3 JOC":
            audio_codec = "Atmos"
            
        if channels_number == "2":
            audio_channels = "2.0"
        elif channels_number == "6":
            audio_channels = "5.1"

        audio_ = audio_codec + audio_channels

        # renomear arquivo
        default_filename = default_filename.replace('&', '.and.')
        default_filename = re.sub(r'[]!"#$%\'()*+,:;<=>?@\\^_`{|}~[-]', '', default_filename)
        default_filename = default_filename.replace(' ', '.')
        default_filename = re.sub(r'\.{2,}', '.', default_filename)

        output_name = '{}.{}p.HMAX.WEB-DL.{}.{}-{}'.format(default_filename, video_height, audio_, video_codec, args.tag)
        if type=='show':
            outputName = os.path.join(folder_name, output_name + '.mkv')
        else:
            outputName = output_name + '.mkv'

        os.rename(video_mkv, outputName)
        print("{} -> {}".format(base_filename, output_name))
        
    def DecryptAudio(inputAudio, keys_audio):
        key_audio_id_original = getKeyId(inputAudio)
        outputAudioTemp = inputAudio.replace('.mp4', '_dec.mp4')
        if key_audio_id_original != 'nothing':
            for key in keys_audio:
                key_id = key[0:32]
                if key_id == key_audio_id_original:
                    print('\nDecrypting audio...')
                    print('Using KEY: ' + key)
                    wvdecrypt_process = subprocess.Popen([HMAXConfig.MP4DECRYPT, '--show-progress', '--key', key, inputAudio, outputAudioTemp])
                    stdoutdata, stderrdata = wvdecrypt_process.communicate()
                    wvdecrypt_process.wait()
                    time.sleep(0.05)
                    os.remove(inputAudio)
                    print('\nDemuxing audio...')
                    mediainfo = mediainfo_(outputAudioTemp)
                    for m in mediainfo['media']['track']:
                        if m['@type'] == 'Audio':
                            codec_name = m['Format']
                            try:
                                codec_tag_string = m['Format_Commercial_IfAny']
                            except Exception:
                                codec_tag_string = ''
                    ext = ''
                    if codec_name == "AAC":
                        ext = '.m4a'
                    elif codec_name == "E-AC-3":
                        ext = ".eac3"
                    elif codec_name == "AC-3":
                        ext = ".ac3"
                    outputAudio = outputAudioTemp.replace("_dec.mp4", ext)
                    print("{} -> {}".format(outputAudioTemp, outputAudio))
                    ff = ffmpy.FFmpeg(executable=HMAXConfig.FFMPEG, inputs={outputAudioTemp: None}, outputs={outputAudio: '-c copy'}, global_options="-y -hide_banner -loglevel warning")
                    ff.run()
                    time.sleep (50.0/1000.0)
                    os.remove(outputAudioTemp)
                    print("Done!")
                    return True

        elif key_audio_id_original == "nothing":
            return True

    def DecryptVideo(inputVideo, keys_video):
        key_video_id_original = getKeyId(inputVideo)
        inputVideo = inputVideo
        outputVideoTemp = inputVideo.replace('.mp4', '_dec.mp4')
        outputVideo = inputVideo
        if key_video_id_original != 'nothing':
            for key in keys_video:
                key_id = key[0:32]
                if key_id == key_video_id_original:
                    print('\nDecrypting video...')
                    print('Using KEY: ' + key)
                    wvdecrypt_process = subprocess.Popen([HMAXConfig.MP4DECRYPT, '--show-progress', '--key', key, inputVideo, outputVideoTemp])
                    stdoutdata, stderrdata = wvdecrypt_process.communicate()
                    wvdecrypt_process.wait()
                    print('\nRemuxing video...')
                    ff = ffmpy.FFmpeg(executable=HMAXConfig.FFMPEG, inputs={outputVideoTemp: None}, outputs={outputVideo: '-c copy'}, global_options='-y -hide_banner -loglevel warning')
                    ff.run()
                    time.sleep(0.05)
                    os.remove(outputVideoTemp)
                    print('Done!')
                    return True

        elif key_video_id_original == 'nothing':
            return True

    global content_id
    content_id = title_parse(args.url_season)
    
    if 'series' in args.url_season:
        if not args.season:
            args.season = 'all'
        get_season(content_id)
    elif 'feature' or 'episode':
        get_metadata(content_id=content_id)
