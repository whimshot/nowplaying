"""Now Playing app in kivy."""
import base64
import io
import logging
import logging.handlers
import os
import pprint
import random
import threading
import time
import xml.etree.ElementTree as ET
from collections import defaultdict

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config, ConfigParser
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image, AsyncImage
from kivy.uix.label import Label
from kivy.uix.slider import Slider


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

    def etree_to_dict(self, t):
        """
        Function to modify a xml.etree.ElementTree thingy to be a dict.
        Attributes will be accessible via ["@attribute"],
        and get the text (aka. content) inside via ["#text"]

        TESTED ONLY FOR PYTHON 3! (but should be working in Python 2...)
        :param t:
        :return:
        """
        # THANKS http://stackoverflow.com/a/10077069

        d = {t.tag: {} if t.attrib else None}
        children = list(t)
        if children:
            dd = defaultdict(list)
            for dc in map(self.etree_to_dict, children):
                for k, v in dc.items():
                    dd[k].append(v)
            # .items() is bad for python 2
            d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
        if t.attrib:
            # .items() is bad for python 2
            d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                    d[t.tag]['#text'] = text
            else:
                d[t.tag] = text
        return d

    def start_update(self):
        threading.Thread(target=self.update).start()

    def update(self):
        codes_we_care_about = ['asal', 'asar', 'minm', 'PICT']
        temp_line = ""
        with open('/tmp/shairport-sync-metadata') as f:
            for line in f:
                if not line.strip().endswith("</item>"):
                    temp_line += line.strip()
                    continue
                line = temp_line + line
                temp_line = ""
                root = ET.fromstring(line)
                e = self.etree_to_dict(root)
                code = self.ascii_integers_to_string(e['item']['code'])
                if code in codes_we_care_about:
                    if 'data' in e['item']:
                        data = base64.b64decode(e['item']['data']['#text'])
                        try:
                            if code == 'asal':
                                decoded_data = data.decode('utf-8')
                                self.album.text = decoded_data
                            elif code == 'asar':
                                decoded_data = data.decode('utf-8')
                                self.artist.text = decoded_data
                            elif code == 'minm':
                                decoded_data = data.decode('utf-8')
                                self.title.text = decoded_data
                            elif code == 'PICT':
                                with open('now_playing.jpg', 'wb') as f:
                                    f.write(data)
                                print(f.closed)
                                time.sleep(2)
                        except UnicodeDecodeError as e:
                            raise
                        finally:
                            pass


class NowPlayingBox(BoxLayout):
    """docstring for NowPlayingBox."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nowplaying = NowPlaying()
        self.albumart = Image(source='now_playing.jpg',
                              allow_stretch=True)
        self.add_widget(self.nowplaying)
        self.add_widget(self.albumart)

    def update(self, dt):
        self.albumart.reload()


class NowPlayingApp(App):
    """docstring for NowPlayingApp."""

    def build(self):
        npb = NowPlayingBox()
        npb.nowplaying.start_update()
        Clock.schedule_interval(npb.update, 2)
        return npb


if __name__ == '__main__':
    NowPlayingApp().run()
