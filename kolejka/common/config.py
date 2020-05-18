# vim:ts=4:sts=4:sw=4:expandtab

import appdirs
import argparse
import configparser
import json
import logging
import os

from .parse import parse_memory, parse_time, parse_bool, parse_int, parse_float, parse_str_list
from .settings import CONFIG_APP_NAME, CONFIG_APP_AUTHOR, CONFIG_FILE, CONFIG_SERVER, FOREMAN_INTERVAL, FOREMAN_CONCURENCY
from .tags import foreman_auto_tags

class KolejkaConfig:
    def __init__(self, config_file=None, config=None, args=None, **kwargs):
        if args is None:
            args = dict()
        if isinstance(args, argparse.Namespace):
            args = args.__dict__
        args.update(kwargs)
        args = dict( [ (k,v) for k,v in args.items() if v is not None ] )
        self.client = argparse.Namespace()
        self.foreman = argparse.Namespace()
        self.worker = argparse.Namespace()
        self.config_file = config_file
        self.config = config 
        raw_config = dict()
        if self.config_file is None:
            self.config_file = args.get('config_file', None)
        if self.config_file is None:
            conf_dirs = appdirs.AppDirs(CONFIG_APP_NAME, CONFIG_APP_AUTHOR, multipath=True)
            check_dirs = conf_dirs.user_config_dir.split(':')
            check_dirs += [ os.path.join('/etc', CONFIG_APP_NAME) ]
            check_dirs += conf_dirs.site_config_dir.split(':')
            logging.debug('Looking for configuration in {}'.format(check_dirs))
            for path in check_dirs:
                check_path = os.path.join(path, CONFIG_FILE)
                if os.path.isfile(check_path):
                    self.config_file = check_path
                    break
        if self.config_file is not None:
            parser = configparser.ConfigParser()
            parser.read(self.config_file)
            raw_config = dict( [ (k, dict(v)) for (k, v) in parser.items() ] )
        if self.config is None:
            self.config = args.get('config', None)
        default_config = raw_config.get('default', dict())
        default_config.update(args)
        if self.config is None:
            self.config = default_config.get('config', 'client')
        logging.info('Using config {} in {} {}'.format(self.config, self.config_file, args))
        if self.config is not None and self.config not in raw_config:
            logging.warning('Config {} not found in config file {}'.format(self.config, self.config_file))
        client_config = raw_config.get(self.config, dict())
        foreman_config = raw_config.get('foreman', dict())
        worker_config = raw_config.get('worker', dict())

        self.client.__setattr__('server', client_config.get('server', default_config.get('server', None) or CONFIG_SERVER))
        self.client.__setattr__('username', client_config.get('username', default_config.get('username', None)))
        self.client.__setattr__('password', client_config.get('password', default_config.get('password', None)))
        self.client.__setattr__('cpus', parse_int(client_config.get('cpus', default_config.get('cpus', None))))
        self.client.__setattr__('memory', parse_memory(client_config.get('memory', default_config.get('memory', None))))
        self.client.__setattr__('swap', parse_memory(client_config.get('swap', default_config.get('swap', None))))
        self.client.__setattr__('storage', parse_memory(client_config.get('storage', default_config.get('storage', None))))
        self.client.__setattr__('image', parse_memory(client_config.get('image', default_config.get('image', None))))
        self.client.__setattr__('workspace', parse_memory(client_config.get('workspace', default_config.get('workspace', None))))
        self.client.__setattr__('pids', parse_int(client_config.get('pids', default_config.get('pids', None))))
        self.client.__setattr__('time', parse_time(client_config.get('time', default_config.get('time', None))))
        self.client.__setattr__('network', parse_bool(client_config.get('network', default_config.get('network', None))))

        self.foreman.__setattr__('temp_path', foreman_config.get('temp', default_config.get('temp', None)))
        self.foreman.__setattr__('interval', parse_float(foreman_config.get('interval', default_config.get('interval', None) or FOREMAN_INTERVAL)))
        self.foreman.__setattr__('concurency', parse_int(foreman_config.get('concurency', default_config.get('concurency', None) or FOREMAN_CONCURENCY)))
        self.foreman.__setattr__('pull', parse_bool(foreman_config.get('pull', default_config.get('pull', None) or False)))
        self.foreman.__setattr__('cpus', parse_int(foreman_config.get('cpus', default_config.get('cpus', None))))
        self.foreman.__setattr__('memory', parse_memory(foreman_config.get('memory', default_config.get('memory', None))))
        self.foreman.__setattr__('swap', parse_memory(foreman_config.get('swap', default_config.get('swap', None))))
        self.foreman.__setattr__('storage', parse_memory(foreman_config.get('storage', default_config.get('storage', None))))
        self.foreman.__setattr__('image', parse_memory(foreman_config.get('image', default_config.get('image', None))))
        self.foreman.__setattr__('workspace', parse_memory(foreman_config.get('workspace', default_config.get('workspace', None))))
        self.foreman.__setattr__('pids', parse_int(foreman_config.get('pids', default_config.get('pids', None))))
        self.foreman.__setattr__('time', parse_time(foreman_config.get('time', default_config.get('time', None))))
        self.foreman.__setattr__('network', parse_bool(foreman_config.get('network', default_config.get('network', None))))
        self.foreman.__setattr__('auto_tags', parse_bool(foreman_config.get('auto_tags', default_config.get('auto_tags', []))))
        tags = parse_str_list(foreman_config.get('tags', default_config.get('tags', None) or []))
        if self.foreman.auto_tags:
            tags = set(tags)
            tags.update(foreman_auto_tags())
            tags = list(tags)
        self.foreman.__setattr__('tags', tags)

        self.worker.__setattr__('debug', parse_bool(worker_config.get('debug', default_config.get('debug', None) or False)))
        self.worker.__setattr__('verbose', parse_bool(worker_config.get('verbose', default_config.get('verbose', None) or False)))
        self.worker.__setattr__('temp_path', worker_config.get('temp', default_config.get('temp', None)))
        self.worker.__setattr__('pull', parse_bool(worker_config.get('pull', default_config.get('pull', None) or False)))
        self.worker.__setattr__('cpus', parse_int(worker_config.get('cpus', default_config.get('cpus', None))))
        self.worker.__setattr__('memory', parse_memory(worker_config.get('memory', default_config.get('memory', None))))
        self.worker.__setattr__('swap', parse_memory(worker_config.get('swap', default_config.get('swap', None))))
        self.worker.__setattr__('storage', parse_memory(worker_config.get('storage', default_config.get('storage', None))))
        self.worker.__setattr__('image', parse_memory(worker_config.get('image', default_config.get('image', None))))
        self.worker.__setattr__('workspace', parse_memory(worker_config.get('workspace', default_config.get('workspace', None))))
        self.worker.__setattr__('pids', parse_int(worker_config.get('pids', default_config.get('pids', None))))
        self.worker.__setattr__('time', parse_time(worker_config.get('time', default_config.get('time', None))))
        self.worker.__setattr__('network', parse_bool(worker_config.get('network', default_config.get('network', None))))

_config = None
def _configure(config_file=None, config=None, args=None, **kwargs):
    global _config
    if _config is None:
        _config = KolejkaConfig(config_file=config_file, config=config, args=args, **kwargs)

def kolejka_config(config_file=None, config=None, args=None, **kwargs):
    _configure(config_file=config_file, config=config, args=args, **kwargs)
    return _config

def client_config(config_file=None, config=None, args=None, **kwargs):
    _configure(config_file=config_file, config=config, args=args, **kwargs)
    logging.debug('Client config : {}'.format(_config.client.__dict__))
    return _config.client

def foreman_config(config_file=None, config=None, args=None, **kwargs):
    _configure(config_file=config_file, config=config, args=args, **kwargs)
    logging.debug('Foreman config : {}'.format(_config.foreman.__dict__))
    return _config.foreman
        
def worker_config(config_file=None, config=None, args=None, **kwargs):
    _configure(config_file=config_file, config=config, args=args, **kwargs)
    logging.debug('Worker config : {}'.format(_config.worker.__dict__))
    return _config.worker
