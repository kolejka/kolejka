# vim:ts=4:sts=4:sw=4:expandtab

from kolejka.common.cgroups import ControlGroupSystem
from kolejka.common.http_socket import HTTPUnixServer, HTTPUnixConnection
from kolejka.common.parse import TimeAction, MemoryAction, parse_time, parse_memory

from kolejka.common.config import KolejkaConfig, kolejka_config, client_config, foreman_config, worker_config
from kolejka.common.limits import KolejkaLimits, KolejkaStats
from kolejka.common.task import KolejkaTask, KolejkaResult

def main():
    import argparse
    import logging
    import setproctitle

    setproctitle.setproctitle('kolejka')
    parser = argparse.ArgumentParser(description='KOLEJKA')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='show more info')
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='show debug info')
    
    subparsers = parser.add_subparsers(dest='module')
    subparsers.required = True
    #CLIENT
    try:
        from kolejka.client.client import config_parser as client_parser
        subparser = subparsers.add_parser('client')
        client_parser(subparser)
    except:
        pass
    #FOREMAN
    try:
        from kolejka.foreman.foreman import config_parser as foreman_parser
        subparser = subparsers.add_parser('foreman')
        foreman_parser(subparser)
    except:
        pass
    #OBSERVER
    try:
        from kolejka.observer.server import config_parser as observer_parser
        subparser = subparsers.add_parser('observer')
        observer_parser(subparser)
    except:
        pass
    #WORKER
    try:
        from kolejka.worker import config_parser as worker_parser
        subparser = subparsers.add_parser('worker')
        worker_parser(subparser)
    except:
        pass

    args = parser.parse_args()
    level=logging.WARNING
    if args.verbose:
        level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logging.basicConfig(level = level)
    args.execute(args)

if __name__ == '__main__':
    main()
