# vim:ts=4:sts=4:sw=4:expandtab

def main():
    import os
    import sys
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kolejka.server.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
