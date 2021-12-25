
class WvDownloaderConfig(object):
    def __init__(self, xml, base_url, output_file, track_id, format_id, file_type):
        self.xml = xml
        self.base_url = base_url
        self.output_file = output_file
        self.track_id = track_id
        self.format_id = format_id
        self.file_type = file_type