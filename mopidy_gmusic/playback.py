from __future__ import unicode_literals

import logging

from mopidy import backend

logger = logging.getLogger(__name__)


BITRATES = {
    128: 'low',
    160: 'med',
    320: 'hi',
}


class GMusicPlaybackProvider(backend.PlaybackProvider):
    def translate_uri(self, uri):
        track_id = uri.rsplit(':')[-1]

        quality = BITRATES[self.backend.config['gmusic']['bitrate']]
        stream_uri = self.backend.session.get_stream_url(
            track_id, quality=quality)

        logger.debug('Translated: %s -> %s', uri, stream_uri)
        return stream_uri
