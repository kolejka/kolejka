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
    help = 'Used to change password.'
    requires_migrations_checks = True
    requires_system_checks = False

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
            '%s' % PASSWORD_FIELD,
            help='Specifies the password for the user.',
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Default is "default".',
        )

    def handle(self, *args, **options):
        username = options[self.UserModel.USERNAME_FIELD]
        password = options[PASSWORD_FIELD]
        database = options['database']
        try:
            u = self.UserModel._default_manager.using(options['database']).get(**{
                self.UserModel.USERNAME_FIELD: username
            })
        except self.UserModel.DoesNotExist:
            raise CommandError("user '%s' does not exist" % username)
        u.set_password(password)
        u.save()

        return "Password changed successfully for user '%s'" % u
