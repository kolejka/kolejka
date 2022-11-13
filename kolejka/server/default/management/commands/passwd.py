# vim:ts=4:sts=4:sw=4:expandtab
"""
Management utility to change passwords.
"""

from django.conf import settings

import getpass
import os
import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS

PASSWORD_FIELD = 'password'

class Command(BaseCommand):
    help = 'Used to change a password.'

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

    def handle(self, *args, **options):
        username = options[self.username_field.name]
        password = options[PASSWORD_FIELD]
        database = options['database']
        try:
            u = self.UserModel._default_manager.using(database).get(**{
                self.username_field.name: username
            })
        except self.UserModel.DoesNotExist:
            raise CommandError(f'user \'{username}\' does not exist')
        u.set_password(password)
        u.save()

        return f'Password changed successfully for user \'{username}\'.'
