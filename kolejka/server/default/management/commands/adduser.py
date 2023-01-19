# vim:ts=4:sts=4:sw=4:expandtab
"""
Management utility to create users.
"""

from django.conf import settings

import getpass
import os
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import exceptions
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS

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
            self.username_field.name,
            help='Specifies the login for the user.',
        )
        parser.add_argument(
            PASSWORD_FIELD,
            help='Specifies the password for the user.',
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help=f'Specifies the database to use. Default is \'{DEFAULT_DB_ALIAS}\'.',
        )
        for field_name in self.UserModel.REQUIRED_FIELDS:
            field = self.UserModel._meta.get_field(field_name)
            if field.many_to_many:
                if field.remote_field.through and not field.remote_field.through._meta.auto_created:
                    raise CommandError(
                        f'Required field \'{field_name}\' specifies a many-to-many relation through model, which is not supported.'
                    )
                else:
                    parser.add_argument(
                        f'--{field_name}', action='append', required=True,
                        help=f'Specifies the {field_name} for the user. Can be used multiple times.',
                    )
            else:
                parser.add_argument(
                    f'--{field_name}', required=True, help=f'Specifies the {field_name} for the user.',
                )
        for group_name in [group.name.lower() for group in Group.objects.all()]:
            parser.add_argument(
                f'--{group_name}', action='store_true', help=f'Add user to group {group_name}.',
            )

    def handle(self, *args, **options):
        username = options[self.username_field.name]
        password = options[PASSWORD_FIELD]
        database = options['database']
        user_data = {}
        verbose_field_name = self.username_field.verbose_name
        user_data[self.username_field.name] = username
        user_data[PASSWORD_FIELD] = password
        try:
            for field_name in self.UserModel.REQUIRED_FIELDS:
                value = options[field_name]
                if not value:
                    raise CommandError(f'You must use --{field_name}.')
                field = self.UserModel._meta.get_field(field_name)
                user_data[field_name] = field.clean(value, None)

            user = self.UserModel._default_manager.db_manager(database).create_user(**user_data)

            for group in Group.objects.all():
                if options[group.name.lower()]:
                    user.groups.add(group)

        except exceptions.ValidationError as e:
            raise CommandError('; '.join(e.messages))
        return f'User \'{username}\' created successfully.'
