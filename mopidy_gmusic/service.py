from gmusicapi import Mobileclient

SEARCH_RESULT_TYPES = ['album', 'artist', 'playlist', 'station', 'song',
                       'situation', 'video']
IFL_STATION_DICT = {'id': 'IFL', 'name': 'I\'m Feeling Lucky'}


class GMusicService(Mobileclient):
    """ Subclass of gmusicapi's Mobileclient for reimplementing some features
    in ways more appropriate for its use in mopidy-gmusic. """

    def __init__(self, debug_logging=True, validate=True, verify_ssl=True):
        self.superclass = super(GMusicService, self)
        self.superclass.__init__(debug_logging,
                                 validate,
                                 verify_ssl)

    def search(self, query, max_results=50):
        """ Allow backwards compatibility for gmusicapi <= 9.0.
        search() was renamed in gmusicapi
        4419d0e10812d5b8861d0fafb45b74e8a1b63f27 """
        try:
            results = self.superclass.search(query, max_results=max_results)
        except AttributeError:
            results = self.superclass.search_all_access(
                                                    query,
                                                    max_results=max_results)
        return results
