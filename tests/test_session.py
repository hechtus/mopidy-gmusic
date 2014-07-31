import unittest

from gmusicapi import CallFailure

import mock

from mopidy_gmusic.session import GMusicSession


class TestFailure(CallFailure):
    def __init__(self):
        super(TestFailure, self).__init__('test error', 'blubb')


class ManagerTest(unittest.TestCase):

    def test_api_genre_compat(self):
        session = GMusicSession()
        session.api.is_authenticated = mock.Mock(return_value=True)

        g = {'id': 'SOME_GENRE', 'name': 'a genre'}
        session.api.get_genres = mock.Mock(return_value=[g])
        self.assertEqual(session.get_genres(), [g])

        session.api.get_genres = mock.Mock(return_value={'genres': [g]})
        self.assertEqual(session.get_genres(), [g])

        session.api.get_genres = mock.Mock(return_value={'xxxx': [g]})
        self.assertEqual(session.get_genres(), [])

        session.api.get_genres = mock.Mock(side_effect=TestFailure)
        self.assertIsNone(session.get_genres())
