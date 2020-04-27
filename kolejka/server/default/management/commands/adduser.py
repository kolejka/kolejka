"""
Management utility to create users.
"""
import getpass
import os
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import exceptions
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS
from django.utils.text import capfirst


PASSWORD_FIELD = 'password'


class Command(BaseCommand):
    help = 'Used to create a user.'
    requires_migrations_checks = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UserModel = get_user_model()
        self.username_field = self.UserModel._meta.get_field(self.UserModel.USERNAME_FIELD)

    def add_arguments(self, parser):
        parser.add_argument(
            '%s' % self.UserModel.USERNAME_FIELD,
            help='Specifies the login for the user.',
        )
        parser.add_argument(
            '--%s' % PASSWORD_FIELD,
            help='Specifies the password for the user.',
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Default is "default".',
        )
        for field_name in self.UserModel.REQUIRED_FIELDS:
            field = self.UserModel._meta.get_field(field_name)
            if field.many_to_many:
                if field.remote_field.through and not field.remote_field.through._meta.auto_created:
                    raise CommandError(
                        "Required field '%s' specifies a many-to-many "
                        "relation through model, which is not supported."
                        % field_name
                    )
                else:
                    parser.add_argument(
                        '--%s' % field_name, action='append', required=True,
                        help=(
                            'Specifies the %s for the user. Can be used '
                            'multiple times.' % field_name,
                        ),
                    )
            else:
                parser.add_argument(
                    '--%s' % field_name, required=True,
                    help='Specifies the %s for the user.' % field_name,
                )
        for group_name in [group.name.lower() for group in Group.objects.all()]:
            parser.add_argument(
                '--%s' % group_name, action='store_true',
                help=(
                    'Add user to group %s.' % group_name,
                ),
            )

    def handle(self, *args, **options):
        username = options[self.UserModel.USERNAME_FIELD]
        database = options['database']
        user_data = {}
        verbose_field_name = self.username_field.verbose_name
        user_data[self.UserModel.USERNAME_FIELD] = username
        user_data[PASSWORD_FIELD] = options[PASSWORD_FIELD]
        try:
            for field_name in self.UserModel.REQUIRED_FIELDS:
                value = options[field_name]
                if not value:
                    raise CommandError('You must use --%s' % field_name)
                field = self.UserModel._meta.get_field(field_name)
                user_data[field_name] = field.clean(value, None)

            user = self.UserModel._default_manager.db_manager(database).create_user(**user_data)

            for group in Group.objects.all():
                if options[group.name.lower()]:
                    user.groups.add(group)

            if options['verbosity'] >= 1:
                self.stdout.write("User created successfully.")
        except exceptions.ValidationError as e:
            raise CommandError('; '.join(e.messages))

