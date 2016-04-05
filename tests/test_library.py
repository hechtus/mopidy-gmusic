import unittest

from mopidy.backend import models

from mopidy_gmusic import actor as backend_lib

from mopidy_gmusic import service

from tests.test_extension import ExtensionTest


class LibraryTest(unittest.TestCase):

    def setUp(self):
        config = ExtensionTest.get_config()
        self.backend = backend_lib.GMusicBackend(config=config, audio=None)

    def test_browse_radio_deactivated(self):
        config = ExtensionTest.get_config()
        config['gmusic']['radio_stations_in_browse'] = False
        self.backend = backend_lib.GMusicBackend(config=config, audio=None)

        refs = self.backend.library.browse('gmusic:directory')
        for ref in refs:
            self.assertNotEqual(ref.uri, 'gmusic:radio')

    def test_browse_none(self):
        refs = self.backend.library.browse(None)
        self.assertEqual(refs, [])

    def test_browse_invalid(self):
        refs = self.backend.library.browse('gmusic:invalid_uri')
        self.assertEqual(refs, [])

    def test_browse_root(self):
        refs = self.backend.library.browse('gmusic:directory')
        found = False
        for ref in refs:
            if ref.uri == 'gmusic:album':
                found = True
                break
        self.assertTrue(found, 'ref \'gmusic:album\' not found')
        found = False
        for ref in refs:
            if ref.uri == 'gmusic:artist':
                found = True
                break
        self.assertTrue(found, 'ref \'gmusic:artist\' not found')
        found = False
        for ref in refs:
            if ref.uri == 'gmusic:radio':
                found = True
                break
        self.assertTrue(found, 'ref \'gmusic:radio\' not found')

    def test_browse_artist(self):
        refs = self.backend.library.browse('gmusic:artist')
        self.assertIsNotNone(refs)

    def test_browse_artist_id_invalid(self):
        refs = self.backend.library.browse('gmusic:artist:artist_id')
        self.assertIsNotNone(refs)
        self.assertEqual(refs, [])

    def test_browse_album(self):
        refs = self.backend.library.browse('gmusic:album')
        self.assertIsNotNone(refs)

    def test_browse_album_id_invalid(self):
        refs = self.backend.library.browse('gmusic:album:album_id')
        self.assertIsNotNone(refs)
        self.assertEqual(refs, [])

    def test_browse_radio(self):
        refs = self.backend.library.browse('gmusic:radio')
        # tests should be unable to fetch stations :(
        self.assertIsNotNone(refs)

        # TODO: What method needs to be invoked to create this Ref object
        # automatically from service.IFL_STATION_DICT?
        iflStation = models.Ref(name="I'm Feeling Lucky", type='directory',
                                uri='gmusic:radio:IFL')
        self.assertEqual(refs, [iflStation])

    def test_browse_station(self):
        refs = self.backend.library.browse('gmusic:radio:invalid_stations_id')
        # tests should be unable to fetch stations :(
        self.assertEqual(refs, [])

    def test_lookup_invalid(self):
        refs = self.backend.library.lookup('gmusic:invalid_uri')
        # tests should be unable to fetch any content :(
        self.assertEqual(refs, [])

    def test_lookup_invalid_album(self):
        refs = self.backend.library.lookup('gmusic:album:invalid_uri')
        # tests should be unable to fetch any content :(
        self.assertEqual(refs, [])

    def test_lookup_invalid_artist(self):
        refs = self.backend.library.lookup('gmusic:artist:invalid_uri')
        # tests should be unable to fetch any content :(
        self.assertEqual(refs, [])

    def test_lookup_invalid_track(self):
        refs = self.backend.library.lookup('gmusic:track:invalid_uri')
        # tests should be unable to fetch any content :(
        self.assertEqual(refs, [])

    def test_no_fuzzy_search(self):
        artistToBeFound = {'artist': {'name': 'easteregg'}}
        artistToBeIgnored = {'artist': {'name': 'easter egg'}}
        artistToBeFound = {'artist': {'name': 'easteregg'}}
        query = {'artist': [artistToBeFound['artist']['name']]}

        search_results = self.createEmptySearchResults()
        search_results['artist_hits'] = [artistToBeFound, artistToBeIgnored]

        expectedResult = self.createEmptySearchResults()
        expectedResult['artist_hits'] = [artistToBeFound]

        result = self.backend.library.filter_search_results(
                search_results, query)
        assert result == expectedResult

    def test_filter_search_results_by_field(self):
        trackToBeFound = {'track': {'title': 'easteregg',
                                    'artist': 'Doublebass',
                                    'album': 'Unreleased',
                                    'album_artist': 'Doublebass'}}
        trackToBeIgnored = {'track': {'title': 'Frimaire',
                                      'artist': 'easteregg',
                                      'album': 'Ferne',
                                      'album_artist': 'easteregg'}}
        query = {'track_name': [trackToBeFound['track']['title']]}

        search_results = self.createEmptySearchResults()
        search_results['song_hits'] = [trackToBeFound, trackToBeIgnored]

        expectedResult = self.createEmptySearchResults()
        expectedResult['song_hits'] = [trackToBeFound]

        result = self.backend.library.filter_search_results(
                search_results, query)
        assert result == expectedResult

    def createEmptySearchResults(self):
        search_results = {}
        for search_result_type in service.SEARCH_RESULT_TYPES:
            search_results['{}_hits'.format(search_result_type)] = []
        return search_results
