# -*- coding: utf-8 -*-
# Module: Blim Downloader
# Created on: 26-11-2020
# Authors: JUNi
# Version: 3.5

import requests
import subprocess
import xmltodict
import ffmpy
import time, shutil
import glob, json
import sys, os, re
import isodate
import oauthlib
from oauthlib import oauth1
from subprocess import Popen
from titlecase import titlecase
from unidecode import unidecode
from pymediainfo import MediaInfo
from os.path import isfile, join

import pywidevine.clients.blim.manifest_parse as manifestParse
import pywidevine.clients.blim.client as blim_client
import pywidevine.clients.blim.config as blim_cfg
from pywidevine.clients.proxy_config import ProxyConfig
from pywidevine.muxer.muxer import Muxer

from pywidevine.clients.blim.downloader_pr import PrDownloader
from pywidevine.clients.blim.downloader_wv import WvDownloader
from pywidevine.clients.blim.config import PrDownloaderConfig
from pywidevine.clients.blim.config import WvDownloaderConfig

currentFile = 'blimtv'
realPath = os.path.realpath(currentFile)
dirPath = os.path.dirname(realPath)

def main(args):

    SubtitleEditexe = shutil.which("subtitleedit") or shutil.which("SubtitleEdit")

    proxies = {}
    proxy_meta = args.proxy
    if proxy_meta == 'none':
        proxies['meta'] = {'http': None, 'https': None}
    elif proxy_meta:
        proxies['meta'] = {'http': proxy_meta, 'https': proxy_meta}
    SESSION = requests.Session()
    SESSION.proxies = proxies.get('meta')
    proxy_cfg = ProxyConfig(proxies)

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

    def getKeyId(name):
        mp4dump = subprocess.Popen([blim_cfg.MP4DUMP, name], stdout=(subprocess.PIPE))
        mp4dump = str(mp4dump.stdout.read())
        A = find_str(mp4dump, 'default_KID')
        KEY_ID_ORI = ''
        KEY_ID_ORI = mp4dump[A:A + 63].replace('default_KID = ', '').replace('[', '').replace(']', '').replace(' ', '')
        if KEY_ID_ORI == '' or KEY_ID_ORI == "'":
            KEY_ID_ORI = 'nothing'
        return KEY_ID_ORI

    def replace_words(x):
        x = re.sub(r'[]¡!"#$%\'()*+,:;<=>¿?@\\^_`{|}~[-]', '', x)
        return unidecode(x)
        
    def downloadFile2(link, file_name):
        with open(file_name, 'wb') as (f):
            print('\nDownloading %s' % file_name)
            response = requests.get(link, stream=True)
            total_length = response.headers.get('content-length')
            if total_length is None:
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    done = int(50 * dl / total_length)
                    sys.stdout.write('\r[%s%s]' % ('=' * done, ' ' * (50 - done)))
                    sys.stdout.flush()
        
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

    def manifest_parse(manifest_url):
        r = SESSION.get(url=manifest_url)
        r.raise_for_status()
        xml = xmltodict.parse(r.text)
        manifest = json.loads(json.dumps(xml))
        if '.mpd' in manifest_url:
            length, video_list, audio_list, subs_list = manifestParse.get_mpd_list(manifest)
            base_url = manifest['MPD']['Period']['BaseURL']
        else:
            length, video_list, audio_list, subs_list = manifestParse.get_ism_list(manifest)
            base_url = manifest_url.split('Manifest')[0]

        video_list = sorted(video_list, key=(lambda k: int(k['Bandwidth'])))
        height_all = []
        for x in video_list:
            height_all.append(x['Height'])

        try:
            while args.customquality != [] and int(video_list[(-1)]['Height']) > int(args.customquality[0]):
                video_list.pop(-1)
        except Exception:
            video_list = []

        if video_list == []:
            video_list = video_list
            args.novideo = True

        audio_list = sorted(audio_list, key=(lambda k: (int(k['Bandwidth']), str(k['Language']))), reverse=True)
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
                        'ID':x['ID'],
                        'Codec': x['Codec']}
                    audioList_new.append(audio_Dict_new)
                    counter = counter + 1

        audioList = audioList_new
        audio_list = sorted(audioList, key=(lambda k: (int(k['Bandwidth']), str(k['Language']))))

        subs_list = []
        subsList_new = []
        if args.sublang:
            for x in subs_list:
                langAbbrev = x['Language']
                if langAbbrev in list(args.sublang):
                    subsList_new.append(x)
            subs_list = subsList_new

        return base_url, length, video_list, audio_list, subs_list, manifest

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

    tokenIsOk = False
    os.makedirs(blim_cfg.COOKIES_FOLDER, exist_ok=True)
    BLIMLOGINDATA_FILE = join(blim_cfg.COOKIES_FOLDER, 'blim_login_data.json')
    SESSION, costumer_key, access_key_secret = blim_client.login(SESSION)

    def get_auth_header(api_url):
        client = oauthlib.oauth1.Client(costumer_key, client_secret=access_key_secret)
        uri, auth_header, body = client.sign(api_url)
        return auth_header

    def get_season(blim_id):
        season_req = requests.get(url=blim_cfg.ENDPOINTS['seasons'] + str(blim_id)).json()['data']

        if 'episode' in season_req['category'] and args.season:
            blim_id = season_req['parentShow']['id']
            season_req = requests.get(url=blim_cfg.ENDPOINTS['seasons'] + str(blim_id)).json()['data']

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

        if 'series' in season_req['category']:
            if seasons == 'all':
                seasons = [x['number'] for x in season_req['seasons']]

            for season_num in seasons:
                episode_list = season_req['seasons'][int(season_num) - 1]['episodes']
                episodes_list_new = []
                for num, ep in enumerate(episode_list, start=1):
                    episodes_list_new.insert(num - 0, {
                        'id': ep['id'],
                        'episode_num': num
                    })
                    episode_list = sorted(episodes_list_new, key=lambda x: x['episode_num'])

                if args.episodeStart:
                    eps = get_episodes(args.episodeStart, len(episode_list))
                    episode_list = [x for x in episode_list if x['episode_num'] in eps]

                for episode in episode_list:
                    get_metadata(blim_id=episode['id'])

        else:
            get_metadata(blim_id)

    def get_metadata(blim_id):
        content_url = blim_cfg.ENDPOINTS['content'] + str(blim_id)
        info_json = requests.get(url=content_url, headers=get_auth_header(content_url), proxies=proxy_cfg.get_proxy('meta')).json()
        if 'episode' in info_json['data']['category']:
            blimType = "show"
            seriesTitles = info_json['data']['parentShow']['titleEditorial']
            seasonNumber = info_json['data']['parentSeason']['number']
            episodeNumber = info_json['data']['episodeNumber']
            episodeTitle = info_json['data']['titleEditorial']

        if 'movie' in info_json['data']['category']:
            blimType = "movie"
            seriesTitles = info_json['data']['titleEditorial']
            releaseYearSearch = info_json['data']['airDate']
            releaseYear = re.search(r"^[0-9]{4}", releaseYearSearch)

        if blimType=="movie":
            seriesName = replace_words(seriesTitles) + ' (' + releaseYear.group() + ')'
            folderName = None

        if blimType=="show":
            seriesName = f'{replace_words(seriesTitles)} S{seasonNumber:02}E{episodeNumber:02} - {replace_words(episodeTitle)}'
            folderName = f'{replace_words(seriesTitles)} S{seasonNumber:02}'

        start_process(get_manifest_url(info_json), seriesName, folderName, blimType)

    codec = "mpd" if args.codec == "widevine" else "ss"
        
    def get_manifest_url(api_json):
        video_json = api_json['data']['videos'][0]['files']
        for x in video_json:
            if x['type'] == codec:
                videoURL = x['path'].replace("AVOD.", "")
                if 'ss_629d09c4372f297f2760c820711c4d4737b14f26c25c55e58f1147819005089e' in videoURL or "468842.mpd" in videoURL:
                    print("Lo sentimos, por el momento Blim no está disponible en tu país")
                    sys.exit(0)
                break
        return videoURL

    def get_drm_info(): # não está utilizando
        resp = requests.get(url=blim_cfg.ENDPOINTS['config'], proxies=proxy_cfg.get_proxy('meta')).json()
        wvlic = resp['widevineLicenseServer']
        wvcert = resp['widevineCertificateServer']
        return wvlic, wvcert

    def start_process(manifest_url, seriesName, folderName, blimType):
        base_url, length, video_list, audio_list, subs_list, xml = manifest_parse(manifest_url)
        video_bandwidth = dict(video_list[(-1)])['Bandwidth']
        video_height = str(dict(video_list[(-1)])['Height'])
        video_width = str(dict(video_list[(-1)])['Width'])
        video_codec = str(dict(video_list[(-1)])['Codec'])
        video_format_id = str(dict(video_list[(-1)])['ID'])
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
                    print('SUBTITLE - Profile: Normal - Language: ' + sub_lang)
                print()

        print('Name: ' + seriesName)
        
        if blimType == 'show':
            CurrentName = seriesName
            CurrentHeigh = str(video_height)
            outputName = folderdownloader + '\\' + str(folderName) + str(CurrentName) + ' [' + str(CurrentHeigh) + 'p].mkv'
        else:
            CurrentName = seriesName
            CurrentHeigh = str(video_height)
            outputName = folderdownloader + str(CurrentName) + ' [' + str(CurrentHeigh) + 'p].mkv'

        if 'ism' in manifest_url:
            if video_height == "1080":
                init_url = blim_cfg.init_files["1080p"]
            elif video_height == "480":
                init_url = blim_cfg.init_files["480p"]

        if not os.path.isfile(outputName):

            if not args.novideo:
                inputVideo = seriesName + ' [' + str(CurrentHeigh) + 'p].mp4'
                if os.path.isfile(inputVideo):
                    print('\n' + inputVideo + '\nFile has already been successfully downloaded previously.\n')
                else:
                    if args.codec == 'playready':
                        prdl_cfg = PrDownloaderConfig(xml, base_url, inputVideo, video_bandwidth, init_url, 'video')
                        downloader = PrDownloader(prdl_cfg)
                    else:
                        wvdl_cfg = WvDownloaderConfig(xml, base_url, inputVideo, video_format_id, 'video/mp4')
                        downloader = WvDownloader(wvdl_cfg)
                    downloader.run()

            if not args.noaudio:
                for x in audio_list:
                    audio_lang = x['Language']
                    inputAudio = seriesName + ' ' + '(' + audio_lang + ')' + '.mp4'
                    inputAudio_demuxed = seriesName + ' ' + '(' + audio_lang + ')' + '.m4a'
                    if os.path.isfile(inputAudio) or os.path.isfile(inputAudio_demuxed):
                        print('\n' + inputAudio + '\nFile has already been successfully downloaded previously.\n')
                    else:
                        if args.codec == 'playready':
                            prdl_cfg = PrDownloaderConfig(xml, base_url, inputAudio, x['Bandwidth'], blim_cfg.init_files["audio"], 'audio')
                            downloader = PrDownloader(prdl_cfg)
                        else:
                            wvdl_cfg = WvDownloaderConfig(xml, base_url, inputAudio, x['ID'], 'audio/mp4')
                            downloader = WvDownloader(wvdl_cfg)
                        downloader.run()

            if not args.nosubs:
                if subs_list != []:
                    for z in subs_list:
                        langAbbrev = str(dict(z)['Language'])
                        inputSub = seriesName + " " + "(" + langAbbrev + ")"
                        if os.path.isfile(inputSub + ".vtt") or os.path.isfile(inputSub + ".srt"):
                            print("\n" + inputSub + "\nFile has already been successfully downloaded previously.\n")
                        else:
                            downloadFile2(str(dict(z)['File_URL']), inputSub + ".vtt")
                            print('\nConverting subtitles...')
                            SubtitleEdit_process = subprocess.Popen([SubtitleEditexe, "/convert", inputSub + ".vtt", "srt", "/fixcommonerrors", "/encoding:utf-8", "/RemoveLineBreaks"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
                            for f in glob.glob(inputSub + ".vtt"):
                                os.remove(f)
                            print("Done!")
                else:
                    print ("\nNo subtitles available.")

            CorrectDecryptVideo = False
            if not args.novideo:
                inputVideo = seriesName + ' [' + str(CurrentHeigh) + 'p].mp4'
                if os.path.isfile(inputVideo):
                    CorrectDecryptVideo = DecryptVideo(inputVideo=inputVideo, keys_video=blim_cfg.protection_keys)
                else:
                    CorrectDecryptVideo = True

            CorrectDecryptAudio = False
            if not args.noaudio:
                for x in audio_list:
                    audio_lang = x['Language']
                    inputAudio = seriesName + ' ' + '(' + audio_lang + ')' + '.mp4'
                    if os.path.isfile(inputAudio):
                        CorrectDecryptAudio = DecryptAudio(inputAudio=inputAudio, keys_audio=blim_cfg.protection_keys)
                    else:
                        CorrectDecryptAudio = True

            if not args.nomux:
                if not args.novideo:
                    if not args.noaudio:
                        if CorrectDecryptVideo == True:
                            if CorrectDecryptAudio == True:
                                print('\nMuxing...')

                                if blimType=="show":
                                    MKV_Muxer=Muxer(CurrentName=CurrentName,
                                                    SeasonFolder=folderName,
                                                    CurrentHeigh=CurrentHeigh,
                                                    Type=blimType,
                                                    mkvmergeexe=blim_cfg.MKVMERGE)

                                else:
                                    MKV_Muxer=Muxer(CurrentName=CurrentName,
                                                    SeasonFolder=None,
                                                    CurrentHeigh=CurrentHeigh,
                                                    Type=blimType,
                                                    mkvmergeexe=blim_cfg.MKVMERGE)

                                MKV_Muxer.mkvmerge_muxer(lang="English")

                                if args.tag:
                                    inputName = CurrentName + ' [' + CurrentHeigh + 'p].mkv'
                                    release_group(base_filename=inputName,
                                                  default_filename=CurrentName,
                                                  folder_name=folderName,
                                                  type=blimType,
                                                  video_height=CurrentHeigh)

                                if not args.keep:
                                    for f in os.listdir():
                                        if re.fullmatch(re.escape(CurrentName) + r'.*\.(mp4|m4a|h264|h265|eac3|srt|txt|avs|lwi|mpd)', f):
                                            os.remove(f)
                                print("Done!")
        else:
            print("\nFile '" + str(outputName) + "' already exists.")

    def release_group(base_filename, default_filename, folder_name, type, video_height):
        if type=='show':
            video_mkv = os.path.join(folder_name, base_filename)
        else:
            video_mkv = base_filename

        mediainfo = MediaInfo.parse(video_mkv)
        video_info = next(x for x in mediainfo.tracks if x.track_type == "Video")
        video_format = video_info.format

        video_codec = ''
        if video_format == "AVC":
            video_codec = 'H.264'
        elif video_format == "HEVC":
            video_codec = 'H.265'

        audio_info = next(x for x in mediainfo.tracks if x.track_type == "Audio")
        codec_name = audio_info.format
        channels_number = int(audio_info.other_channel_positions[0].split('/')[0])

        audio_codec = ''
        audio_channels = ''
        if codec_name == "AAC":
            audio_codec = "AAC"
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

        output_name = '{}.{}p.BLIM.WEB-DL.{}.{}-{}'.format(default_filename, video_height, audio_, video_codec, args.tag)
        if type=='show':
            outputName = os.path.join(folder_name, output_name + '.mkv')
        else:
            outputName = output_name + '.mkv'

        os.rename(video_mkv, outputName)
        print("{} -> {}".format(base_filename, output_name))

    def DecryptAudio(inputAudio, keys_audio):
        key_audio_id_original = getKeyId(inputAudio)
        outputAudioTemp = inputAudio.replace(".mp4", "_dec.mp4")
        if key_audio_id_original != "nothing":
            for key in keys_audio:
                key_id=key[0:32]
                if key_id == key_audio_id_original:
                    print("\nDecrypting audio...")
                    print ("Using KEY: " + key)
                    wvdecrypt_process = subprocess.Popen([blim_cfg.MP4DECRYPT, "--show-progress", "--key", key, inputAudio, outputAudioTemp])
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
                    ff = ffmpy.FFmpeg(executable=blim_cfg.FFMPEG, inputs={outputAudioTemp: None}, outputs={outputAudio: '-c copy'}, global_options="-y -hide_banner -loglevel warning")
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
                    wvdecrypt_process = subprocess.Popen([blim_cfg.MP4DECRYPT, '--show-progress', '--key', key, inputVideo, outputVideoTemp])
                    stdoutdata, stderrdata = wvdecrypt_process.communicate()
                    wvdecrypt_process.wait()
                    print('\nRemuxing video...')
                    ff = ffmpy.FFmpeg(executable=blim_cfg.FFMPEG, inputs={outputVideoTemp: None}, outputs={outputVideo: '-c copy'}, global_options='-y -hide_banner -loglevel warning')
                    ff.run()
                    time.sleep(0.05)
                    os.remove(outputVideoTemp)
                    print('Done!')
                    return True

        elif key_video_id_original == 'nothing':
            return True

    def id_parse(x):
        if 'player' in args.url_season:
            id_ = args.url_season.split('/')[-2]
        else:
            id_ = args.url_season.split('/')[-1]
        return id_

    blim_id = id_parse(args.url_season)

    if 'player' in args.url_season:
        get_metadata(blim_id)
    else:
        get_season(blim_id)

