# vim:ts=4:sts=4:sw=4:expandtab

import appdirs
import argparse
import configparser
import json
import logging
import os

from .parse import parse_memory, parse_time, parse_int, parse_float
from .settings import CONFIG_APP_NAME, CONFIG_APP_AUTHOR, CONFIG_FILE, CONFIG_SERVER, CONFIG_REPOSITORY, FOREMAN_INTERVAL, FOREMAN_CONCURENCY

class KolejkaConfig:
    def __init__(self, config_path=None, config=None, args=None, **kwargs):
        if args is None:
            args = dict()
        if isinstance(args, argparse.Namespace):
            args = args.__dict__
        args.update(kwargs)
        self.client = argparse.Namespace()
        self.foreman = argparse.Namespace()
        self.workman = argparse.Namespace()
        self.config_path = config_path
        self.config = config 
        raw_config = dict()
        if self.config_path is None:
            self.config_path = args.get('config_path', None)
        if self.config_path is None:
            conf_dirs = appdirs.AppDirs(CONFIG_APP_NAME, CONFIG_APP_AUTHOR, multipath=True)
            check_dirs = conf_dirs.user_config_dir.split(':')
            check_dirs += conf_dirs.site_config_dir.split(':')
            for path in check_dirs:
                check_path = os.path.join(path, CONFIG_FILE)
                if os.path.isfile(check_path):
                    self.config_path = check_path
                    break
        if self.config_path is not None:
            parser = configparser.ConfigParser()
            parser.read(self.config_path)
            raw_config = dict( [ (k, dict(v)) for (k, v) in parser.items() ] )
        if self.config is None:
            self.config = args.get('config', None)
        default_config = raw_config.get('default', dict())
        default_config.update(args)
        if self.config is None:
            self.config = default_config.get('config', 'client')
        logging.info('Using config {} in {} {}'.format(self.config, self.config_path, args))
        if self.config is not None and self.config not in raw_config:
            logging.warning('Config {} not found in config file {}'.format(self.config, self.config_path))
        client_config = raw_config.get(self.config, dict())
        foreman_config = raw_config.get('foreman', dict())
        workman_config = raw_config.get('workman', dict())

        self.client.__setattr__('server', client_config.get('server', default_config.get('server', None) or CONFIG_SERVER))
        self.client.__setattr__('repository', client_config.get('repository', default_config.get('repository', None) or CONFIG_REPOSITORY))
        self.client.__setattr__('username', client_config.get('username', default_config.get('username', None)))
        self.client.__setattr__('password', client_config.get('password', default_config.get('password', None)))

        self.foreman.__setattr__('temp_path', foreman_config.get('temp', default_config.get('temp', None)))
        self.foreman.__setattr__('interval', parse_float(foreman_config.get('interval', default_config.get('interval', None) or FOREMAN_INTERVAL)))
        self.foreman.__setattr__('concurency', parse_int(foreman_config.get('concurency', default_config.get('concurency', None) or FOREMAN_CONCURENCY)))
        self.foreman.__setattr__('cpus', parse_int(foreman_config.get('cpus', default_config.get('cpus', None))))
        self.foreman.__setattr__('memory', parse_memory(foreman_config.get('memory', default_config.get('memory', None))))
        self.foreman.__setattr__('storage', parse_memory(foreman_config.get('storage', default_config.get('storage', None))))
        self.foreman.__setattr__('pids', parse_int(foreman_config.get('pids', default_config.get('pids', None))))
        self.foreman.__setattr__('time', parse_time(foreman_config.get('time', default_config.get('time', None))))

        self.workman.__setattr__('temp_path', workman_config.get('temp', default_config.get('temp', None)))
        self.workman.__setattr__('repository', client_config.get('repository', default_config.get('repository', None) or CONFIG_REPOSITORY))
        self.workman.__setattr__('cpus', parse_int(workman_config.get('cpus', default_config.get('cpus', None))))
        self.workman.__setattr__('memory', parse_memory(workman_config.get('memory', default_config.get('memory', None))))
        self.workman.__setattr__('storage', parse_memory(workman_config.get('storage', default_config.get('storage', None))))
        self.workman.__setattr__('pids', parse_int(workman_config.get('pids', default_config.get('pids', None))))
        self.workman.__setattr__('time', parse_time(workman_config.get('time', default_config.get('time', None))))

_config = None
def _configure(config_path=None, config=None, args=None, **kwargs):
    global _config
    if _config is None:
        _config = KolejkaConfig(config_path=config_path, config=config, args=args, **kwargs)

def kolejka_config(config_path=None, config=None, args=None, **kwargs):
    _configure(config_path=config_path, config=config, args=args, **kwargs)
    return _config

def client_config(config_path=None, config=None, args=None, **kwargs):
    _configure(config_path=config_path, config=config, args=args, **kwargs)
    logging.debug('Client config : {}'.format(_config.client.__dict__))
    return _config.client

def foreman_config(config_path=None, config=None, args=None, **kwargs):
    _configure(config_path=config_path, config=config, args=args, **kwargs)
    logging.debug('Foreman config : {}'.format(_config.foreman.__dict__))
    return _config.foreman
        
def worker_config(config_path=None, config=None, args=None, **kwargs):
    _configure(config_path=config_path, config=config, args=args, **kwargs)
    logging.debug('Worker config : {}'.format(_config.worker.__dict__))
    return _config.worker
