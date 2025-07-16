#!/usr/bin/env python3
"""
Setup script for PyDomino Mac app bundling
"""

from setuptools import setup

APP = ['src/main.py']
DATA_FILES = [
    ('soundfonts', ['soundfonts/YamahaGrandPiano.sf2']),
]

OPTIONS = {
    'argv_emulation': True,
    'iconfile': None,  # Will add icon later
    'site_packages': True,
    'plist': {
        'CFBundleName': 'PyDomino',
        'CFBundleDisplayName': 'PyDomino',
        'CFBundleIdentifier': 'app.pydomino.PyDomino',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleInfoDictionaryVersion': '6.0',
        'LSMinimumSystemVersion': '10.15',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleDocumentTypes': [],
    },
    'packages': ['PySide6', 'src'],
    'includes': [
        'src.ui.main_window',
        'src.ui.piano_roll_widget', 
        'src.ui.virtual_keyboard_widget',
        'src.midi_routing',
        'src.audio_routing'
    ],
    'excludes': [
        'tkinter',
        'matplotlib',
        'scipy',
        'IPython',
        'PIL'
    ],
}

setup(
    name='PyDomino',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'PySide6>=6.5.0',
        'python-rtmidi>=1.5.0',
        'numpy>=1.24.0',
        'pyaudio>=0.2.11',
    ],
)