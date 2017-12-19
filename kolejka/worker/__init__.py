# vim:ts=4:sts=4:sw=4:expandtab

__import__('pkg_resources').declare_namespace('kolejka')

def main():
    import argparse
    import logging
    import setproctitle

    parser = argparse.ArgumentParser(description='KOLEJKA worker')
    parser.add_argument('-s', '--stage', type=int, default=0)
    parser.add_argument("-t", "--task", type=str, default='TASK', help='task folder')
    parser.add_argument("-r", "--result", type=str, default='RESULT', help='result folder')
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help='show more info')
    parser.add_argument("-d", "--debug", action="store_true", default=False, help='show debug info')
    parser.add_argument("--temp", type=str, default=None, help='temporary directory')
    args = parser.parse_args()
    level=logging.WARNING
    if args.verbose:
        level=logging.INFO
    if args.debug:
        level=logging.DEBUG
    logging.basicConfig(level=level)
    setproctitle.setproctitle('kolejka-worker')
    if args.stage == 0:
        from kolejka.worker.stage0 import stage0
        stage0(args.task, args.result, args.temp)
    elif args.stage == 2:
        from kolejka.worker.stage2 import stage2
        stage2(args.task, args.result)

if __name__ == '__main__':
    main()
