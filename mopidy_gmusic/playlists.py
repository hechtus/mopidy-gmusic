from __future__ import unicode_literals

import logging
import operator

from mopidy import backend
from mopidy.models import Playlist, Ref

logger = logging.getLogger(__name__)


class GMusicPlaylistsProvider(backend.PlaylistsProvider):

    def __init__(self, *args, **kwargs):
        super(GMusicPlaylistsProvider, self).__init__(*args, **kwargs)
        self._radio_stations_as_playlists = (
            self.backend.config['gmusic']['radio_stations_as_playlists'])
        self._radio_stations_count = (
            self.backend.config['gmusic']['radio_stations_count'])
        self._radio_tracks_count = (
            self.backend.config['gmusic']['radio_tracks_count'])
        self._playlists = {}

    def as_list(self):
        refs = [
            Ref.playlist(uri=pl.uri, name=pl.name)
            for pl in self._playlists.values()]
        return sorted(refs, key=operator.attrgetter('name'))

    def get_items(self, uri):
        playlist = self._playlists.get(uri)
        if playlist is None:
            return None
        return [Ref.track(uri=t.uri, name=t.name) for t in playlist.tracks]

    def lookup(self, uri):
        return self._playlists.get(uri)

    def refresh(self):
        playlists = {}

        # We need to grab all the songs for later. All access metadata
        # will be included with the playlist entry, but uploaded music
        # will not.
        library_tracks = {}
        for track in self.backend.session.get_all_songs():
            mopidy_track = self.backend.library._to_mopidy_track(track)
            library_tracks[track['id']] = mopidy_track

        # add "Thumbs up" playlist... It appears that gmusic api's 
        #get_promoted_songs == Thumbs up playlist 
        tracks = []
        for track in self.backend.session.get_promoted_songs():
            tracks.append(self.backend.library._to_mopidy_track(track))

        if len(tracks) > 0:
            uri = 'gmusic:playlist:promoted'
            playlists[uri] = Playlist(uri=uri, name='Thumbs up', tracks=tracks)

        # load user playlists
        for playlist in self.backend.session.get_all_user_playlist_contents():
            tracks = []
            for entry in playlist['tracks']:
                if entry['deleted']:
                    continue

                if entry['source'] == u'1':
                    tracks.append(library_tracks[entry['trackId']])
                else:
                    entry['track']['id'] = entry['trackId']
                    tracks.append(self.backend.library._to_mopidy_track(
                        entry['track']))

            uri = 'gmusic:playlist:' + playlist['id']
            playlists[uri] = Playlist(uri=uri,
                                      name=playlist['name'],
                                      tracks=tracks)

        # load shared playlists
        for playlist in self.backend.session.get_all_playlists():
            if playlist.get('type') == 'SHARED':
                tracks = []
                tracklist = self.backend.session.get_shared_playlist_contents(
                    playlist['shareToken'])
                for entry in tracklist:
                    if entry['source'] == u'1':
                        tracks.append(library_tracks[entry['trackId']])
                    else:
                        entry['track']['id'] = entry['trackId']
                        tracks.append(self.backend.library._to_mopidy_track(
                            entry['track']))

                uri = 'gmusic:playlist:' + playlist['id']
                playlists[uri] = Playlist(uri=uri,
                                          name=playlist['name'],
                                          tracks=tracks)

        l = len(playlists)
        logger.info('Loaded %d playlists from Google Music', len(playlists))

        # load radios as playlists
        if self._radio_stations_as_playlists:
            logger.info('Starting to loading radio stations')
            stations = self.backend.session.get_radio_stations(
                self._radio_stations_count)
            for station in stations:
                tracks = []
                tracklist = self.backend.session.get_station_tracks(
                    station['id'], self._radio_tracks_count)
                for track in tracklist:
                    tracks.append(
                        self.backend.library._to_mopidy_track(track))
                uri = 'gmusic:playlist:' + station['id']
                playlists[uri] = Playlist(uri=uri,
                                          name=station['name'],
                                          tracks=tracks)
            logger.info('Loaded %d radios from Google Music',
                        len(playlists) - l)

        self._playlists = playlists
        backend.BackendListener.send('playlists_loaded')

    def create(self, name):
        raise NotImplementedError

    def delete(self, uri):
        raise NotImplementedError

    def save(self, playlist):
        raise NotImplementedError
