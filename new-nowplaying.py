"""Now Playing app in kivy."""
import atexit
import base64
import hashlib
import logging
import logging.handlers
import os
import shutil
import threading
import xml.etree.ElementTree as ET

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
logger_ch.setLevel(logging.DEBUG)
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
logger.debug('Logger up and running.')


# pid = str(os.getpid())
# pidfile = "/tmp/healthstats.pid"
# with open(pidfile, 'w') as pf:
#     pf.write(pid)


def cleanup():
    """Cleanup the pid file."""
    # if os.path.isfile(pidfile):
    #     os.unlink(pidfile)
    shutil.copy2('no_album_art.jpg', 'now_playing.jpg')


atexit.register(cleanup)    # Register with atexit


class NowPlayingLabel(Label):
    """docstring for NowPlayingLabel."""
    pass


class NowPlaying(BoxLayout):
    """docstring for NowPlaying."""

    stop = threading.Event()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids.title.text = 'Title'
        self.ids.artist.text = 'Artist'
        self.ids.album.text = 'Album'
        logger.debug('Information screen setup.')

    def ascii_integers_to_string(self, string, base=16, digits_per_char=2):
        return "".join([chr(int(string[i:i + digits_per_char],
                                base=base)) for i in
                        range(0, len(string), digits_per_char)])

    def start_update(self):
        threading.Thread(target=self.update).start()

    def update(self):
        global album_art_changed
        data_line = ''  # full line of metadata
        with open('/tmp/shairport-sync-metadata') as ssmd:
            for read_line in ssmd:
                if read_line.strip().endswith('</item>'):
                    data_line += read_line.strip()
                else:
                    data_line += read_line.strip()
                    continue
                try:
                    md_root = ET.fromstring(data_line)
                except ET.ParseError:
                    print('Got junk data: {0}'.format(data_line))
                else:
                    md_dict = {}
                    for i in md_root.iter():
                        if i.tag in ['type', 'code']:
                            md_dict[i.tag] = self.ascii_integers_to_string(
                                i.text)
                            print('found {0} with {1}'.format(i.tag,
                                                              md_dict[i.tag]))
                        elif i.tag == 'data':
                            md_dict[i.tag] = base64.b64decode(i.text)
                            print('found {0} with {1}'.format(i.tag,
                                                              md_dict[i.tag]))

                    ca_filename = ''  # file name to store cover art locally
                    if md_dict['code'] in ['asal', 'asar', 'minm']:
                        if md_dict['code'] == 'asal':
                            self.ids.album.text = md_dict['data'].decode(
                                'utf-8')
                            print('Album: {0}'.format(self.ids.album.text))
                            ca_filename = hashlib.md5(
                                md_dict['data']).hexdigest() + '.jpg'
                            print('Album art in: {0}'.format(ca_filename))
                        elif md_dict['code'] == 'asar':
                            self.ids.artist.text = md_dict['data'].decode(
                                'utf-8')
                            print('Artist: {0}').format(md_dict['data'])
                        elif md_dict['code'] == 'minm':
                            self.ids.title.text = md_dict['data'].decode(
                                'utf-8')
                            print('Title: {0}').format(md_dict['data'])
                    elif md_dict['code'] == 'PICT':
                        try:
                            shutil.copy2(ca_filename, 'now_playing.jpg')
                            album_art_changed = True
                            print('Found album art.')
                        except Exception as e:
                            print('New album art.')
                            with open(ca_filename, 'wb') as arf:
                                arf.write(md_dict['data'])
                                shutil.copy2(ca_filename, 'now_playing.jpg')
                                album_art_changed = True
                                print('Wrote {0}'.format(ca_filename))

                data_line = ''


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

    def on_stop(self):
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
