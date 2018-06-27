*************
Mopidy-GMusic
*************

.. image:: https://img.shields.io/pypi/v/Mopidy-GMusic.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-GMusic/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/travis/mopidy/mopidy-gmusic/develop.svg?style=flat
    :target: https://travis-ci.org/mopidy/mopidy-gmusic
    :alt: Travis CI build status

.. image:: https://img.shields.io/coveralls/mopidy/mopidy-gmusic/develop.svg?style=flat
   :target: https://coveralls.io/r/mopidy/mopidy-gmusic
   :alt: Test coverage

`Mopidy <http://www.mopidy.com/>`_ extension for playing music from
`Google Play Music <https://play.google.com/music/>`_.


Dependencies
============

You must have a Google account, and either:

- have some music uploaded to your Google Play Music library, or

- have a subscription for Google Play Music All Access.


Installation
============

Install the Mopidy-GMusic extension by running::

    pip install mopidy-gmusic


Configuration
=============

Before starting Mopidy, you must add your Google username, password and device
ID to your Mopidy configuration file::

    [gmusic]
    username = alice
    password = secret
    deviceid = 0123456789abcdef

If you use 2-step verification to access your Google account, which you should,
you must create an application password in your Google account for
Mopidy-GMusic. See Google's docs on `how to make an app password
<https://support.google.com/accounts/answer/185833>`_ if you're not already
familiar with this.

Google Play Music now requires all clients to provide a device ID. In the past,
mopidy-gmusic generated one automatically from your MAC address, but Google
seems to have changed their API in a way that prevents this from working.
Therefore you will need to configure one manually.
If no device ID is configured, mopidy-gmusic will output a list of registered
devices and their IDs. You can either use one of those IDs in your config file,
or use the special value `mac` if you want gmusicapi to use the old method of
generating an ID from your MAC address.::

    [gmusic]
    deviceid = 0123456789abcdef
    # or
    deviceid = mac

By default, All Access will be enabled automatically if you subscribe. You may
force enable or disable it by using the all_access option::

    [gmusic]
    all_access = true

By default, the bitrate is set to 160 kbps. You can change this to either 128
or 320 kbps by setting::

    [gmusic]
    bitrate = 320

All Access radios are available as browsable content or playlist. The following
are the default config values::

    [gmusic]
    # Show radio stations in content browser
    radio_stations_in_browse = true
    # Show radio stations as playlists
    radio_stations_as_playlists = false
    # Limit the number of radio stations, unlimited if unset
    radio_stations_count =
    # Limit the number or tracks for each radio station
    radio_tracks_count = 25


Usage
=====

The extension is enabled by default if all dependencies are
available. You can simply browse through your library and search for
tracks, albums, and artists. Google Play Music playlists are imported
as well. You can even add songs from your All Access subscription to
your library. Mopidy will able to play them.


SSL Errors
==========

There have been reports of some errors relating to certificate verification like
the following::

    SSLError: ("bad handshake: Error([('SSL routines', 'SSL3_GET_SERVER_CERTIFICATE', 'certificate verify failed')],)",)

This is because OpenSSL 1.0.1 cannot handle cross-signed certificates. There
have been a number of possible solutions for this. Below, they are listed in
order of preference. If one is not possible or does not work, try the next one.

- Upgrade to OpenSSL 1.0.2
- Assign the result of the following command to the REQUESTS_CA_BUNDLE::

    python -c 'import certifi; print certifi.old_where()'

- Downgrade to certifi==2015.04.28


Project resources
=================

- `Source code <https://github.com/mopidy/mopidy-gmusic>`_
- `Issue tracker <https://github.com/mopidy/mopidy-gmusic/issues>`_


Credits
=======

We are currently looking for a co-maintainer. Preferably someone who is familiar
with the codebase, familiar with python development, and uses the uploaded music
feature. If you're interested, please take a look at the code base and work on
submitting a pull request or two (to show you understand how everything works
together). If you need help getting a development environment set up, don't
hesitate to ping belak in the #mopidy channel on the Freenode IRC network.

- Original author: `Ronald Hecht <https://github.com/hechtus>`_
- Current maintainer: `Kaleb Elwert <https://github.com/belak>`_
- `Contributors <https://github.com/mopidy/mopidy-gmusic/graphs/contributors>`_


Changelog
=========

v2.0.0 (2016-11-2)
-------------------

- Require gmusicapi >= 10.1.
- Make search work for gmusicapi >= 10.0. (Fixes: #116, PR: #117)
- Enable search for accounts without All Access. (PR: #117)
- Require cachetools. (PR: #119)
- Caching should be more consistent. (Fixes: #63, PR: #122)
- Autodetect All Access if not specified in config. (PR: #123)
- General refactoring. (PR: #120, #121)
- Much faster playlist loading. (PR: #130)
- Library browse rewrite. (PR: #131)
- Add IFL playlist and improve radio caching. (PR: #135)


v1.0.0 (2015-10-23)
-------------------

- Require Mopidy >= 1.0.
- Require gmusicapi >= 6.0.
- Update to work with new playback API in Mopidy 1.0. (PR: #75)
- Update to work with new search API in Mopidy 1.0.
- Fix crash when tracks lack album or artist information. (Fixes: #74, PR: #24,
  also thanks to PRs #27, #64)
- Log error on login failure instead of swallowing the error. (PR: #36)
- Add support for All Access search and lookup (PR: #34)
- Add dynamic playlist based on top rated tracks.
- Add support for radio stations in browser and/or as playlists.
- Add support for browsing artists and albums in the cached library.
- Add cover art to ``Album.images`` model field.
- Add background refreshing of library and playlists. (Fixes: #21)
- Fix authentication issues. (Fixes: #82, #87)
- Add LRU cache for All Access albums and tracks.
- Increment Google's play count if 50% or 240s of the track has been played.
  (PR: #51, and later changes)
- Let gmusicapi use the device's MAC address as device ID by default.
- Fix increasing of play counts in Google Play Music. (Fixes: #96)
- Fix scrobbling of tracks to Last.fm through Mopidy-Scrobbler. (Fixes: #60)
- Fix unhandled crashes on network connectivity issues. (Fixes: #85)
- Add ``gmusic/bitrate`` config to select streaming bitrate.


v0.3.0 (2014-01-28)
-------------------

- Issue #19: Public playlist support
- Issue #16: All playlist files are playable now
- Require Mopidy >= 0.18.


v0.2.2 (2013-11-11)
-------------------

- Issue #17: Fixed a bug regarding various artist albums
  (compilations)
- Issue #18: Fixed Google Music API playlist call for version 3.0.0
- Issue #16 (partial): All Access tracks in playlists are playable now


v0.2.1 (2013-10-11)
-------------------

- Issue #15: Fixed a bug regarding the translation of Google album
  artists to Mopidy album artists


v0.2 (2013-10-11)
-----------------

- Issue #12: Now able to play music from Google All Access
- Issue #9: Switched to the Mobileclient API of Google Music API
- Issue #4: Generate Album and Artist Search Results


v0.1.1 (2013-09-23)
-------------------

- Issue #11: Browsing the library fixed by implementing find_exact()


v0.1 (2013-09-16)
-----------------

- Initial release
