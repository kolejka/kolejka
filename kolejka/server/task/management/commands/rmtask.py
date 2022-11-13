# vim:ts=4:sts=4:sw=4:expandtab

from django.conf import settings

from django.core.management.base import BaseCommand, CommandError

import django.utils.timezone

from kolejka.server.task.models import Task
from kolejka.common.parse import TimeAction, parse_time

class Command(BaseCommand):
    help = 'Remove tasks'
    
    def add_arguments(self, parser):
        parser.add_argument('task_keys', nargs='+')

    def handle(self, *args, **options):
        count = 0
        for task_key in options['task_keys']:
            try:
                task = Task.objects.get(key=task_key)
                task.delete()
                count += 1
            except Task.DoesNotExist:
                pass
        if count:
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} tasks'))
