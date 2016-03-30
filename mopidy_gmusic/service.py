from gmusicapi import Mobileclient


class GMusicService(Mobileclient):
    ''' Subclass of gmusicapi's Mobileclient for reimplementing some features
    in ways more appropriate for its use in mopidy-gmusic. '''

    def __init__(self, debug_logging=True, validate=True, verify_ssl=True):
        self.superclass = super(GMusicService, self)
        self.superclass.__init__(debug_logging,
                                 validate,
                                 verify_ssl)

    def search(self, query, max_results=50):
        ''' Allow backwards compatibility for gmusicapi <= 9.0.
        search() was renamed in gmusicapi
        4419d0e10812d5b8861d0fafb45b74e8a1b63f27 '''
        # TODO: solely use search as soon as gmusicapi in its AUR is updated.
        try:
            results = self.superclass.search(query, max_results=max_results)
        except AttributeError:
            results = self.superclass.search_all_access(
                                                    query,
                                                    max_results=max_results)
        return results

    def add_store_track(self, store_song_id):
        ''' Allow backwards compatibility for gmusicapi <= 9.0.
        add_aa_track() was renamed in gmusicapi
        3abdfcc2d2e47a567697953dde00ad382721a15e '''
        # TODO: solely use search as soon as gmusicapi in its AUR is updated.
        try:
            library_track_id = self.superclass.add_store_track(self,
                                                               store_song_id)
        except AttributeError:
            library_track_id = self.superclass.add_aa_track(self,
                                                            store_song_id)
        return library_track_id
