from __future__ import unicode_literals

import logging
import time

from threading import Lock

from mopidy import backend

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

        # If no device ID was specified, we need to try and get one
        # (if possible).
        if self.config['gmusic']['deviceid'] is None:
            devices = self.session.api.get_registered_devices()
            devices.sort(key=lambda item: item['lastAccessedTimeMs'],
                         reverse=True)

            dev_ids = []
            for device in devices:
                dev_id = device['id']
                # Android devices ID starts with 0x, and iOS device
                # IDs start with ios:, so we need to chop them off.
                if dev_id.startswith('0x'):
                    dev_id = dev_id[2:]
                elif dev_id.startswith('ios:'):
                    dev_id = dev_id[4:]
                else:
                    continue

                dev_ids.append(dev_id)

                logger.info("GMusic Device %s, Type: %s, ID: %s",
                            device['friendlyName'], device['type'], dev_id)

            # If we found any device IDs, we select the first one. We
            # previously sorted by the last accessed time, so this
            # will be the most recently used.
            if len(dev_ids) > 0:
                self.session.logout()
                logger.info("Using device ID %s for GMusic login", dev_ids[0])
                self.session.login(self.config['gmusic']['username'],
                                   self.config['gmusic']['password'],
                                   dev_ids[0])
            else:
                logger.warn('No valid GMusic device IDs found')

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
