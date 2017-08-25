"""Now Playing app in kivy."""
import base64
import io
import logging
import logging.handlers
import os
import shutil
import threading
import time
import xml.etree.ElementTree as ET
from collections import defaultdict

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

album_art_changed = False
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
logger_fh = logging.handlers.RotatingFileHandler('nowplaying.log',
                                                 maxBytes=1048576,
                                                 backupCount=7)
logger_fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
logger_ch = logging.StreamHandler()
logger_ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
logger_formatter = logging.Formatter('%(asctime)s'
                                     + ' %(levelname)s'
                                     + ' %(name)s[%(process)d]'
                                     + ' %(message)s')
logger_fh.setFormatter(logger_formatter)
logger_ch.setFormatter(logger_formatter)
# add the handlers to the logger
logger.addHandler(logger_fh)
logger.addHandler(logger_ch)


class NowPlayingLabel(Label):
    """docstring for NowPlayingLabel."""
    pass


class NowPlaying(BoxLayout):
    """docstring for NowPlaying."""

    stop = threading.Event()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.album = NowPlayingLabel(text='Album', color=[1, 0, 0, ])
        self.title = NowPlayingLabel(text='Title',  color=[0, 1, 0, ])
        self.artist = NowPlayingLabel(text='Artist', color=[0, 0, 1, ])
        self.add_widget(self.title)
        self.add_widget(self.artist)
        self.add_widget(self.album)

    def ascii_integers_to_string(self, string, base=16, digits_per_char=2):
        return "".join([chr(int(string[i:i + digits_per_char],
                                base=base)) for i in
                        range(0, len(string), digits_per_char)])

    def start_update(self):
        threading.Thread(target=self.update).start()

    def update(self):
        global album_art_changed
        codes_we_care_about = ['asal', 'asar', 'minm', 'PICT']
        temp_line = ""
        with open('/tmp/shairport-sync-metadata') as f:
            for line in f:
                if not line.strip().endswith("</item>"):
                    temp_line += line.strip()
                    continue
                line = temp_line + line
                temp_line = ""
                logger.debug('New item: %s', line)
                try:
                    logger.debug(line)
                    root = ET.fromstring(line)
                except ET.ParseError:
                    logger.exception(line)
                else:
                    meta_data = {}
                    for i in root.iter():
                        if i.tag in ['type', 'code']:
                            meta_data[i.tag] = self.ascii_integers_to_string(
                                i.text)
                        elif i.tag == 'data':
                            meta_data[i.tag] = base64.b64decode(i.text)

                    if meta_data['code'] in ['asal', 'asar', 'minm']:
                        meta_data['data'] = meta_data['data'].decode('utf-8')

                    if meta_data['code'] == 'asal':
                        self.album.text = meta_data['data']
                    elif meta_data['code'] == 'asar':
                        self.artist.text = meta_data['data']
                    elif meta_data['code'] == 'minm':
                        self.title.text = meta_data['data']
                    elif (meta_data['code'] == 'PICT') and 'data' in meta_data:
                        album_art_changed = True
                        shutil.copy2('no_album_art.jpg', 'now_playing.jpg')
                        with open('now_playing.jpg', 'wb') as f:
                            f.write(meta_data['data'])
                            album_art_changed = True

                    logger.info('New track playing: %s %s %s', self.title.text,
                                self.artist.text, self.album.text)


class NowPlayingBox(BoxLayout):
    """docstring for NowPlayingBox."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info('Starting up.')
        self.nowplaying = NowPlaying()
        self.albumart = Image(source='now_playing.jpg',
                              allow_stretch=True)
        self.add_widget(self.nowplaying)
        self.add_widget(self.albumart)

    def update(self, dt):
        global album_art_changed
        if album_art_changed:
            self.albumart.reload()
            album_art_changed = False


class NowPlayingApp(App):
    """docstring for NowPlayingApp."""

    def on_start(self):
        shutil.copy2('no_album_art.jpg', 'now_playing.jpg')

    def build(self):
        global album_art_changed
        album_art_changed = False
        npb = NowPlayingBox()
        npb.nowplaying.start_update()
        Clock.schedule_interval(npb.update, 2)
        return npb


if __name__ == '__main__':
    NowPlayingApp().run()
