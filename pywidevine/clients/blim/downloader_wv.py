import threading, isodate
import requests
import math

from requests.sessions import session
from tqdm import tqdm
from queue import Queue

dlthreads = 24

class WvDownloader(object):
    def __init__(self, config):
        self.mpd = config.mpd
        self.output_file = config.output_file
        self.mimetype = config.file_type
        self.formatId = config.format_id
        self.config = config

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
        segment_template = self.get_segment_template()
        return self.get_segments(segment_template)

    def get_segments(self, segment_template):
        urls = []
        urls.append(self.config.base_url + segment_template['@initialization'].replace('$RepresentationID$', self.config.format_id))
        print(urls)
        try:
            current_number = int(segment_template.get("@startNumber", 0))
            period_duration = self.get_duration()
            segment_duration = int(segment_template["@duration"]) / int(segment_template["@timescale"])
            total_segments = math.ceil(period_duration / segment_duration)
            for _ in range(current_number, current_number + total_segments):
                urls.append(self.config.base_url + self.process_url_templace(segment_template['@media'], 
                            representation_id=self.config.format_id,
                            bandwidth=None, time="0", number=str(current_number)))
                current_number += 1
        except KeyError:
            current_number = 0
            current_time = 0
            for seg in segment_template["SegmentTimeline"]["S"]:
                if '@t' in seg:
                    current_time = seg['@t']
                for i in range(int(seg.get('@r', 0)) + 1):
                    urls.append(self.config.base_url + self.process_url_templace(segment_template['@media'], 
                                representation_id=self.config.format_id,
                                bandwidth=None, time=str(current_time), number=str(current_number)))
                    current_number += 1
                    current_time += seg['@d']
        return urls

    def get_duration(self):
        media_duration = self.mpd["MPD"]["@mediaPresentationDuration"]
        return isodate.parse_duration(media_duration).total_seconds()

    def get_segment_template(self):
        tracks = self.mpd['MPD']['Period']['AdaptationSet']

        segment_template = []
        if self.mimetype == "video/mp4":
            for video_track in tracks:
                if video_track["@mimeType"] == self.mimetype:
                    for v in video_track["Representation"]:
                        segment_template = v["SegmentTemplate"]
        
        if self.mimetype == "audio/mp4":
            for audio_track in tracks:
                if audio_track["@mimeType"] == self.mimetype:
                    try:
                        segment_template = audio_track["SegmentTemplate"]
                    except (KeyError, TypeError):
                        for a in self.list_representation(audio_track):
                            segment_template = a["SegmentTemplate"]

        return segment_template

    def list_representation(self, x):
        if isinstance(x['Representation'], list):
            X = x['Representation']
        else:
            X = [x['Representation']]
        return X

    def run(self):
        urls = self.generate_segments()
        work_q = Queue()
        result_q = Queue()

        print('\n' + self.output_file) 
        pool = [WorkerThread(work_q=work_q, result_q=result_q) for i in range(dlthreads)]
        for thread in pool:
            thread.start()

        work_count = 0
        for seg_url in urls:
            work_q.put((work_count, seg_url))
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

    def DownloadSegment(self, url):
        resp = self.session.get(url, stream=True)
        resp.raw.decode_content = True
        data = resp.raw.read()
        return data

class WorkerThread(threading.Thread):
    def __init__(self, work_q, result_q):
        super(WorkerThread, self).__init__()
        self.work_q = work_q
        self.result_q = result_q
        self.stoprequest = threading.Event()
        self.downloader = Downloader()

    def run(self):
        while not self.stoprequest.isSet():
            try:
                (seq, url) = self.work_q.get(True, 0.05)
                self.result_q.put((seq, self.downloader.DownloadSegment(url)))
            except:
                continue

    def join(self, timeout=None):
        self.stoprequest.set()
        super(WorkerThread, self).join(timeout)
