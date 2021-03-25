#!/usr/bin/env python
'''
Copyright 2021 - Albert Montijn (montijnalbert@gmail.com)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

   ---------------------------------------------------------------------------
   Programming is the result of learning from others and making errors.
   A good programmer often follows the tips and tricks of better programmers.
   The solution of a problem seldom leads to new or original code.
   So any resemblance to already existing code is purely coincidental
'''

import os
import json
import random
import datetime
import re
import subprocess
from kodi import Kodi

import logging
log = logging.getLogger(__name__)

class Music:
    def __init__(self, kodi, musicfile):
        self.kodi = kodi
        self.musicfile = musicfile

    def get_albuminfo(self, albumid):
        with open(self.musicfile, "r") as music_file:
            music_json = json.load(music_file)
        log.debug("get_albuminfo: albumid=%s, musicfile=%s"
                 % (albumid, self.musicfile))

        album_info_list = []
        for album_info in music_json["albums"]:
            if album_info["id"] == str(albumid):
                log.debug("album_info (%s) matcht (%s)" % ( str(album_info) , str(albumid)))
                album_info_list.append(album_info)
                break
        log.debug("Gevonden: %s" % str(album_info_list))
        return album_info_list

    def search_albuminfo(self, artist="", album="", genre=""):
        artist_name = artist.lower()
        album_name = album.lower()

        with open(self.musicfile, "r") as music_file:
            music_json = json.load(music_file)
        log.debug("kodiGetAlbums:artist=[%s], album=[%s], genre=[%s], musicfile=[%s]"
                 % (artist_name, album_name, genre, self.musicfile))

        album_info_list = [album_info for album_info in music_json["albums"]
                           if (artist_name == ""
                               or artist_name in album_info["artistsearch"])
                           and (album_name == ""
                                or album_name in album_info["albumsearch"])
                           and (genre == ""
                                or genre in album_info["genre"])
                           ]
        log.debug("Gevonden: %s" % str(album_info_list))
        return album_info_list

    def json_cleanup(self, original):
        cleaned = re.sub('[\'"]', '_', original)
        return cleaned

    def make_artistsearch(self, original):
        cleaned = original.lower()
        # remove special characters
        cleaned = re.sub('&', ' and ', cleaned)
        cleaned = re.sub('[-.\'\][]', ' ', cleaned)

        # remove consecutive spaces to 1 space
        cleaned = re.sub(' +', ' ', cleaned)
        # remove leading and trailing spaces
        cleaned = cleaned.strip()
        return cleaned

    def make_albumsearch(self, original):
        cleaned = original.lower()
        # specials
        cleaned = re.sub('12 x 5', 'twelve times 5', cleaned)
        cleaned = re.sub('20 jahre', 'zwanzig jahre', cleaned)
        cleaned = re.sub('[Oo]p\.', 'opus ', cleaned)
        cleaned = re.sub('[Nn]o[s]*\.', 'nummer ', cleaned)

        # remove special characters
        # cleaned = re.sub('[^0-9a-z ]+', ' ', cleaned)
        cleaned = re.sub('[-.\'():\[\]_,/]', ' ', cleaned)
        # remove combinations of digits + letters
        cleaned = re.sub('[0-9]+[a-z]+', '', cleaned)
        # remove combinations of letters + digits
        cleaned = re.sub('[a-z]+[0-9]+', '', cleaned)
        # remove leading digits and spaces
        cleaned = re.sub('^[0-9 ]+', '', cleaned)
        # remove consecutive spaces to 1 space
        cleaned = re.sub(' +', ' ', cleaned)
        # change last single i (roman 1) to 1
        cleaned = re.sub(' i$', ' 1', cleaned)
        # change last double i (roman 2) to 2
        cleaned = re.sub(' ii$', ' 2', cleaned)
        # change last triple i (roman 3) to 3
        cleaned = re.sub(' iii', ' 3', cleaned)
        # keep only first 5 words:
        cleaned = re.sub(r'((\w+ ){1,4}\w+).*',r'\1',cleaned)
        # remove leading and trailing spaces
        cleaned = cleaned.strip()
        return cleaned

    def refresh_album_info(self, path):
        answer = self.kodi.get_all_albums()
        log.debug(str(answer))
        if answer['result'] is not None:
            albums = answer['result']['albums']
        else:
            albums = {}

        genres = set()
        artists = set()
        albumnames = set()

        fmusic = open(self.musicfile, "w+")
        # separator is added before datastring and changed to ',' in the loop
        separator = '{"albums":['

        for album in albums:
            artist = ""
            artistsearch = ""
            for a in album["artist"]:
                artist = artist + a + " "
                artistsearch = artistsearch + a + ","
            artistsearch = self.make_artistsearch(artist)
            for a in artistsearch.split(','):
                artists.add(a.strip())

            genre = ""
            for g in album["genre"]:
                genre = genre + g + " "
            genres.add(genre)

            albumlabel = self.json_cleanup(album["label"])
            albumsearch = self.make_albumsearch(albumlabel)
            albumnames.add(albumsearch)
            line = '%s{"id":"%s","artist":"%s","album":"%s",'\
                         % (separator, album["albumid"], artist, albumlabel)\
                         + '"genre":"%s","artistsearch":"%s","albumsearch":"%s"}\n'\
                         % (genre, artistsearch, albumsearch)
            log.debug(line)
            fmusic.write(line)
            separator = ','

        fmusic.write(']}')
        fmusic.close()

        NL = '\n'
        fgenres = open(path+"genres", "w+")
        for genre in sorted(genres):
            fgenres.write(genre+NL)
        fgenres.close()

        fartists = open(path+"artists", "w+")
        for artist in sorted(artists):
            fartists.write(artist+NL)
        fartists.close()

        falbums = open(path+"albums", "w+")
        for album in sorted(albumnames):
            falbums.write(album+NL)
        falbums.close()


if __name__ == '__main__':
    logging.basicConfig(filename='kodimusic.log',
                        level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-4.4s:%(module)-10.10s - %(message)s',
                        datefmt='%Y%m%d %H:%M:%S')
    kodi_url = "http://192.168.0.5:8080/jsonrpc"
    # os.chdir("/profiles/nl/handler")
    kodi = Kodi(kodi_url)
    music = Music(kodi, "music")

    music.refresh_album_info("")  # create files in current directory

    # test
    albumlist = music.get_albuminfo("4")
    log.info("album[4]:"+str(albumlist))
    print("album[4]:"+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(artist="pink floyd", album="echoes")
    log.info("pink floyd, echoes:"+str(albumlist))
    print("pink floyd, echoes:"+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(artist="pink floyd")
    log.info("only pink floyd:"+str(albumlist))
    print("only pink floyd:"+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(album="echoes")
    log.info("only echoes:"+str(albumlist))
    print("only echoes:"+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(genre="Jazz")
    print("Jazz:"+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(artist="glenn gould")
    print('artist="glenn gould":'+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(artist="arvo pärt")
    print('artist="arvo pärt"'+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(artist="schubert")
    print('artist="schubert":'+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(artist="bryn terfel")
    print('artist="bryn terfel"'+str(albumlist))
    print("------------------------------------------")
    albumlist = music.search_albuminfo(artist="mozart")
    print('artist="bryn terfel"'+str(albumlist))
    print("------------------------------------------")

