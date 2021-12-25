import threading, isodate
import requests
import math
import urllib.parse

from requests.sessions import session
from tqdm import tqdm
from queue import Queue

dlthreads = 24

class PrDownloader(object):
    def __init__(self, config):
        self.ism = config.ism
        self.output_file = config.output_file
        self.bitrate = config.bitrate
        self.base_url = config.base_url
        self.init_url = config.init_url
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
        quality_level = self.get_quality_level()
        return self.get_segments(quality_level)

    def get_segments(self, stream_index):
        urls = []
        urls.append(self.init_url)
        t = 0
        for seg in stream_index["c"]:
            if '@t' in seg:
                t = seg['@t']
            for i in range(int(seg.get('@r', 0)) + 1):
                path = stream_index['@Url'].format(**{
                     'bitrate': self.bitrate,
                     'start time': t})
                url = urllib.parse.urljoin(self.base_url, path)
                urls.append(url)
                t += int(seg['@d'])
        return urls

    def get_quality_level(self):
        X = [item for (i, item) in enumerate(self.ism['SmoothStreamingMedia']['StreamIndex']) if self.config.file_type in item.get('@Type')][0]
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
