import requests, pathlib
import math, subprocess
import os, sys, shutil

class WvDownloader(object):
    def __init__(self, config):
        self.xml = config.xml
        self.output_file = config.output_file
        self.config = config

    def download_track(self, aria2c_infile, file_name):
        aria2c_opts = [
                'aria2c',
                '--enable-color=false',
                '--allow-overwrite=true',
                '--summary-interval=0',
                '--download-result=hide',
                '--async-dns=false',
                '--check-certificate=false',
                '--auto-file-renaming=false',
                '--file-allocation=none',
                '--console-log-level=warn',
                '-x16', '-s16', '-j16',
                '-i', aria2c_infile]
        subprocess.run(aria2c_opts, check=True)
                
        source_files = pathlib.Path(temp_folder).rglob(r'./*.mp4')
        with open(file_name, mode='wb') as (destination):
            for file in source_files:
                with open(file, mode='rb') as (source):
                    shutil.copyfileobj(source, destination)
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
        os.remove(aria2c_infile)
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
        segment_template = self.get_segment_template()
        return self.get_segments(segment_template)

    def get_segments(self, segment_template):
        urls = []
        urls.append(self.config.base_url + segment_template['@initialization'].replace('$RepresentationID$', self.config.format_id))
        current_number = 1
        for seg in self.force_segmentimeline(segment_template):
            if '@t' in seg:
                current_time = seg['@t']
            for i in range(int(seg.get('@r', 0)) + 1):
                urls.append(self.config.base_url + self.process_url_templace(segment_template['@media'], 
                            representation_id=self.config.format_id,
                            bandwidth=None, time=str(current_time), number=str(current_number)))
                current_number += 1
                current_time += seg['@d']
        return urls

    def force_segmentimeline(self, segment_timeline):
        if isinstance(segment_timeline['SegmentTimeline']['S'], list):
            x16 = segment_timeline['SegmentTimeline']['S']
        else:
            x16 = [segment_timeline['SegmentTimeline']['S']]
        return x16

    def force_instance(self, x):
        if isinstance(x['Representation'], list):
            X = x['Representation']
        else:
            X = [x['Representation']]
        return X

    def get_segment_template(self):
        x = [item for (i, item) in enumerate(self.xml['MPD']['Period']['AdaptationSet']) if self.config.track_id == item["@id"]][0]
        segment_level = [item['SegmentTemplate'] for (i, item) in enumerate(self.force_instance(x)) if self.config.format_id == item["@id"]][0]
        return segment_level

    def run(self):
        urls = self.generate_segments()

        print('\n' + self.output_file)
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
        print('Done!')
