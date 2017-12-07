# vim:ts=4:sts=4:sw=4:expandtab

import appdirs
import json
import os

APP_NAME = 'kolejka'
APP_AUTHOR = 'matinf.uj.edu.pl'
APP_DIRS = appdirs.AppDirs(APP_NAME, APP_AUTHOR, multipath=True)
CONFIG_FILE = 'kolejka.conf'
CONFIG_PATHS = [ os.path.join(d, CONFIG_FILE) for d in ['.'] + APP_DIRS.user_config_dir.split(':') + APP_DIRS.site_config_dir.split(':') ]

def autoconfig():
    settings = {
        'app_name' : APP_NAME,
        'instance' : 'http://kolejka.matinf.uj.edu.pl:8000',
    }

    for config_path in CONFIG_PATHS:
        if os.path.isfile(config_path):
            settings['config_path'] = config_path
            with open(config_path, 'r') as config_file:
                settings.update(json.load(config_file))
            break
    return settings
