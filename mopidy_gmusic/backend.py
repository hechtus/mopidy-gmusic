from __future__ import unicode_literals

import logging
import time

from threading import Lock

from mopidy import backend, exceptions

import pykka

from .library import GMusicLibraryProvider
from .playback import GMusicPlaybackProvider
from .playlists import GMusicPlaylistsProvider
from .repeating_timer import RepeatingTimer
from .scrobbler_frontend import GMusicScrobblerListener
from .session import GMusicSession

logger = logging.getLogger(__name__)


class GMusicBackend(
        pykka.ThreadingActor, backend.Backend, GMusicScrobblerListener):

    def __init__(self, config, audio):
        super(GMusicBackend, self).__init__()

        self.config = config

        self._refresh_library_rate = \
            config['gmusic']['refresh_library'] * 60.0
        self._refresh_playlists_rate = \
            config['gmusic']['refresh_playlists'] * 60.0
        self._refresh_library_timer = None
        self._refresh_playlists_timer = None
        self._refresh_lock = Lock()
        self._playlist_lock = Lock()
        self._refresh_last = 0
        # do not run playlist refresh around library refresh
        self._refresh_threshold = self._refresh_playlists_rate * 0.3

        self.library = GMusicLibraryProvider(backend=self)
        self.playback = GMusicPlaybackProvider(audio=audio, backend=self)
        self.playlists = GMusicPlaylistsProvider(backend=self)
        self.session = GMusicSession(all_access=config['gmusic']['all_access'])

        self.uri_schemes = ['gmusic']

    def on_start(self):
        self.session.login(self.config['gmusic']['username'],
                           self.config['gmusic']['password'],
                           self.config['gmusic']['deviceid'])

        if not self.config['gmusic']['deviceid']:
            logger.error('There is no gmusic deviceid set. '
                         'Registered devices are listed below.')
            for device in self.session.api.get_registered_devices():
                deviceid = device['id']
                if deviceid.startswith('ios:'):
                    deviceid = deviceid[4:]
                elif deviceid.startswith('0x'):
                    deviceid = deviceid[2:]
                logger.error('Name: %s, ID: %s',
                            device.get('friendlyName', 'Unknown Device'),
                            deviceid)
            raise exceptions.BackendError("No deviceid configured")

        # wait a few seconds to let mopidy settle
        # then refresh google music content asynchronously
        self._refresh_library_timer = RepeatingTimer(
            self._refresh_library,
            self._refresh_library_rate)
        self._refresh_library_timer.start()
        # schedule playlist refresh as desired
        if self._refresh_playlists_rate > 0:
            self._refresh_playlists_timer = RepeatingTimer(
                self._refresh_playlists,
                self._refresh_playlists_rate)
            self._refresh_playlists_timer.start()

    def on_stop(self):
        if self._refresh_library_timer:
            self._refresh_library_timer.cancel()
            self._refresh_library_timer = None
        if self._refresh_playlists_timer:
            self._refresh_playlists_timer.cancel()
            self._refresh_playlists_timer = None
        self.session.logout()

    def increment_song_playcount(self, track_id):
        # Called through GMusicScrobblerListener
        self.session.increment_song_playcount(track_id)

    def _refresh_library(self):
        with self._refresh_lock:
            t0 = round(time.time())
            logger.info('Start refreshing Google Music library')
            self.library.refresh()
            t = round(time.time()) - t0
            logger.info('Finished refreshing Google Music library in %ds', t)

    def _refresh_playlists(self):
        with self._playlist_lock:
            t0 = round(time.time())
            logger.info('Start refreshing Google Music playlists')
            self.playlists.refresh()
            t = round(time.time()) - t0
            logger.info('Finished refreshing Google Music playlists in %ds', t)
