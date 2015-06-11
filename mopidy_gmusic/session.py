from __future__ import unicode_literals

import logging

from gmusicapi import CallFailure, Mobileclient, Webclient

logger = logging.getLogger(__name__)


class GMusicSession(object):

    def __init__(self):
        super(GMusicSession, self).__init__()
        logger.info('Mopidy uses Google Music')
        self.api = Mobileclient()

    def login(self, username, password, deviceid):
        if self.api.is_authenticated():
            self.api.logout()

        if not self.api.login(username, password):
            logger.error(u'Failed to login as "%s"', username)

        if self.api.is_authenticated():
            if deviceid is None:
                self.deviceid = self.get_deviceid(username, password)
            else:
                self.deviceid = deviceid
        else:
            return False

    def logout(self):
        if self.api.is_authenticated():
            return self.api.logout()
        else:
            return True

    def get_all_songs(self):
        if self.api.is_authenticated():
            return self.api.get_all_songs()
        else:
            return {}

    def get_stream_url(self, song_id):
        if self.api.is_authenticated():
            try:
                return self.api.get_stream_url(song_id, self.deviceid)
            except CallFailure as error:
                logger.error(u'Failed to lookup "%s": %s', song_id, error)

    def get_all_user_playlist_contents(self):
        if self.api.is_authenticated():
            return self.api.get_all_user_playlist_contents()
        else:
            return {}

    def get_shared_playlist_contents(self, shareToken):
        if self.api.is_authenticated():
            return self.api.get_shared_playlist_contents(shareToken)
        else:
            return {}

    def get_all_playlists(self):
        if self.api.is_authenticated():
            return self.api.get_all_playlists()
        else:
            return {}

    def get_promoted_songs(self):
        if self.api.is_authenticated():
            return self.api.get_promoted_songs()
        else:
            return {}

    def get_deviceid(self, username, password):
        logger.warning(u'No mobile device ID configured. '
                       u'Trying to detect one.')
        webapi = Webclient(validate=False)
        webapi.login(username, password)
        devices = webapi.get_registered_devices()
        deviceid = None
        for device in devices:
            if device['type'] == 'PHONE' and device['id'][0:2] == u'0x':
                # Omit the '0x' prefix
                deviceid = device['id'][2:]
                break
        webapi.logout()
        if deviceid is None:
            logger.error(u'No valid mobile device ID found. '
                         u'Playing songs will not work.')
        else:
            logger.info(u'Using mobile device ID %s', deviceid)
        return deviceid

    def get_track_info(self, store_track_id):
        if self.api.is_authenticated():
            try:
                return self.api.get_track_info(store_track_id)
            except CallFailure as error:
                logger.error(u'Failed to get All Access track info: %s', error)

    def get_album_info(self, albumid, include_tracks=True):
        if self.api.is_authenticated():
            try:
                return self.api.get_album_info(albumid, include_tracks)
            except CallFailure as error:
                logger.error(u'Failed to get All Access album info: %s', error)

    def get_artist_info(
            self, artistid, include_albums=True, max_top_tracks=5,
            max_rel_artist=5):
        if self.api.is_authenticated():
            try:
                return self.api.get_artist_info(
                    artistid, include_albums, max_top_tracks, max_rel_artist)
            except CallFailure as error:
                logger.error(
                    u'Failed to get All Access artist info: %s', error)

    def search_all_access(self, query, max_results=50):
        if self.api.is_authenticated():
            try:
                return self.api.search_all_access(query, max_results)
            except CallFailure as error:
                logger.error(u'Failed to search All Access: %s', error)

    def get_all_stations(self):
        if self.api.is_authenticated():
            return self.api.get_all_stations()
        else:
            return []

    def get_radio_stations(self, num_stations=0):
        stations = self.get_all_stations()
        # last plaid radio first
        stations.reverse()
        # add IFL radio on top
        stations.insert(0, {'id': 'IFL', 'name': 'I\'m Feeling Lucky'})
        if num_stations > 0:
            # limit radio stations
            stations = stations[:num_stations]
        return stations

    def get_station_tracks(self, station_id, num_tracks=25):
        if self.api.is_authenticated():
            return self.api.get_station_tracks(station_id, num_tracks)
        else:
            return {}

    def increment_song_playcount(self, song_id, plays=1, playtime=None):
        if self.api.is_authenticated():
            return self.api.increment_song_playcount(song_id, plays, playtime)
