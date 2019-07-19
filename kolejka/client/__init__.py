# vim:ts=4:sts=4:sw=4:expandtab

from kolejka.client.client import KolejkaClient

def main():
    import argparse
    import logging
    import setproctitle
    from kolejka.client.client import config_parser as client_parser

    setproctitle.setproctitle('kolejka-client')
    parser = argparse.ArgumentParser(description='KOLEJKA client')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='show more info')
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='show debug info')
    parser.add_argument('--config-file', help='config file')
    parser.add_argument('--config', help='config')
    client_parser(parser)
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
