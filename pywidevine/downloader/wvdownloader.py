
import threading
import os
import requests
import math
import shutil
import pathlib, sys, subprocess

from requests.sessions import session
from tqdm import tqdm
from queue import Queue

dlthreads = 24

class WvDownloader(object):
    def __init__(self, config):
        self.xml = config.xml
        self.output_file = config.output_file
        self.tqdm_mode = config.tqdm_mode
        self.cookies = config.cookies
        self.config = config

    def download_track(self, aria_input, file_name):
        aria_command = ['aria2c', '-i', aria_input,
         '--enable-color=false',
         '--allow-overwrite=true',
         '--summary-interval=0',
         '--download-result=hide',
         '--async-dns=false',
         '--check-certificate=false',
         '--auto-file-renaming=false',
         '--file-allocation=none',
         '--console-log-level=warn',
         '-x16', '-j16', '-s16']
        if sys.version_info >= (3, 5):
            aria_out = subprocess.run(aria_command)
            aria_out.check_returncode()
                
        source_files = pathlib.Path(temp_folder).rglob(r'./*.mp4')
        with open(file_name, mode='wb') as (destination):
            for file in source_files:
                with open(file, mode='rb') as (source):
                    shutil.copyfileobj(source, destination)
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
        os.remove(aria_input)
        print('\nDone!')

    def process_url_templace(self, template, representation_id, bandwidth, time, number):
        if representation_id is not None: result = template.replace('$RepresentationID$', representation_id)
        if number is not None:
            nstart = result.find('$Number')
            if nstart >= 0:
                nend = result.find('$', nstart+1)
                if nend >= 0:
                    var = result[nstart+1 : nend]
                    if 'Number%' in var:
                        value = var[6:] % (int(number))
                    else:
                        value = number
                    result = result.replace('$'+var+'$', value)
        if bandwidth is not None:         result = result.replace('$Bandwidth$', bandwidth)
        if time is not None:              result = result.replace('$Time$', time)
        result = result.replace('$$', '$').replace('../', '')
        return result

    def generate_segments(self):
        segs = self.get_representation_number()
        return self.get_segments(segs)

    def get_segments(self, segment_level):
        media = segment_level['@media']
        current_number = 1
        current_time = 0
        for seg in self.force_segment_level(segment_level):
            if '@t' in seg:
                current_time = seg['@t']
            for _ in range(int(seg.get('@r', 0)) + 1):
                url = self.process_url_templace(media, representation_id=self.config.format_id, bandwidth=self.config.bandwidth, time=str(current_time), number=str(current_number))
                current_number += 1
                current_time += int(seg['@d'])
                yield url

    def force_segment_level(self, segment_level):
        if isinstance(segment_level['SegmentTimeline']['S'], list):
            segment_level = segment_level['SegmentTimeline']['S']
        else:
            segment_level = [segment_level['SegmentTimeline']['S']]
        return segment_level

    def get_representation_number(self):
        x = []
        for [idx, item] in enumerate(self.xml['MPD']['Period']['AdaptationSet']):
            try:
                if self.config.file_type in item.get('@mimeType'):
                    x = idx
            except TypeError:
                if self.config.file_type in item.get('@contentType'):
                    x = idx

        y = []
        if 'video' in self.config.file_type: 
            for [number, rep] in enumerate(self.xml['MPD']['Period']['AdaptationSet'][x]['Representation']):
                if self.config.format_id == rep.get('@id'):
                    y = number

        mpd = self.xml['MPD']['Period']
        try:
            segment_level = mpd['AdaptationSet'][x]['SegmentTemplate']
        except TypeError:
            segment_level = mpd['AdaptationSet'][x]['SegmentTemplate']

        return segment_level
    
    def run(self):
        segment_list = self.generate_segments()
        urls = []
        for seg_url in segment_list:
            url = self.config.base_url + '/' + seg_url
            urls.append(url)

        print('\n' + self.output_file) 
        # download por aria2c
        if not self.tqdm_mode:
            global temp_folder
            aria2c_infile = 'aria2c_infile.txt'
            if os.path.isfile(aria2c_infile): 
                os.remove(aria2c_infile)
            temp_folder = self.output_file.replace('.mp4', '')
            if os.path.exists(temp_folder): 
                shutil.rmtree(temp_folder)
            if not os.path.exists(temp_folder):
                os.makedirs(temp_folder)

            if len(urls) > 1:
                num_segments = int(math.log10(len(urls))) + 1
            with open(aria2c_infile, 'a', encoding='utf8') as (file):
                for (i, url) in enumerate(urls):
                    file.write(f'{url}\n')
                    file.write(f'\tout={temp_folder}.{i:0{num_segments}d}.mp4\n')
                    file.write(f'\tdir={temp_folder}\n')
                    file.flush()
            self.download_track(aria2c_infile, self.output_file)
        else:
            # download por thread
            work_q = Queue()
            result_q = Queue()

            pool = [WorkerThread(work_q=work_q, result_q=result_q, cookies=self.cookies) for i in range(dlthreads)]
            for thread in pool:
                thread.start()

            work_count = 0
            for seg_url in urls:
                url = seg_url
                work_q.put((work_count, url, self.cookies))
                work_count += 1
            results = []
            
            for _ in tqdm(range(work_count)):
                results.append(result_q.get())
            outfile = open(self.output_file , 'wb+')
            sortedr = sorted(results, key=lambda v: v[0])
            for r in sortedr:
                outfile.write(r[1])
            outfile.close()
            del results
            print('Done!')

class Downloader:
    def __init__(self):
        self.session = requests.Session()

    def DownloadSegment(self, url, cookies):
        resp = self.session.get(url, cookies=cookies, stream=True)
        resp.raw.decode_content = True
        data = resp.raw.read()
        return data

class WorkerThread(threading.Thread):
    def __init__(self, work_q, result_q, cookies):
        super(WorkerThread, self).__init__()
        self.work_q = work_q
        self.result_q = result_q
        self.cookies = cookies
        self.stoprequest = threading.Event()
        self.downloader = Downloader()

    def run(self):
        while not self.stoprequest.isSet():
            try:
                (seq, url, cookies) = self.work_q.get(True, 0.05)
                self.result_q.put((seq, self.downloader.DownloadSegment(url, cookies)))
            except:
                continue

    def join(self, timeout=None):
        self.stoprequest.set()
        super(WorkerThread, self).join(timeout)
