from __future__ import unicode_literals

import re

from setuptools import find_packages, setup


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']


setup(
    name='Mopidy-GMusic',
    version=get_version('mopidy_gmusic/__init__.py'),
    url='https://github.com/mopidy/mopidy-gmusic',
    license='Apache License, Version 2.0',
    author='Ronald Hecht',
    author_email='ronald.hecht@gmx.de',
    description='Mopidy extension for playing music from Google Play Music',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'Mopidy >= 1.0',
        'Pykka >= 1.1',
        'gmusicapi >= 7.0.1',
        'requests >= 2.0',
    ],
    entry_points={
        'mopidy.ext': [
            'gmusic = mopidy_gmusic:GMusicExtension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
