# -*- coding: utf-8 -*-
# Module: Paramount Plus Downloader
# Created on: 19-02-2021
# Authors: JUNi
# Version: 2.0

import urllib.parse
import re, base64, requests, sys, os
import subprocess, shutil
import xmltodict, isodate
import json, ffmpy
import http, html, time

from unidecode import unidecode
from http.cookiejar import MozillaCookieJar
from titlecase import titlecase
from pymediainfo import MediaInfo

import pywidevine.clients.paramountplus.config as pmnp_cfg
from pywidevine.clients.proxy_config import ProxyConfig
from pywidevine.muxer.muxer import Muxer

from pywidevine.clients.paramountplus.downloader import WvDownloader
from pywidevine.clients.paramountplus.config import WvDownloaderConfig


currentFile = 'paramountplus'
realPath = os.path.realpath(currentFile)
dirPath = os.path.dirname(realPath)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
SESSION = requests.Session()

def main(args):
    global _id
    
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
        keys_file = dirPath + '/KEYS/PARAMOUNTPLUS.txt'
        try:
            keys_file_pmnp = open(keys_file, 'r')
            keys_file_txt = keys_file_pmnp.readlines()
        except Exception:
            with open(keys_file, 'a', encoding='utf8') as (file):
                file.write('##### One KEY per line. #####\n')
            keys_file_pmnp = open(keys_file, 'r', encoding='utf8')
            keys_file_txt = keys_file_pmnp.readlines()

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

    def getKeyId(name):
        mp4dump = subprocess.Popen([pmnp_cfg.MP4DUMP, name], stdout=(subprocess.PIPE))
        mp4dump = str(mp4dump.stdout.read())
        A = find_str(mp4dump, 'default_KID')
        KEY_ID_ORI = ''
        KEY_ID_ORI = mp4dump[A:A + 63].replace('default_KID = ', '').replace('[', '').replace(']', '').replace(' ', '')
        if KEY_ID_ORI == '' or KEY_ID_ORI == "'":
            KEY_ID_ORI = 'nothing'
        return KEY_ID_ORI

    def find_str(s, char):
        index = 0
        if char in s:
            c = char[0]
            for ch in s:
                if ch == c:
                    if s[index:index + len(char)] == char:
                        return index
                index += 1

        return -1

    def mediainfo_(file):
        mediainfo_output = subprocess.Popen([MediaInfo_exe, '--Output=JSON', '-f', file], stdout=(subprocess.PIPE))
        mediainfo_json = json.load(mediainfo_output.stdout)
        return mediainfo_json

    def ReplaceDontLikeWord(X):
        try:
            X = X.replace(" : ", " - ").replace(": ", " - ").replace(":", " - ").replace("&", "and").replace("+", "").replace(";", "").replace("ÃƒÂ³", "o").\
                replace("[", "").replace("'", "").replace("]", "").replace("/", "").replace("//", "").\
                replace("’", "'").replace("*", "x").replace("<", "").replace(">", "").replace("|", "").\
                replace("~", "").replace("#", "").replace("%", "").replace("{", "").replace("}", "").replace(",", "").\
                replace("?","").replace("¿","")
        except Exception:
            X = X.replace(" : ", " - ").replace(": ", " - ").replace(":", " - ").replace("&", "and").replace("+", "").replace(";", "").\
                replace("ÃƒÂ³", "o").replace("[", "").replace("'", "").replace("]", "").replace("/", "").\
                replace("//", "").replace("’", "'").replace("*", "x").replace("<", "").replace(">", "").replace("|", "").\
                replace("~", "").replace("#", "").replace("%", "").replace("{", "").replace("}", "").replace(",", "").\
                replace("?","").replace("¿","")

        return titlecase(X)

    def replace_code_lang(X):
        X = X.lower()
        X = X.replace('es-mx', 'es-la').replace('pt-BR', 'pt-br').replace('dolby digital', 'en').replace('dd+', 'en')
        return X

    def get_cookies(file_path):
        try:
            cj = http.cookiejar.MozillaCookieJar(file_path)
            cj.load()
        except Exception:
            print('\nCookies not found! Please dump the cookies with the Chrome extension https://chrome.google.com/webstore/detail/cookiestxt/njabckikapfpffapmjgojcnbfjonfjfg and place the generated file in ' + file_path)
            print('\nWarning, do not click on "download all cookies", you have to click on "click here".\n')
            sys.exit(0)

        cookies = str()
        for cookie in cj:
            cookie.value = urllib.parse.unquote(html.unescape(cookie.value))
            cookies = cookies + cookie.name + '=' + cookie.value + ';'

        cookies = list(cookies)
        del cookies[-1]
        cookies = ''.join(cookies)
        return cookies

    cookies_file = 'cookies_pmnp.txt'
    cookies = get_cookies(dirPath + '/cookies/' + cookies_file)
    pmnp_headers = {
        'Accept':'application/json, text/plain, */*', 
        'Access-Control-Allow-Origin':'*', 
        'cookie':cookies, 
        'User-Agent':USER_AGENT
    }

    def mpd_parsing(mpd_url):
        base_url = mpd_url.split('stream.mpd')[0]
        r = SESSION.get(url=mpd_url)
        r.raise_for_status()
        xml = xmltodict.parse(r.text)
        mpdf = json.loads(json.dumps(xml))
        length = isodate.parse_duration(mpdf['MPD']['@mediaPresentationDuration']).total_seconds()
        tracks = mpdf['MPD']['Period']['AdaptationSet']

        def get_pssh(track):
            pssh = ''
            for t in track["ContentProtection"]:
                if t['@schemeIdUri'].lower() == 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed':
                    pssh = t["cenc:pssh"]
            return pssh

        def force_instance(x):
            if isinstance(x['Representation'], list):
                X = x['Representation']
            else:
                X = [x['Representation']]
            return X

        video_list = []
        for video_tracks in tracks:
            if video_tracks['@contentType'] == 'video':
                pssh = get_pssh(video_tracks)
                for x in force_instance(video_tracks):
                    try:
                        codecs = x['@codecs']
                    except (KeyError, TypeError):
                        codecs = video_tracks['@codecs']
                    video_dict = {
                         'Height':x['@height'],
                         'Width':x['@width'], 
                         'Bandwidth':x['@bandwidth'],
                         'ID':x['@id'],
                         'TID':video_tracks['@id'],
                         'Codec':codecs}
                    video_list.append(video_dict)

        video_list = sorted(video_list, key=(lambda k: int(k['Bandwidth'])))

        while args.customquality != [] and int(video_list[(-1)]['Height']) > int(args.customquality[0]):
            video_list.pop(-1)

        audio_list = []
        for audio_tracks in tracks:
            if audio_tracks['@contentType'] == 'audio':
                for x in force_instance(audio_tracks):
                    try:
                        codecs = x['@codecs']
                    except (KeyError, TypeError):
                        codecs = audio_tracks['@codecs']
                    audio_dict = {
                         'Bandwidth':x['@bandwidth'],  
                         'ID':x['@id'],
                         'TID':audio_tracks['@id'],
                         'Language':replace_code_lang(audio_tracks['@lang']), 
                         'Codec':codecs}
                    audio_list.append(audio_dict)

        audio_list = sorted(audio_list, key=(lambda k: (int(k['Bandwidth']), str(k['Language']))), reverse=True)
        if args.only_2ch_audio:
            c = 0
            while c != len(audio_list):
                if '-3' in audio_list[c]['Codec'].split('=')[0]:
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
                        'TID':x['TID'],
                        'ID':x['ID']}
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

        return base_url, length, video_list, audio_list, [], pssh, mpdf

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
    
    _id = args.url_season.split('/')[-2]
    if '/video/' in args.url_season:
        content_regex = r'(\/shows\/)([\w-]+)(\/video\/)([\w-]+)'
        url_match = re.search(content_regex, args.url_season)
        _id = url_match[2]

    def get_content_info():
        if 'shows' in args.url_season:
            pmnp_season_url = 'https://www.paramountplus.com/shows/{}/xhr/episodes/page/0/size/100/xs/0/season/{}/'.format(_id, '')
            season_req = requests.get(url=pmnp_season_url, headers=pmnp_headers, proxies=proxy_cfg.get_proxy('meta'))
            
            if not args.season:
                args.season = 'all'

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

            if seasons == 'all':
                seasons_list = [x['season_number'] for x in season_req.json()['result']['data']]
                seasons = sorted(set(seasons_list))

            for season_num in seasons:
                pmnp_season_url = 'https://www.paramountplus.com/shows/{}/xhr/episodes/page/0/size/500/xs/0/season/{}/'.format(_id, season_num)
                season_req = requests.get(url=pmnp_season_url, headers=pmnp_headers, proxies=proxy_cfg.get_proxy('meta'))
                if season_req.json()['result']['total'] < 1:
                    print('This season doesnt exist!')
                    exit()

                for num, ep in enumerate(season_req.json()['result']['data'], start=1):
                    episodeNumber = ep['episode_number']
                    seasonNumber = ep['season_number']
                    seriesTitle = ReplaceDontLikeWord(ep['series_title'])
                    episodeTitle = ReplaceDontLikeWord(ep['label'])
                    seriesName = f'{seriesTitle} S{seasonNumber:0>2}E{episodeNumber:0>2} - {episodeTitle}'
                    folderName = f'{seriesTitle} S{seasonNumber:0>2}'
                    raw_url = urllib.parse.urljoin('https://www.paramountplus.com', ep['metaData']['contentUrl'])

                    episodes_list_new = []
                    episodes_dict = {
                        'id': ep['content_id'],
                        'raw_url': raw_url,
                        'pid':ep['metaData']['pid'],
                        'seriesName':seriesName, 
                        'folderName':folderName, 
                        'episodeNumber': num,
                        'seasonNumber':seasonNumber,
                        'pmnpType': 'show'}
                    episodes_list_new.append(episodes_dict)
                    episodes_list = []
                    for x in episodes_list_new:
                        episodes_list.append(x)
                    #episodes_list = sorted(episodes_list, key=lambda x: x['episodeNumber'])

                    if args.episodeStart:
                        eps = get_episodes(args.episodeStart, len(episodes_list))
                        episodes_list = [x for x in episodes_list if x['episodeNumber'] in eps]

                    if 'video' in args.url_season:
                        episodes_list = [x for x in episodes_list if x['id'] in url_match.group(4)]

                    for content_json in episodes_list:
                        start_process(content_json)

        if 'movies' in args.url_season:
            while 1:
                resp = requests.get(url=args.url_season + '/', headers=pmnp_headers, proxies=proxy_cfg.get_proxy('meta'))
                if resp.ok:
                    break

            html_data = resp
            html_data = html_data.text.replace('\r\n', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '')
            html_data_list = re.split('(</div>)(?i)', html_data)
            json_web = []
            for div in html_data_list:
                if 'player.paramsVO.adCallParams' in div:
                    print()
                    rg = re.compile('(player.metaData = )(.*)(;player.tms_program_id)')
                    m = rg.search(div)
                    if m:
                        json_web = m.group(2)
                        json_web = json.loads(json_web)

            content_dict = {}
            episodes_list = []
            year_regex = r'(\d{4})'
            movieTitle = ReplaceDontLikeWord(json_web['seriesTitle'])
            try:
                r = re.search(year_regex, json_web['airdate'])
            except KeyError:
                r = re.search(year_regex, json_web['airdate_tv'])
            seriesName = f'{movieTitle} ({r.group(0)})'

            content_dict = {
             'id':json_web['contentId'],
             'raw_url': str(args.url_season),
             'pid': json_web['pid'],
             'seriesName':seriesName,
             'folderName':None, 
             'episodeNumber':1, 
             'seasonNumber':1,
             'pmnpType': 'movie'}
            episodes_list.append(content_dict)

            for content_json in episodes_list:
                start_process(content_json)

    def get_license(id_json):
        while 1:
            resp = requests.get(url=id_json['raw_url'], headers=pmnp_headers, proxies=proxy_cfg.get_proxy('meta'))
            if resp.ok:
                break

        html_data = resp
        html_data = html_data.text.replace('\r\n', '').replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', '')
        html_data_list = re.split('(</div>)(?i)', html_data)
        json_web = []
        for div in html_data_list:
            if '(!window.CBS.Registry.drmPromise) {' in div:
                rg = re.compile('(player.drm = )(.*)(;}player.enableCP)')
                m = rg.search(div)
                if m:
                    json_web = m.group(2)
                    json_web = json.loads(json_web)

        lic_url = json_web['widevine']['url']
        header_auth = json_web['widevine']['header']['Authorization']
        if not lic_url:
            print('Too many requests...')
        return lic_url, header_auth

    global folderdownloader
    if args.output:
        if not os.path.exists(args.output):
            os.makedirs(args.output)
        os.chdir(args.output)
        if ":" in str(args.output):
            folderdownloader = str(args.output).replace('/','\\').replace('.\\','\\')
        else:
            folderdownloader = dirPath + str(args.output).replace('/','\\').replace('.\\','\\')
    else:
        folderdownloader = dirPath.replace('/','\\').replace('.\\','\\')

    def get_manifest(id_json):
        api_manifest = 'https://link.theplatform.com/s/dJ5BDC/{}?format=SMIL&manifest=m3u&Tracking=true&mbr=true'.format(id_json['pid'])
        r = requests.get(url=api_manifest, headers=pmnp_headers, proxies=proxy_cfg.get_proxy('meta'))
        xmls = xmltodict.parse(r.text)
        smil = json.loads(json.dumps(xmls))
        videoSrc = []
        try:
            for x in smil['smil']['body']['seq']['switch']:
                videoSrc = x['video']['@src']
        except Exception:
            videoSrc = smil['smil']['body']['seq']['switch']['video']['@src']
        lic_url, header_auth = get_license(id_json)
        return {'mpd_url': videoSrc, 'license': lic_url, 'lic_header': header_auth}

    def start_process(content_info):
        drm_info = get_manifest(content_info)
        base_url, length, video_list, audio_list, subs_list, pssh, xml = mpd_parsing(drm_info['mpd_url'])
        video_bandwidth = dict(video_list[(-1)])['Bandwidth']
        video_height = str(dict(video_list[(-1)])['Height'])
        video_width = str(dict(video_list[(-1)])['Width'])
        video_codec = str(dict(video_list[(-1)])['Codec'])
        video_format_id = str(dict(video_list[(-1)])['ID'])
        video_track_id = str(dict(video_list[(-1)])['TID'])
        if not args.onlykeys:
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
                        sub_lang = z['Language']
                        print('SUBTITLE - Profile: Normal - Language: ' + sub_lang)
                    print()

            print('Name: ' + content_info['seriesName'])

        if content_info['pmnpType'] == 'show':
            CurrentName = content_info['seriesName']
            CurrentHeigh = str(video_height)
            VideoOutputName = folderdownloader + '\\' + str(content_info['folderName']) + '\\' + str(CurrentName) + ' [' + str(CurrentHeigh) + 'p].mkv'
        else:
            CurrentName = content_info['seriesName']
            CurrentHeigh = str(video_height)
            VideoOutputName = folderdownloader + '\\' + str(CurrentName) + '\\' + ' [' + str(CurrentHeigh) + 'p].mkv'

        if args.onlykeys:
            keys_all = get_keys(drm_info, pssh)
            with open(keys_file, 'a', encoding='utf8') as (file):
                file.write(CurrentName + '\n')
                print('\n' + CurrentName)
            for key in keys_all:
                with open(keys_file, 'a', encoding='utf8') as (file):
                    file.write(key + '\n')
                print(key)

        else:

            if not args.novideo or (not args.noaudio):
                print("\nGetting KEYS...")
                
                try:
                    keys_all = get_keys(drm_info, pssh)
                except KeyError:
                    print('License request failed, using keys from txt')
                    keys_all = keys_file_txt
                else:
                    with open(keys_file, "a", encoding="utf8") as file:
                        file.write(CurrentName + "\n")
                    for key in keys_all:
                        with open(keys_file, "a", encoding="utf8") as file:
                            file.write(key + "\n")
                print("Done!")

            if not os.path.isfile(VideoOutputName):

                if not args.novideo:
                    inputVideo = CurrentName + ' [' + str(CurrentHeigh) + 'p].mp4'
                    if os.path.isfile(inputVideo):
                        print('\n' + inputVideo + '\nFile has already been successfully downloaded previously.\n')
                    else:
                        wvdl_cfg = WvDownloaderConfig(xml, base_url, inputVideo, video_track_id, video_format_id)
                        wvdownloader = WvDownloader(wvdl_cfg)
                        wvdownloader.run()

                if not args.noaudio:
                    for x in audio_list:
                        langAbbrev = x['Language']
                        format_id = x['ID']
                        inputAudio = CurrentName + ' ' + '(' + langAbbrev + ').mp4'
                        inputAudio_demuxed = CurrentName + ' ' + '(' + langAbbrev + ')' + '.m4a'
                        if os.path.isfile(inputAudio) or os.path.isfile(inputAudio_demuxed):
                            print('\n' + inputAudio + '\nFile has already been successfully downloaded previously.\n')
                        else:
                            wvdl_cfg = WvDownloaderConfig(xml, base_url, inputAudio, x['TID'], x['ID'])
                            wvdownloader = WvDownloader(wvdl_cfg)
                            wvdownloader.run()

                CorrectDecryptVideo = False
                if not args.novideo:
                    inputVideo = CurrentName + ' [' + str(CurrentHeigh) + 'p].mp4'
                    if os.path.isfile(inputVideo):
                        CorrectDecryptVideo = DecryptVideo(inputVideo=inputVideo, keys_video=keys_all)
                    else:
                        CorrectDecryptVideo = True
                        
                CorrectDecryptAudio = False
                if not args.noaudio:
                    for x in audio_list:
                        langAbbrev = x['Language']
                        inputAudio = CurrentName + ' ' + '(' + langAbbrev + ')' + '.mp4'
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

                                    pmnpType = content_info['pmnpType']
                                    folderName = content_info['folderName']

                                    if pmnpType=="show":
                                        MKV_Muxer=Muxer(CurrentName=CurrentName,
                                                        SeasonFolder=folderName,
                                                        CurrentHeigh=CurrentHeigh,
                                                        Type=pmnpType,
                                                        mkvmergeexe=pmnp_cfg.MKVMERGE)

                                    else:
                                        MKV_Muxer=Muxer(CurrentName=CurrentName,
                                                        SeasonFolder=None,
                                                        CurrentHeigh=CurrentHeigh,
                                                        Type=pmnpType,
                                                        mkvmergeexe=pmnp_cfg.MKVMERGE)

                                    MKV_Muxer.mkvmerge_muxer(lang="English")

                                    if args.tag:
                                        inputName = CurrentName + ' [' + CurrentHeigh + 'p].mkv'
                                        release_group(base_filename=inputName,
                                                      default_filename=CurrentName,
                                                      folder_name=folderName,
                                                      type=pmnpType,
                                                      video_height=CurrentHeigh)

                                    if not args.keep:
                                        for f in os.listdir():
                                            if re.fullmatch(re.escape(CurrentName) + r'.*\.(mp4|m4a|h264|h265|eac3|srt|txt|avs|lwi|mpd)', f):
                                                os.remove(f)
                                    print("Done!")
            else:
                print("\nFile '" + str(VideoOutputName) + "' already exists.")

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
            audio_codec = "ATMOS"
            
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
        default_filename = unidecode(default_filename)

        output_name = '{}.{}p.PMNP.WEB-DL.{}.{}-{}'.format(default_filename, video_height, audio_, video_codec, args.tag)
        if type=='show':
            outputName = os.path.join(folder_name, output_name + '.mkv')
        else:
            outputName = output_name + '.mkv'

        os.rename(video_mkv, outputName)
        print("{} -> {}".format(base_filename, output_name))

    from pywidevine.decrypt.wvdecryptcustom import WvDecrypt
    from pywidevine.cdm import cdm, deviceconfig

    def do_decrypt(init_data_b64, cert_data_b64, device, licurl, licheader):
        wvdecrypt = WvDecrypt(init_data_b64=init_data_b64, cert_data_b64=cert_data_b64, device=deviceconfig.device_android_generic)
        chal = wvdecrypt.get_challenge()
        headers = {
            'authorization': licheader
        }
        
        try:
            license_res = requests.Session().post(url=licurl, data=chal, headers=headers, proxies=proxy_cfg.get_proxy('meta'))
            license_base64 = base64.b64encode(license_res.content)
        except Exception:
            print(license_res.text)
            license_base64 = "Error"
            return license_base64
        if license_base64 != 'Error':
            wvdecrypt.update_license(license_base64)
            wvdecrypt.start_process()
            Correct, keyswvdecrypt = wvdecrypt.start_process()
            return Correct, keyswvdecrypt
        else:
            keyswvdecrypt = []
            Correct = True
            return Correct, keyswvdecrypt

    def get_keys(lic_info, pssh):
        Correct = False
        keys_new = []
        device = deviceconfig.DeviceConfig(deviceconfig.device_android_generic)
        while Correct is False:
            Correct, keys_new = do_decrypt(init_data_b64=bytes(pssh.encode()), cert_data_b64=None, device=device, licurl=lic_info['license'], licheader=lic_info['lic_header'])
        return keys_new

    def DecryptAudio(inputAudio, keys_audio):
        key_audio_id_original = getKeyId(inputAudio)
        outputAudioTemp = inputAudio.replace(".mp4", "_dec.mp4")
        if key_audio_id_original != "nothing":
            for key in keys_audio:
                key_id=key[0:32]
                if key_id == key_audio_id_original:
                    print("\nDecrypting audio...")
                    print ("Using KEY: " + key)
                    wvdecrypt_process = subprocess.Popen([pmnp_cfg.MP4DECRYPT, "--show-progress", "--key", key, inputAudio, outputAudioTemp])
                    stdoutdata, stderrdata = wvdecrypt_process.communicate()
                    wvdecrypt_process.wait()
                    time.sleep (50.0/1000.0)
                    os.remove(inputAudio)
                    print("\nDemuxing audio...")
                    mediainfo = MediaInfo.parse(outputAudioTemp)
                    audio_info = next(x for x in mediainfo.tracks if x.track_type == "Audio")
                    codec_name = audio_info.format

                    ext = ''
                    if codec_name == "AAC":
                        ext = '.m4a'
                    elif codec_name == "E-AC-3":
                        ext = ".eac3"
                    elif codec_name == "AC-3":
                        ext = ".ac3"
                    outputAudio = outputAudioTemp.replace("_dec.mp4", ext)
                    print("{} -> {}".format(outputAudioTemp, outputAudio))
                    ff = ffmpy.FFmpeg(executable=pmnp_cfg.FFMPEG, inputs={outputAudioTemp: None}, outputs={outputAudio: '-c copy'}, global_options="-y -hide_banner -loglevel warning")
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
                    wvdecrypt_process = subprocess.Popen([pmnp_cfg.MP4DECRYPT, '--show-progress', '--key', key, inputVideo, outputVideoTemp])
                    stdoutdata, stderrdata = wvdecrypt_process.communicate()
                    wvdecrypt_process.wait()
                    print('\nRemuxing video...')
                    ff = ffmpy.FFmpeg(executable=pmnp_cfg.FFMPEG, inputs={outputVideoTemp: None}, outputs={outputVideo: '-c copy'}, global_options='-y -hide_banner -loglevel warning')
                    ff.run()
                    time.sleep(0.05)
                    os.remove(outputVideoTemp)
                    print('Done!')
                    return True

        elif key_video_id_original == 'nothing':
            return True

        def DemuxAudio(inputAudio):
            if os.path.isfile(inputAudio):
                print('\nDemuxing audio...')
                mediainfo = mediainfo_(inputAudio)
                for m in mediainfo['media']['track']:
                    if m['@type'] == 'Audio':
                        codec_name = m['Format']
                        try:
                            codec_tag_string = m['Format_Commercial_IfAny']
                        except Exception:
                            codec_tag_string = ''

                ext = ''
                if codec_name == 'AAC':
                    ext = '.m4a'
                else:
                    if codec_name == 'E-AC-3':
                        ext = '.eac3'
                    else:
                        if codec_name == 'AC-3':
                            ext = '.ac3'
                outputAudio = inputAudio.replace('.mp4', ext)
                print('{} -> {}'.format(inputAudio, outputAudio))
                ff = ffmpy.FFmpeg(executable=pmnp_cfg.FFMPEG,
                  inputs={inputAudio: None},
                  outputs={outputAudio: '-c copy'},
                  global_options='-y -hide_banner -loglevel warning')
                ff.run()
                time.sleep(0.05)
                os.remove(inputAudio)
                print('Done!')

    get_content_info()
