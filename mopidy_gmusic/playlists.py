from __future__ import unicode_literals

import logging

from mopidy import backend
from mopidy.models import Playlist

logger = logging.getLogger(__name__)


class GMusicPlaylistsProvider(backend.PlaylistsProvider):

    def _get_track_id(self, api_track):
        if 'storeId' in api_track:
            return api_track['storeId']
        elif 'trackId' in api_track:
            return api_track['trackId']
        elif 'id' in api_track:
            return api_track['id']
        logger.debug('Skip track: no id %s', str(api_track))
        return None

    def _create_track(self, api_track):
        track_id = self._get_track_id(api_track)
        if track_id:
            return self.backend.library.lookup('gmusic:track:' + track_id)
        else:
            return None

    def _create_playlist_with_tracks(self, tracks, name, id, uri):
        if len(tracks) > 0:
            logger.info('Playlist %s with %d tracks loaded',
                        name, len(tracks))
            return Playlist(uri=uri, name=name, tracks=tracks)
        else:
            logger.debug('Skip empty playlist: %s/%s', id, name)

    def _create_playlist(self, api_tracks, name, id, uri):
        tracks = []
        for api_track in api_tracks:
            track = self._create_track(api_track)
            if track:
                tracks += track
        return self._create_playlist_with_tracks(tracks, name, id, uri)


    def _create_thumbs_up_playlist(self):
        return self._create_playlist(
                            self.backend.session.get_thumbs_up_songs(),
                            'Thumbs up',
                            'thumbs_up',
                            'gmusic:playlist:thumbs_up')

    def _create_playlist_from_station(self, station):
        station_id = station['id']
        station_name = 'radio/ ' + station['name']
        station_uri = 'gmusic:playlist:station-' + station_id
        station_tracks = self.backend.session.get_station_tracks(station_id)
        return self._create_playlist(station_tracks,
                                      station_name,
                                      station_id,
                                      station_uri)

    def _get_all_stations(self):
      playlists = []
      stations = self.backend.session.get_all_stations()
      stations.reverse()
      ifl = {}
      ifl['id'] = 'IFL'
      ifl['name'] = 'I\'m Feeling Lucky'
      stations.insert(0, ifl)
      for station in stations:
          playlist = self._create_playlist_from_station(station)
          if playlist:
              playlists.append(playlist)
          else:
              logger.info('something bad happend: ' + str(playlist))
      return playlists

    def create(self, name):
        pass  # TODO

    def delete(self, uri):
        pass  # TODO

    def lookup(self, uri):
        for playlist in self.playlists:
            if playlist.uri == uri:
                return playlist

    def refresh(self):
        playlists = []

        # add thumbs up playlist
        playlist = self._create_thumbs_up_playlist()
        if playlist:
            playlists.append(playlist)

        for playlist in self.backend.session.get_all_user_playlist_contents():
            tracks = []
            for api_track in playlist['tracks']:
                if not api_track['deleted']:
                    tracks += self._create_track(api_track)
            playlist = self._create_playlist_with_tracks(tracks,
                                            playlist['name'],
                                            playlist['id'],
                                            'gmusic:playlist:' + playlist['id'])
            if playlist:
                playlists.append(playlist)

        for playlist in self.backend.session.get_all_playlists():
            if playlist.get('type') == 'SHARED':
                tracks = []
                tracklist = self.backend.session.get_shared_playlist_contents(
                    playlist['shareToken'])
                for api_track in tracklist:
                    tracks += self._create_track(api_track)
                playlist = self._create_playlist_with_tracks(tracks,
                                                playlist['name'],
                                                playlist['id'],
                                                'gmusic:playlist:' + playlist['id'])

        # add radios stations
        playlists.extend(self._get_all_stations())

        self.playlists = playlists
        backend.BackendListener.send('playlists_loaded')

    def save(self, playlist):
        pass  # TODO
