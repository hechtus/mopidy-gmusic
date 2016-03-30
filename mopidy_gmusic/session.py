from __future__ import unicode_literals

import functools
import logging

import gmusicapi

import requests

from service import GMusicService


logger = logging.getLogger(__name__)


def endpoint(default=None, require_all_access=False):
    default = default() if callable(default) else default

    def outer_wrapper(func):

        @functools.wraps(func)
        def inner_wrapper(self, *args, **kwargs):
            if require_all_access and not self.all_access:
                logger.warning(
                    'Google Play Music All Access is required for %s()',
                    func.__name__)
                return default

            if not self.api.is_authenticated():
                return default

            try:
                return func(self, *args, **kwargs)
            except gmusicapi.CallFailure:
                logger.exception('Call to Google Music failed')
                return default
            except requests.exceptions.RequestException:
                logger.exception('HTTP request to Google Music failed')
                return default

        return inner_wrapper

    return outer_wrapper


class GMusicSession(object):

    def __init__(self, all_access, api=None):
        self.all_access = all_access
        if api is None:
            self.api = GMusicService()
        else:
            self.api = api

    def login(self, username, password, device_id):
        if self.api.is_authenticated():
            self.api.logout()

        if device_id is None:
            device_id = self.api.FROM_MAC_ADDRESS

        authenticated = self.api.login(username, password, device_id)

        if authenticated:
            logger.info('Logged in to Google Music')
        else:
            logger.error('Failed to login to Google Music as "%s"', username)
        return authenticated

    @endpoint(default=None)
    def logout(self):
        return self.api.logout()

    @endpoint(default=list)
    def get_all_songs(self):
        return self.api.get_all_songs()

    @endpoint(default=None)
    def get_stream_url(self, song_id, quality='hi'):
        return self.api.get_stream_url(song_id, quality=quality)

    @endpoint(default=list)
    def get_all_playlists(self):
        return self.api.get_all_playlists()

    @endpoint(default=list)
    def get_all_user_playlist_contents(self):
        return self.api.get_all_user_playlist_contents()

    @endpoint(default=list)
    def get_shared_playlist_contents(self, share_token):
        return self.api.get_shared_playlist_contents(share_token)

    @endpoint(default=list)
    def get_promoted_songs(self):
        return self.api.get_promoted_songs()

    @endpoint(default=None, require_all_access=True)
    def get_track_info(self, store_track_id):
        return self.api.get_track_info(store_track_id)

    @endpoint(default=None, require_all_access=True)
    def get_album_info(self, album_id, include_tracks=True):
        return self.api.get_album_info(
            album_id, include_tracks=include_tracks)

    @endpoint(default=None, require_all_access=True)
    def get_artist_info(
            self, artist_id, include_albums=True, max_top_tracks=5,
            max_rel_artist=5):
        return self.api.get_artist_info(
            artist_id,
            include_albums=include_albums,
            max_top_tracks=max_top_tracks,
            max_rel_artist=max_rel_artist)

    @endpoint(default=None, require_all_access=True)
    def search_all_access(self, query, max_results=50, field=None):
        results = self.api.search(query, max_results=max_results)
        if field:
            return self.filter_search_results_by_field(results, field)
        return results

    def filter_search_results_by_field(self, results, field):
        for search_result_type in self.api.SEARCH_RESULT_TYPES:
            if search_result_type != field:
                results['{}_hits'.format(search_result_type)] = []
        return results

    @endpoint(default=list)
    def get_all_stations(self):
        return self.api.get_all_stations()

    def get_radio_stations(self, num_stations=None):
        stations = self.get_all_stations()

        # Last played radio first
        stations.reverse()

        # Add IFL radio on top
        stations.insert(0, {'id': 'IFL', 'name': 'I\'m Feeling Lucky'})

        if num_stations is not None and num_stations > 0:
            # Limit radio stations
            stations = stations[:num_stations]

        return stations

    @endpoint(default=list, require_all_access=True)
    def get_station_tracks(self, station_id, num_tracks=25):
        return self.api.get_station_tracks(
            station_id, num_tracks=num_tracks)

    @endpoint(default=None)
    def increment_song_playcount(self, song_id, plays=1, playtime=None):
        return self.api.increment_song_playcount(
            song_id, plays=plays, playtime=playtime)
