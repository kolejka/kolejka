from django.core.management.base import BaseCommand, CommandError

import django.utils.timezone

from kolejka.server.task.models import Task
from kolejka.common.parse import TimeAction, parse_time
from kolejka.server import settings

class Command(BaseCommand):
    help = 'Unassigns overdue tasks'
    
    def add_arguments(self, parser):
        parser.add_argument('time', action=TimeAction, help='time')

    def handle(self, *args, **options):
        count = Task.objects.filter(result__isnull=True, assignee__isnull=False, time_assign__lt=django.utils.timezone.now() - options['time']).update(assignee=None, time_assign=None)
        if count:
            self.stdout.write(self.style.SUCCESS('Successfully unassigned %d tasks' % count))
