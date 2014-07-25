from __future__ import unicode_literals

import os

from mopidy import config, ext


__version__ = '0.3.0'


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
        schema['deviceid'] = config.String(optional=True)
        schema['all_access'] = config.String(optional=True)
        schema['max_radio_stations'] = config.Integer(minimum=0, optional=True)
        schema['max_radio_tracks'] = config.Integer(minimum=0, optional=True)
        return schema

    def setup(self, registry):
        from .actor import GMusicBackend
        registry.add('backend', GMusicBackend)
