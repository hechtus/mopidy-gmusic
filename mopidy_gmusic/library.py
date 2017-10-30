from __future__ import unicode_literals

import hashlib
import logging

from mopidy import backend
from mopidy.models import Album, Artist, Ref, SearchResult, Track

from mopidy_gmusic.lru_cache import LruCache

logger = logging.getLogger(__name__)


class GMusicLibraryProvider(backend.LibraryProvider):
    root_directory = Ref.directory(uri='gmusic:directory', name='Google Music')

    def __init__(self, *args, **kwargs):
        super(GMusicLibraryProvider, self).__init__(*args, **kwargs)
        self.tracks = {}
        self.albums = {}
        self.artists = {}
        self.aa_artists = {}
        self.aa_tracks = LruCache()
        self.aa_albums = LruCache()
        self.all_access = False
        self._radio_stations_in_browse = (
            self.backend.config['gmusic']['radio_stations_in_browse'])
        self._radio_stations_count = (
            self.backend.config['gmusic']['radio_stations_count'])
        self._radio_tracks_count = (
            self.backend.config['gmusic']['radio_tracks_count'])
        self._root = []
        self._root.append(Ref.directory(uri='gmusic:album', name='Albums'))
        self._root.append(Ref.directory(uri='gmusic:artist', name='Artists'))
        # browsing all tracks results in connection timeouts
        # self._root.append(Ref.directory(uri='gmusic:track', name='Tracks'))

        if self._radio_stations_in_browse:
            self._root.append(Ref.directory(uri='gmusic:radio',
                                            name='Radios'))
        # show root only if there is something to browse
        if len(self._root) > 0:
            GMusicLibraryProvider.root_directory = Ref.directory(
                uri='gmusic:directory', name='Google Music')

    def set_all_access(self, all_access):
        self.all_access = all_access

    def _browse_albums(self):
        refs = []
        for album in self.albums.values():
            refs.append(self._album_to_ref(album))
        refs.sort(key=lambda ref: ref.name)
        return refs

    def _browse_album(self, uri):
        refs = []
        for track in self._lookup_album(uri):
            refs.append(self._track_to_ref(track, True))
        return refs

    def _browse_artists(self):
        refs = []
        for artist in self.artists.values():
            refs.append(self._artist_to_ref(artist))
        refs.sort(key=lambda ref: ref.name)
        return refs

    def _browse_artist(self, uri):
        refs = []
        for album in self._get_artist_albums(uri):
            refs.append(self._album_to_ref(album))
            refs.sort(key=lambda ref: ref.name)
        if len(refs) > 0:
            refs.insert(0, Ref.directory(uri=uri + ':all', name='All Tracks'))
            return refs
        else:
            # Show all tracks if no album is available
            return self._browse_artist_all_tracks(uri)

    def _browse_artist_all_tracks(self, uri):
        artist_uri = ':'.join(uri.split(':')[:3])
        refs = []
        tracks = self._lookup_artist(artist_uri, True)
        for track in tracks:
            refs.append(self._track_to_ref(track))
        return refs

    def browse(self, uri):
        logger.debug('browse: %s', str(uri))
        if not uri:
            return []
        if uri == self.root_directory.uri:
            return self._root

        parts = uri.split(':')

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

        # all radio stations
        if uri == 'gmusic:radio':
            stations = self.backend.session.get_radio_stations(
                self._radio_stations_count)
            # create Ref objects
            refs = []
            for station in stations:
                refs.append(Ref.directory(uri='gmusic:radio:' + station['id'],
                                          name=station['name']))
            return refs

        # a single radio station
        # uri == 'gmusic:radio:station_id'
        if len(parts) == 3 and parts[1] == 'radio':
            station_id = parts[2]
            tracks = self.backend.session.get_station_tracks(
                station_id, self._radio_tracks_count)
            # create Ref objects
            refs = []
            for track in tracks:
                track_id = track['nid']
                # some clients request a lookup themself, some don't
                # we do not want to ask the API for every track twice
                # we'll fetch some information directly from provided object
                track_name = '%s - %s' % (track['artist'], track['title'])
                refs.append(Ref.track(uri='gmusic:track:' + track_id,
                                      name=track_name))
            return refs

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

        if is_all_access and self.all_access:
            track = self.aa_tracks.hit(uri)
            if track:
                return [track]
            song = self.backend.session.get_track_info(uri.split(':')[2])
            if song is None:
                logger.warning('There is no song %r', uri)
                return []
            if 'artistId' not in song:
                logger.warning('Failed to lookup %r', uri)
                return []
            return [self._aa_to_mopidy_track(song)]
        elif not is_all_access:
            try:
                return [self.tracks[uri]]
            except KeyError:
                logger.debug('Failed to lookup %r', uri)
                return []
        else:
            return []

    def _lookup_album(self, uri):
        is_all_access = uri.startswith('gmusic:album:B')
        if self.all_access and is_all_access:
            tracks = self.aa_albums.hit(uri)
            if tracks:
                return tracks
            album = self.backend.session.get_album_info(
                uri.split(':')[2], include_tracks=True)
            if album is None or not album['tracks']:
                logger.warning('Failed to lookup %r: %r', uri, album)
                return []
            tracks = [
                self._aa_to_mopidy_track(track) for track in album['tracks']]
            self.aa_albums[uri] = tracks
            return sorted(tracks, key=lambda t: (t.disc_no,
                                                 t.track_no))
        elif not is_all_access:
            try:
                album = self.albums[uri]
            except KeyError:
                logger.debug('Failed to lookup %r', uri)
                return []
            tracks = self._find_exact(
                dict(album=album.name,
                     artist=[artist.name for artist in album.artists],
                     date=album.date)).tracks
            return sorted(tracks, key=lambda t: (t.disc_no,
                                                 t.track_no))
        else:
            logger.debug('Failed to lookup %r', uri)
            return []

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
        sorter = lambda t: (t.album.date,
                            t.album.name,
                            t.disc_no,
                            t.track_no)
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
        self.aa_artists = {}
        for song in self.backend.session.get_all_songs():
            self._to_mopidy_track(song)

    def search(self, query=None, uris=None, exact=False):
        if exact:
            return self._find_exact(query=query, uris=uris)

        lib_tracks, lib_artists, lib_albums = self._search_library(query, uris)

        if query and self.all_access:
            aa_tracks, aa_artists, aa_albums = self._search_all_access(
                query, uris)
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

    def _search_all_access(self, query=None, uris=None):
        for (field, values) in query.iteritems():
            if not hasattr(values, '__iter__'):
                values = [values]

            # Since gmusic does not support search filters, just search for the
            # first 'searchable' filter
            if field in [
                    'track_name', 'album', 'artist', 'albumartist', 'any']:
                logger.info(
                    'Searching Google Play Music All Access for: %s',
                    values[0])
                res = self.backend.session.search_all_access(
                    values[0], max_results=50)
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

                uri_filter = lambda t: q in t.uri.lower()
                track_name_filter = lambda t: q in t.name.lower()
                album_filter = lambda t: q in getattr(
                    t, 'album', Album()).name.lower()
                artist_filter = lambda t: filter(
                    lambda a: q in a.name.lower(), t.artists) or filter(
                    lambda a: q in a.name, getattr(t, 'album',
                                                   Album()).artists)

                albumartist_filter = lambda t: any([
                    q in a.name.lower()
                    for a in getattr(t.album, 'artists', [])])
                track_no_filter = lambda t: q == t.track_no
                date_filter = lambda t: t.date and t.date.startswith(q)
                any_filter = lambda t: (
                    uri_filter(t) or
                    track_name_filter(t) or
                    album_filter(t) or
                    artist_filter(t) or
                    albumartist_filter(t) or
                    date_filter(t))

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
        uri = 'gmusic:track:' + song['id']
        track = Track(
            uri=uri,
            name=song['title'],
            artists=[self._to_mopidy_artist(song)],
            album=self._to_mopidy_album(song),
            track_no=song.get('trackNumber', 1),
            disc_no=song.get('discNumber', 1),
            date=unicode(song.get('year', 0)),
            length=int(song['durationMillis']),
            bitrate=320)
        self.tracks[uri] = track
        return track

    def _to_mopidy_album(self, song):
        # First try to process the album as an aa album
        # (Difference being that non aa albums don't have albumId)
        try:
            album = self._aa_to_mopidy_album(song)
            return album
        except KeyError:
            name = song.get('album', '')
            artist = self._to_mopidy_album_artist(song)
            date = unicode(song.get('year', 0))
            uri = 'gmusic:album:' + self._create_id(artist.name + name + date)
            images = self._get_images(song)
            album = Album(
                uri=uri,
                name=name,
                artists=[artist],
                num_tracks=song.get('totalTrackCount', 1),
                num_discs=song.get(
                    'totalDiscCount', song.get('discNumber', 1)),
                date=date,
                images=images)
            self.albums[uri] = album
            return album

    def _to_mopidy_artist(self, song):
        name = song.get('artist', '')
        uri = 'gmusic:artist:' + self._create_id(name)

        # First try to process the artist as an aa artist
        # (Difference being that non aa artists don't have artistId)
        try:
            artist = self._aa_to_mopidy_artist(song)
            self.artists[uri] = artist
            return artist
        except KeyError:
            artist = Artist(
                uri=uri,
                name=name)
            self.artists[uri] = artist
            return artist

    def _to_mopidy_album_artist(self, song):
        name = song.get('albumArtist', '')
        if name.strip() == '':
            name = song.get('artist', '')
        uri = 'gmusic:artist:' + self._create_id(name)
        artist = Artist(
            uri=uri,
            name=name)
        self.artists[uri] = artist
        return artist

    def _aa_to_mopidy_track(self, song):
        uri = 'gmusic:track:' + song['storeId']
        album = self._aa_to_mopidy_album(song)
        artist = self._aa_to_mopidy_artist(song)
        track = Track(
            uri=uri,
            name=song['title'],
            artists=[artist],
            album=album,
            track_no=song.get('trackNumber', 1),
            disc_no=song.get('discNumber', 1),
            date=album.date,
            length=int(song['durationMillis']),
            bitrate=320)
        self.aa_tracks[uri] = track
        return track

    def _aa_to_mopidy_album(self, song):
        uri = 'gmusic:album:' + song['albumId']
        name = song['album']
        artist = self._aa_to_mopidy_album_artist(song)
        date = unicode(song.get('year', 0))
        images = self._get_images(song)
        return Album(
            uri=uri,
            name=name,
            artists=[artist],
            date=date,
            images=images)

    def _aa_to_mopidy_artist(self, song):
        name = song.get('artist', '')
        artist_id = self._create_id(name)
        uri = 'gmusic:artist:' + artist_id
        self.aa_artists[artist_id] = song['artistId'][0]
        return Artist(
            uri=uri,
            name=name)

    def _aa_to_mopidy_album_artist(self, song):
        name = song.get('albumArtist', '')
        if name.strip() == '':
            name = song['artist']
        uri = 'gmusic:artist:' + self._create_id(name)
        return Artist(
            uri=uri,
            name=name)

    def _aa_search_track_to_mopidy_track(self, search_track):
        track = search_track['track']

        aa_artist_id = self._create_id(track['artist'])
        if 'artistId' in track:
            self.aa_artists[aa_artist_id] = track['artistId'][0]
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
        artist_id = self._create_id(artist['name'])
        uri = 'gmusic:artist:' + artist_id
        self.aa_artists[artist_id] = artist['artistId']
        return Artist(
            uri=uri,
            name=artist['name'])

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
        uri = 'gmusic:artist:' + self._create_id(name)
        return Artist(
            uri=uri,
            name=name)

    def _album_to_ref(self, album):
        name = ''
        for artist in album.artists:
            if len(name) > 0:
                name += ', '
            name += artist.name
        if (len(name)) > 0:
            name += ' - '
        if album.name:
            name += album.name
        else:
            name += 'Unknown Album'
        return Ref.directory(uri=album.uri, name=name)

    def _artist_to_ref(self, artist):
        if artist.name:
            name = artist.name
        else:
            name = 'Unknown artist'
        return Ref.directory(uri=artist.uri, name=name)

    def _track_to_ref(self, track, with_track_no=False):
        if with_track_no and track.track_no > 0:
            name = '%d - ' % track.track_no
        else:
            name = ''
        for artist in track.artists:
            if len(name) > 0:
                name += ', '
            name += artist.name
        if (len(name)) > 0:
            name += ' - '
        name += track.name
        return Ref.track(uri=track.uri, name=name)

    def _get_images(self, song):
        if 'albumArtRef' in song:
            return [art_ref['url']
                    for art_ref in song['albumArtRef']
                    if 'url' in art_ref]

    def _create_id(self, u):
        return hashlib.md5(u.encode('utf-8')).hexdigest()

    def _convert_to_int(self, string):
        try:
            return int(string)
        except ValueError:
            return object()
