from __future__ import unicode_literals

import logging

from mopidy import backend
from mopidy.models import Playlist

from .session import GMusicSession

logger = logging.getLogger(__name__)


class GMusicPlaylistsProvider(backend.PlaylistsProvider):

    def _create_track(self, api_track):
        track_id = GMusicSession.get_track_id(api_track)
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

        self.playlists = playlists
        backend.BackendListener.send('playlists_loaded')

    def save(self, playlist):
        pass  # TODO
