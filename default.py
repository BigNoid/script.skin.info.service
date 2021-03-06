import sys
import os
import datetime
import xbmc
import xbmcgui
import xbmcaddon
from Utils import *
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString


TrackTitle = None
AdditionalParams = []
Window = 10000
extrathumb_limit = 4
extrafanart_limit = 10
Addon_Data_Path = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % __addonid__).decode("utf-8"))
Skin_Data_Path = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % xbmc.getSkinDir()).decode("utf-8"))


class Daemon:

    def __init__(self):
        log("version %s started" % __addonversion__)
        self._init_vars()
        self.run_backend()

    def _init_vars(self):
        self.window = xbmcgui.Window(10000)  # Home Window
        self.wnd = xbmcgui.Window(12003)  # Video info dialog
        self.musicvideos = []
        self.movies = []
        self.id = None
        self.dbid = None
        self.type = False
        self.tag = ""
        self.silent = True
        self.prop_prefix = ""
        self.Artist_mbid = None
        self.window.clearProperty('SongToMusicVideo.Path')

    def run_backend(self):
        self._stop = False
        self.previousitem = ""
        self.previousartist = ""
        self.previoussong = ""
        log("starting backend")
        self.musicvideos = create_musicvideo_list()
        self.movies = create_movie_list()
        while (not self._stop) and (not xbmc.abortRequested):
            if xbmc.getCondVisibility("Container.Content(movies) | Container.Content(sets) | Container.Content(artists) | Container.Content(albums) | Container.Content(episodes) | Container.Content(musicvideos)"):
                self.selecteditem = xbmc.getInfoLabel("ListItem.DBID")
                if (self.selecteditem != self.previousitem):
                    self.previousitem = self.selecteditem
                    if self.selecteditem > -1:
                        if xbmc.getCondVisibility("Container.Content(artists)"):
                            self._set_artist_details(self.selecteditem)
                            log("setting movieset labels")
                        elif xbmc.getCondVisibility("Container.Content(albums)"):
                            self._set_album_details(self.selecteditem)
                            log("setting movieset labels")
                        elif xbmc.getCondVisibility("SubString(ListItem.Path,videodb://movies/sets/,left)"):
                            self._set_movieset_details(self.selecteditem)
                        elif xbmc.getCondVisibility("Container.Content(movies)"):
                            self._set_movie_details(self.selecteditem)
                        elif xbmc.getCondVisibility("Container.Content(episodes)"):
                            self._set_episode_details(self.selecteditem)
                        elif xbmc.getCondVisibility("Container.Content(musicvideos)"):
                            self._set_musicvideo_details(self.selecteditem)
                        else:
                            clear_properties()
            elif xbmc.getCondVisibility("Container.Content(years)"):
                self._detail_selector("year")
            elif xbmc.getCondVisibility("Container.Content(genres)"):
                self._detail_selector("genre")
            elif xbmc.getCondVisibility("Container.Content(directors)"):
                self._detail_selector("director")
            elif xbmc.getCondVisibility("Container.Content(actors)"):
                self._detail_selector("cast")
            elif xbmc.getCondVisibility("Container.Content(studios)"):
                self._detail_selector("studio")
            elif xbmc.getCondVisibility("Container.Content(countries)"):
                self._detail_selector("country")
            elif xbmc.getCondVisibility("Container.Content(tags)"):
                self._detail_selector("tag")
            elif xbmc.getCondVisibility('Container.Content(songs)') and self.musicvideos:
                # get artistname and songtitle of the selected item
                self.selecteditem = xbmc.getInfoLabel('ListItem.DBID')
                # check if we've focussed a new song
                if self.selecteditem != self.previousitem:
                    self.previousitem = self.selecteditem
                    # clear the window property
                    self.window.clearProperty('SongToMusicVideo.Path')
                    # iterate through our musicvideos
                    for musicvideo in self.musicvideos:
                        if self.selecteditem == musicvideo[0]:  # needs fixing
                            # match found, set the window property
                            self.window.setProperty('SongToMusicVideo.Path', musicvideo[2])
                            xbmc.sleep(100)
                            # stop iterating
                            break
         #   elif xbmc.getCondVisibility("Window.IsActive(visualisation)"):
            elif False:
                self.selecteditem = xbmc.getInfoLabel('MusicPlayer.Artist')
                if (self.selecteditem != self.previousitem) and self.selecteditem:
                    self.previousitem = self.selecteditem
                    from MusicBrainz import GetMusicBrainzIdFromNet
                    log("Daemon updating SimilarArtists")
                    Artist_mbid = GetMusicBrainzIdFromNet(self.selecteditem)
                    passDataToSkin('SimilarArtistsInLibrary', None, self.prop_prefix)
                    passDataToSkin('SimilarArtists', GetSimilarArtistsInLibrary(Artist_mbid), self.prop_prefix)
                    xbmc.sleep(2000)
            elif xbmc.getCondVisibility('Window.IsActive(screensaver)'):
                xbmc.sleep(1000)
            else:
                self.previousitem = ""
                self.selecteditem = ""
                clear_properties()
                xbmc.sleep(500)
            if xbmc.getCondVisibility("IsEmpty(Window(home).Property(skininfos_daemon_running))"):
                clear_properties()
                self._stop = True
            xbmc.sleep(100)

    def _set_song_details(self, dbid):  # unused, needs fixing
        try:
            b = ""
            a = datetime.datetime.now()
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["artist", "file"], "sort": { "method": "artist" } }, "id": 1}')
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_query = simplejson.loads(json_query)
            clear_properties()
            if "result" in json_query and 'musicvideos' in json_query['result']:
                set_movie_properties(json_query)
            b = datetime.datetime.now() - a
            log('Total time needed to request JSON and set properties for song: %s' % b)
        except Exception as e:
            log(e)

    def _set_artist_details(self, dbid):
        try:
            b = ""
            a = datetime.datetime.now()
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "year", "albumlabel", "playcount", "thumbnail"], "sort": { "method": "label" }, "filter": {"artistid": %s} }, "id": 1}' % dbid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_query = simplejson.loads(json_query)
            clear_properties()
            if 'albums' in json_query['result']:
                set_artist_properties(json_query)
            b = datetime.datetime.now() - a
            log('Total time needed to request JSON and set properties for artist: %s' % b)
        except Exception as e:
            log(e)

    def _set_movie_details(self, dbid):
        try:
            if xbmc.getCondVisibility('Container.Content(movies)') or self.type == "movie":
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["streamdetails","set","setid","cast"], "movieid":%s }, "id": 1}' % dbid)
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                log(json_query)
                json_response = simplejson.loads(json_query)
                if 'moviedetails' in json_response['result']:
                    self._set_properties(json_response)
        except Exception as e:
            log(e)

    def _set_episode_details(self, dbid):
        try:
            if xbmc.getCondVisibility('Container.Content(episodes)') or self.type == "episode":
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"properties": ["streamdetails"], "episodeid":%s }, "id": 1}' % dbid)
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                log(json_query)
                json_response = simplejson.loads(json_query)
                if 'episodedetails' in json_response['result']:
                    self._set_properties(json_response['result']['episodedetails']['streamdetails']['audio'], json_response['result']['episodedetails']['streamdetails']['subtitle'])
        except Exception as e:
            log(e)

    def _set_musicvideo_details(self, dbid):
        try:
            if xbmc.getCondVisibility('Container.Content(musicvideos)') or self.type == "musicvideo":
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideoDetails", "params": {"properties": ["streamdetails"], "musicvideoid":%s }, "id": 1}' % dbid)
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                log(json_query)
                json_response = simplejson.loads(json_query)
                if 'musicvideodetails' in json_response['result']:
                    self._set_properties(json_response['result']['musicvideodetails']['streamdetails']['audio'], json_response['result']['musicvideodetails']['streamdetails']['subtitle'])
        except Exception as e:
            log(e)

    def _set_album_details(self, dbid):
        try:
            b = ""
            a = datetime.datetime.now()
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "track", "duration", "file", "lastplayed", "disc"], "sort": { "method": "label" }, "filter": {"albumid": %s} }, "id": 1}' % dbid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_query = simplejson.loads(json_query)
            clear_properties()
            if "result" in json_query and 'songs' in json_query['result']:
                set_album_properties(json_query)
            b = datetime.datetime.now() - a
            log('Total time needed to request JSON and set properties for album: %s' % b)
        except Exception as e:
            log(e)

    def _set_movieset_details(self, dbid):
        try:
            b = ""
            a = datetime.datetime.now()
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSetDetails", "params": {"setid": %s, "properties": [ "thumbnail" ], "movies": { "properties":  [ "rating", "art", "file", "year", "director", "writer","genre" , "thumbnail", "runtime", "studio", "plotoutline", "plot", "country"], "sort": { "order": "ascending",  "method": "year" }} },"id": 1 }' % dbid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_query = simplejson.loads(json_query)
            clear_properties()
            if "result" in json_query and 'setdetails' in json_query['result']:
                set_movie_properties(json_query)
            b = datetime.datetime.now() - a
            log('Total time needed to request JSON and set properties for set: %s' % b)
        except Exception as e:
            log("Exception in _set_movieset_details:")
            log(e)

    def _detail_selector(self, comparator):
        self.selecteditem = xbmc.getInfoLabel("ListItem.Label")
        if (self.selecteditem != self.previousitem):
            if xbmc.getCondVisibility("!Stringcompare(ListItem.Label,..)"):
                self.previousitem = self.selecteditem
                clear_properties()
                count = 1
                for movie in self.movies["result"]["movies"]:
                    log(comparator)
                    if self.selecteditem in str(movie[comparator]):
                        log(movie)
                        self.window.setProperty('Detail.Movie.%i.Path' % (count), movie["file"])
                        self.window.setProperty('Detail.Movie.%i.Art(fanart)' % (count), movie["art"].get('fanart', ''))
                        self.window.setProperty('Detail.Movie.%i.Art(poster)' % (count), movie["art"].get('poster', ''))
                        count += 1
                    if count > 19:
                        break
            else:
                clear_properties()

    def _set_properties(self, results):
        # Set language properties
        count = 1
        audio = results['result']['moviedetails']['streamdetails']['audio']
        subtitles = results['result']['moviedetails']['streamdetails']['subtitle']
        subs = []
        streams = []
        # Clear properties before setting new ones
        clear_properties()
        for item in audio:
            streams.append(str(item['language']))
            self.wnd.setProperty('AudioLanguage.%d' % count, item['language'])
            self.wnd.setProperty('AudioCodec.%d' % count, item['codec'])
            self.wnd.setProperty('AudioChannels.%d' % count, str(item['channels']))
            count += 1
        count = 1
        for item in subtitles:
            subs.append(str(item['language']))
            self.wnd.setProperty('SubtitleLanguage.%d' % count, item['language'])
            count += 1
        wnd.setProperty('SubtitleLanguage', " / ".join(subs))
        wnd.setProperty('AudioLanguage', " / ".join(streams))
     #   self.cleared = False

if (__name__ == "__main__"):
    try:
        params = dict( arg.split("=") for arg in sys.argv[1].split("&"))
    except:
        params = {}
    if xbmc.getCondVisibility("IsEmpty(Window(home).Property(skininfos_daemon_running))"):
        xbmc.executebuiltin('SetProperty(skininfos_daemon_running,True,home)')
        log("starting daemon")
        Daemon()
    else:
        log("Daemon already active")
log('finished')
