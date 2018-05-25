from __future__ import unicode_literals

import os

from mopidy import config, ext


__version__ = '2.0.0'


class GMusicExtension(ext.Extension):

    dist_name = 'Mopidy-GMusic'
    ext_name = 'gmusic'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(GMusicExtension, self).get_config_schema()

        schema['username'] = config.String()
        schema['password'] = config.Secret()

        schema['bitrate'] = config.Integer(choices=(128, 160, 320))

        schema['deviceid'] = config.String(optional=True)

        schema['all_access'] = config.Boolean(optional=True)

        schema['refresh_library'] = config.Integer(minimum=-1, optional=True)
        schema['refresh_playlists'] = config.Integer(minimum=-1, optional=True)

        schema['radio_stations_in_browse'] = config.Boolean(optional=True)
        schema['radio_stations_as_playlists'] = config.Boolean(optional=True)
        schema['radio_stations_count'] = config.Integer(
            minimum=1, optional=True)
        schema['radio_tracks_count'] = config.Integer(minimum=1, optional=True)

        schema['top_tracks_count'] = config.Integer(minimum=1, optional=True)

        return schema

    def setup(self, registry):
        from .backend import GMusicBackend
        from .scrobbler_frontend import GMusicScrobblerFrontend
        registry.add('backend', GMusicBackend)
        registry.add('frontend', GMusicScrobblerFrontend)
