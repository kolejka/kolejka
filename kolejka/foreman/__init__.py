# vim:ts=4:sts=4:sw=4:expandtab

def main():
    import argparse
    import logging
    import setproctitle
    from kolejka.foreman.foreman import config_parser as foreman_parser

    setproctitle.setproctitle('kolejka-foreman')
    parser = argparse.ArgumentParser(description='KOLEJKA foreman')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='show more info')
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='show debug info')
    parser.add_argument('--config-file', help='config file')
    parser.add_argument('--config', help='config')
    foreman_parser(parser)
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
