from __future__ import unicode_literals

import logging

from cachetools import LRUCache

from mopidy import backend
from mopidy.models import Album, Artist, Ref, SearchResult, Track

from mopidy_gmusic.translator import album_to_ref, artist_to_ref, track_to_ref
from mopidy_gmusic.translator import create_id, get_images

logger = logging.getLogger(__name__)


class GMusicLibraryProvider(backend.LibraryProvider):
    root_directory = Ref.directory(uri='gmusic:directory', name='Google Music')

    def __init__(self, *args, **kwargs):
        super(GMusicLibraryProvider, self).__init__(*args, **kwargs)

        # tracks, albums, and artists here refer to what is explicitly
        # in our library.
        self.tracks = {}
        self.albums = {}
        self.artists = {}

        # aa_* caches are *only* used for temporary objects. Library
        # objects will never make it here.
        self.aa_artists = LRUCache(1024)
        self.aa_tracks = LRUCache(1024)
        self.aa_albums = LRUCache(1024)

        self._radio_stations_in_browse = (
            self.backend.config['gmusic']['radio_stations_in_browse'])
        self._radio_stations_count = (
            self.backend.config['gmusic']['radio_stations_count'])
        self._radio_tracks_count = (
            self.backend.config['gmusic']['radio_tracks_count'])

        self._top_tracks_count = (
            self.backend.config['gmusic']['top_tracks_count'])

        # Setup the root of library browsing.
        self._root = [
            Ref.directory(uri='gmusic:album', name='Albums'),
            Ref.directory(uri='gmusic:artist', name='Artists'),
            Ref.directory(uri='gmusic:track', name='Tracks')
        ]

        if self._radio_stations_in_browse:
            self._root.append(Ref.directory(uri='gmusic:radio',
                                            name='Radios'))

    @property
    def all_access(self):
        return self.backend.session.all_access

    def _browse_tracks(self):
        tracks = list(self.tracks.values())
        tracks.sort(key=lambda ref: ref.name)
        refs = []
        for track in tracks:
            refs.append(track_to_ref(track))
        return refs

    def _browse_albums(self):
        refs = []
        for album in self.albums.values():
            refs.append(album_to_ref(album))
        refs.sort(key=lambda ref: ref.name)
        return refs

    def _browse_album(self, uri):
        refs = []
        for track in self._lookup_album(uri):
            refs.append(track_to_ref(track, True))
        return refs

    def _browse_artists(self):
        refs = []
        for artist in self.artists.values():
            refs.append(artist_to_ref(artist))
        refs.sort(key=lambda ref: ref.name)
        return refs

    def _browse_artist(self, uri):
        refs = []
        for album in self._get_artist_albums(uri):
            refs.append(album_to_ref(album))
            refs.sort(key=lambda ref: ref.name)
        if len(refs) > 0:
            refs.insert(0, Ref.directory(uri=uri + ':all', name='All Tracks'))
            is_all_access = uri.startswith('gmusic:artist:A')
            if is_all_access:
                refs.insert(1, Ref.directory(uri=uri + ':top', name='Top Tracks'))
            return refs
        else:
            # Show all tracks if no album is available
            return self._browse_artist_all_tracks(uri)

    def _browse_artist_all_tracks(self, uri):
        artist_uri = ':'.join(uri.split(':')[:3])
        refs = []
        tracks = self._lookup_artist(artist_uri, True)
        for track in tracks:
            refs.append(track_to_ref(track))
        return refs

    def _browse_artist_top_tracks(self, uri):
        artist_uri = ':'.join(uri.split(':')[:3])
        refs = []
        tracks = self._get_artist_top_tracks(artist_uri)
        for track in tracks:
            refs.append(track_to_ref(track))
        return refs

    def _browse_radio_stations(self, uri):
        stations = self.backend.session.get_radio_stations(
            self._radio_stations_count)
        # create Ref objects
        refs = []
        for station in stations:
            refs.append(Ref.directory(uri='gmusic:radio:' + station['id'],
                                      name=station['name']))
        return refs

    def _browse_radio_station(self, uri):
        station_id = uri.split(':')[2]
        tracks = self.backend.session.get_station_tracks(
            station_id, self._radio_tracks_count)

        # create Ref objects
        refs = []
        for track in tracks:
            mopidy_track = self._to_mopidy_track(track)
            self.aa_tracks[mopidy_track.uri] = mopidy_track
            refs.append(track_to_ref(mopidy_track))
        return refs

    def browse(self, uri):
        logger.debug('browse: %s', str(uri))
        if not uri:
            return []
        if uri == self.root_directory.uri:
            return self._root

        parts = uri.split(':')

        # tracks
        if uri == 'gmusic:track':
            return self._browse_tracks()

        # albums
        if uri == 'gmusic:album':
            return self._browse_albums()

        # a single album
        # uri == 'gmusic:album:album_id'
        if len(parts) == 3 and parts[1] == 'album':
            return self._browse_album(uri)

        # artists
        if uri == 'gmusic:artist':
            return self._browse_artists()

        # a single artist
        # uri == 'gmusic:artist:artist_id'
        if len(parts) == 3 and parts[1] == 'artist':
            return self._browse_artist(uri)

        # all tracks of a single artist
        # uri == 'gmusic:artist:artist_id:all'
        if len(parts) == 4 and parts[1] == 'artist' and parts[3] == 'all':
            return self._browse_artist_all_tracks(uri)

        # top tracks of a single artist
        # uri == 'gmusic:artist:artist_id:top'
        if len(parts) == 4 and parts[1] == 'artist' and parts[3] == 'top':
            return self._browse_artist_top_tracks(uri)

        # all radio stations
        if uri == 'gmusic:radio':
            return self._browse_radio_stations(uri)

        # a single radio station
        # uri == 'gmusic:radio:station_id'
        if len(parts) == 3 and parts[1] == 'radio':
            return self._browse_radio_station(uri)

        logger.debug('Unknown uri for browse request: %s', uri)

        return []

    def lookup(self, uri):
        if uri.startswith('gmusic:track:'):
            return self._lookup_track(uri)
        elif uri.startswith('gmusic:album:'):
            return self._lookup_album(uri)
        elif uri.startswith('gmusic:artist:'):
            return self._lookup_artist(uri)
        else:
            return []

    def _lookup_track(self, uri):
        is_all_access = uri.startswith('gmusic:track:T')

        try:
            return [self.tracks[uri]]
        except KeyError:
            logger.debug('Track not a library track %r', uri)
            pass

        if is_all_access and self.all_access:
            track = self.aa_tracks.get(uri)
            if track:
                return [track]
            song = self.backend.session.get_track_info(uri.split(':')[2])
            if song is None:
                logger.warning('There is no song %r', uri)
                return []
            if 'artistId' not in song:
                logger.warning('Failed to lookup %r', uri)
                return []
            mopidy_track = self._to_mopidy_track(song)
            self.aa_tracks[mopidy_track.uri] = mopidy_track
            return [mopidy_track]
        else:
            return []

    def _lookup_album(self, uri):
        is_all_access = uri.startswith('gmusic:album:B')
        if self.all_access and is_all_access:
            tracks = self.aa_albums.get(uri)
            if tracks:
                return tracks
            album = self.backend.session.get_album_info(
                uri.split(':')[2], include_tracks=True)
            if album and album.get('tracks'):
                tracks = [self._to_mopidy_track(track)
                          for track in album['tracks']]
                for track in tracks:
                    self.aa_tracks[track.uri] = track
                tracks = sorted(tracks, key=lambda t: (t.disc_no, t.track_no))
                self.aa_albums[uri] = tracks
                return tracks

            logger.warning('Failed to lookup all access album %r: %r',
                           uri, album)

        # Even if the album has an all access ID, we need to look it
        # up here (as a fallback) because purchased tracks can have a
        # store ID, but only show up in your library.
        try:
            album = self.albums[uri]
        except KeyError:
            logger.debug('Failed to lookup %r', uri)
            return []

        tracks = self._find_exact(
            dict(album=album.name,
                 artist=[artist.name for artist in album.artists],
                 date=album.date)).tracks
        return sorted(tracks, key=lambda t: (t.disc_no, t.track_no))

    def _get_artist_top_tracks(self, uri):
        is_all_access = uri.startswith('gmusic:artist:A')
        artist_id = uri.split(':')[2]

        if not is_all_access:
            logger.debug("Top Tracks not available for non-all-access artists")
            return []

        artist_info = self.backend.session.get_artist_info(artist_id,
                                                           include_albums=False,
                                                           max_top_tracks=self._top_tracks_count,
                                                           max_rel_artist=0)
        top_tracks = []

        for track_dict in artist_info['topTracks']:
            top_tracks.append(self._to_mopidy_track(track_dict))

        return top_tracks

    def _get_artist_albums(self, uri):
        is_all_access = uri.startswith('gmusic:artist:A')

        artist_id = uri.split(':')[2]
        if is_all_access:
            # all access
            artist_infos = self.backend.session.get_artist_info(
                artist_id, max_top_tracks=0, max_rel_artist=0)
            if artist_infos is None or 'albums' not in artist_infos:
                return []
            albums = []
            for album in artist_infos['albums']:
                albums.append(
                    self._aa_search_album_to_mopidy_album({'album': album}))
            return albums
        elif self.all_access and artist_id in self.aa_artists:
            albums = self._get_artist_albums(
                'gmusic:artist:%s' % self.aa_artists[artist_id])
            if len(albums) > 0:
                return albums
            # else fall back to non aa albums
        if uri in self.artists:
            artist = self.artists[uri]
            return [album for album in self.albums.values()
                    if artist in album.artists]
        else:
            logger.debug('0 albums available for artist %r', uri)
            return []

    def _lookup_artist(self, uri, exact_match=False):
        def sorter(track):
            return (
                track.album.date,
                track.album.name,
                track.disc_no,
                track.track_no,
            )

        if self.all_access:
            try:
                all_access_id = self.aa_artists[uri.split(':')[2]]
                artist_infos = self.backend.session.get_artist_info(
                    all_access_id, max_top_tracks=0, max_rel_artist=0)
                if not artist_infos or not artist_infos['albums']:
                    logger.warning('Failed to lookup %r', artist_infos)
                tracks = [
                    self._lookup_album('gmusic:album:' + album['albumId'])
                    for album in artist_infos['albums']]
                tracks = reduce(lambda a, b: (a + b), tracks)
                return sorted(tracks, key=sorter)
            except KeyError:
                pass
        try:
            artist = self.artists[uri]
        except KeyError:
            logger.debug('Failed to lookup %r', uri)
            return []

        tracks = self._find_exact(
            dict(artist=artist.name)).tracks
        if exact_match:
            tracks = filter(lambda t: artist in t.artists, tracks)
        return sorted(tracks, key=sorter)

    def refresh(self, uri=None):
        self.tracks = {}
        self.albums = {}
        self.artists = {}

        album_tracks = {}
        for track in self.backend.session.get_all_songs():
            mopidy_track = self._to_mopidy_track(track)

            self.tracks[mopidy_track.uri] = mopidy_track
            self.albums[mopidy_track.album.uri] = mopidy_track.album

            # We don't care about the order because we're just using
            # this as a temporary variable to grab the proper album
            # artist out of the album.
            if mopidy_track.album.uri not in album_tracks:
                album_tracks[mopidy_track.album.uri] = []

            album_tracks[mopidy_track.album.uri].append(mopidy_track)

        # Yes, this is awful. No, I don't have a better solution. Yes,
        # I'm annoyed at Google for not providing album artist IDs.
        for album in self.albums.values():
            artist_found = False
            for album_artist in album.artists:
                for track in album_tracks[album.uri]:
                    for artist in track.artists:
                        if album_artist.name == artist.name:
                            artist_found = True
                            self.artists[artist.uri] = artist

            if not artist_found:
                for artist in album.artists:
                    self.artists[artist.uri] = artist

    def search(self, query=None, uris=None, exact=False):
        if exact:
            return self._find_exact(query=query, uris=uris)

        lib_tracks, lib_artists, lib_albums = self._search_library(query, uris)

        if query:
            aa_tracks, aa_artists, aa_albums = self._search(query, uris)
            for aa_artist in aa_artists:
                lib_artists.add(aa_artist)

            for aa_album in aa_albums:
                lib_albums.add(aa_album)

            lib_tracks = set(lib_tracks)

            for aa_track in aa_tracks:
                lib_tracks.add(aa_track)

        return SearchResult(uri='gmusic:search',
                            tracks=lib_tracks,
                            artists=lib_artists,
                            albums=lib_albums)

    def _find_exact(self, query=None, uris=None):
        # Find exact can only be done on gmusic library,
        # since one can't filter all access searches
        lib_tracks, lib_artists, lib_albums = self._search_library(query, uris)

        return SearchResult(uri='gmusic:search',
                            tracks=lib_tracks,
                            artists=lib_artists,
                            albums=lib_albums)

    def _search(self, query=None, uris=None):
        for (field, values) in query.iteritems():
            if not hasattr(values, '__iter__'):
                values = [values]

            # Since gmusic does not support search filters, just search for the
            # first 'searchable' filter
            if field in [
                    'track_name', 'album', 'artist', 'albumartist', 'any']:
                logger.info(
                    'Searching Google Play Music for: %s',
                    values[0])
                res = self.backend.session.search(values[0], max_results=50)
                if res is None:
                    return [], [], []

                albums = [
                    self._aa_search_album_to_mopidy_album(album_res)
                    for album_res in res['album_hits']]
                artists = [
                    self._aa_search_artist_to_mopidy_artist(artist_res)
                    for artist_res in res['artist_hits']]
                tracks = [
                    self._aa_search_track_to_mopidy_track(track_res)
                    for track_res in res['song_hits']]

                return tracks, artists, albums

        return [], [], []

    def _search_library(self, query=None, uris=None):
        if query is None:
            query = {}
        self._validate_query(query)
        result_tracks = self.tracks.values()

        for (field, values) in query.iteritems():
            if not hasattr(values, '__iter__'):
                values = [values]
            # FIXME this is bound to be slow for large libraries
            for value in values:
                if field == 'track_no':
                    q = self._convert_to_int(value)
                else:
                    q = value.strip().lower()

                def uri_filter(track):
                    return q in track.uri.lower()

                def track_name_filter(track):
                    return q in track.name.lower()

                def album_filter(track):
                    return q in getattr(track, 'album', Album()).name.lower()

                def artist_filter(track):
                    return (
                        any(q in a.name.lower() for a in track.artists) or
                        albumartist_filter(track))

                def albumartist_filter(track):
                    album_artists = getattr(track, 'album', Album()).artists
                    return any(q in a.name.lower() for a in album_artists)

                def track_no_filter(track):
                    return track.track_no == q

                def date_filter(track):
                    return track.date and track.date.startswith(q)

                def any_filter(track):
                    return any([
                        uri_filter(track),
                        track_name_filter(track),
                        album_filter(track),
                        artist_filter(track),
                        albumartist_filter(track),
                        date_filter(track),
                    ])

                if field == 'uri':
                    result_tracks = filter(uri_filter, result_tracks)
                elif field == 'track_name':
                    result_tracks = filter(track_name_filter, result_tracks)
                elif field == 'album':
                    result_tracks = filter(album_filter, result_tracks)
                elif field == 'artist':
                    result_tracks = filter(artist_filter, result_tracks)
                elif field == 'albumartist':
                    result_tracks = filter(albumartist_filter, result_tracks)
                elif field == 'track_no':
                    result_tracks = filter(track_no_filter, result_tracks)
                elif field == 'date':
                    result_tracks = filter(date_filter, result_tracks)
                elif field == 'any':
                    result_tracks = filter(any_filter, result_tracks)
                else:
                    raise LookupError('Invalid lookup field: %s' % field)

        result_artists = set()
        result_albums = set()
        for track in result_tracks:
            result_artists |= track.artists
            result_albums.add(track.album)

        return result_tracks, result_artists, result_albums

    def _validate_query(self, query):
        for (_, values) in query.iteritems():
            if not values:
                raise LookupError('Missing query')
            for value in values:
                if not value:
                    raise LookupError('Missing query')

    def _to_mopidy_track(self, song):
        track_id = song.get('id', song.get('nid'))
        if track_id is None:
            raise ValueError
        if track_id[0] != "T" and "-" not in track_id:
            track_id = "T"+track_id
        return Track(
            uri='gmusic:track:' + track_id,
            name=song['title'],
            artists=[self._to_mopidy_artist(song)],
            album=self._to_mopidy_album(song),
            track_no=song.get('trackNumber', 1),
            disc_no=song.get('discNumber', 1),
            date=unicode(song.get('year', 0)),
            length=int(song['durationMillis']),
            bitrate=320)

    def _to_mopidy_album(self, song):
        name = song.get('album', '')
        artist = self._to_mopidy_album_artist(song)
        date = unicode(song.get('year', 0))

        album_id = song.get('albumId')
        if album_id is None:
            album_id = create_id(artist.name + name + date)

        uri = 'gmusic:album:' + album_id
        images = get_images(song)
        return Album(
            uri=uri,
            name=name,
            artists=[artist],
            num_tracks=song.get('totalTrackCount'),
            num_discs=song.get('totalDiscCount'),
            date=date,
            images=images)

    def _to_mopidy_artist(self, song):
        name = song.get('artist', '')
        artist_id = song.get('artistId')
        if artist_id is not None:
            artist_id = artist_id[0]
        else:
            artist_id = create_id(name)
        uri = 'gmusic:artist:' + artist_id
        return Artist(uri=uri, name=name)

    def _to_mopidy_album_artist(self, song):
        name = song.get('albumArtist', '')
        if name.strip() == '':
            name = song.get('artist', '')
        uri = 'gmusic:artist:' + create_id(name)
        return Artist(uri=uri, name=name)

    def _aa_search_track_to_mopidy_track(self, search_track):
        track = search_track['track']

        aa_artist_id = create_id(track['artist'])
        if 'artistId' in track:
            aa_artist_id = track['artistId'][0]
        else:
            logger.warning('No artistId for Track %r', track)

        artist = Artist(
            uri='gmusic:artist:' + aa_artist_id,
            name=track['artist'])

        album = Album(
            uri='gmusic:album:' + track['albumId'],
            name=track['album'],
            artists=[artist],
            date=unicode(track.get('year', 0)))

        return Track(
            uri='gmusic:track:' + track['storeId'],
            name=track['title'],
            artists=[artist],
            album=album,
            track_no=track.get('trackNumber', 1),
            disc_no=track.get('discNumber', 1),
            date=unicode(track.get('year', 0)),
            length=int(track['durationMillis']),
            bitrate=320)

    def _aa_search_artist_to_mopidy_artist(self, search_artist):
        artist = search_artist['artist']
        uri = 'gmusic:artist:' + artist['artistId']
        return Artist(uri=uri, name=artist['name'])

    def _aa_search_album_to_mopidy_album(self, search_album):
        album = search_album['album']
        uri = 'gmusic:album:' + album['albumId']
        name = album['name']
        artist = self._aa_search_artist_album_to_mopidy_artist_album(album)
        date = unicode(album.get('year', 0))
        return Album(
            uri=uri,
            name=name,
            artists=[artist],
            date=date)

    def _aa_search_artist_album_to_mopidy_artist_album(self, album):
        name = album.get('albumArtist', '')
        if name.strip() == '':
            name = album.get('artist', '')
        uri = 'gmusic:artist:' + create_id(name)
        return Artist(uri=uri, name=name)

    def _convert_to_int(self, string):
        try:
            return int(string)
        except ValueError:
            return object()
