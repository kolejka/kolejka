# vim:ts=4:sts=4:sw=4:expandtab

from django.conf import settings

from django.core.management.base import BaseCommand, CommandError

import django.utils.timezone

from kolejka.server.task.models import Task
from kolejka.common.parse import TimeAction, parse_time

class Command(BaseCommand):
    help = 'List tasks'
    
    def add_arguments(self, parser):
        parser.add_argument('--assigned', type=bool)
        parser.add_argument('--resolved', type=bool)

    def handle(self, *args, **options):
        filter = dict()
        if options['assigned'] is not None:
            filter['assignee__isnull'] = not options['assigned']
        if options['resolved'] is not None:
            filter['result__isnull'] = not options['resolved']
        for task in Task.objects.filter(**filter):
            self.stdout.write(f'{task.key}\n')
