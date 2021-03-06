# Generated by Django 3.0.5 on 2020-04-22 09:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Blob',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True)),
                ('active', models.BooleanField(default=True)),
                ('size', models.BigIntegerField()),
                ('time_create', models.DateTimeField(auto_now_add=True)),
                ('time_access', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Reference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True)),
                ('time_create', models.DateTimeField(auto_now_add=True)),
                ('time_access', models.DateTimeField(auto_now=True)),
                ('permanent', models.BooleanField(default=False)),
                ('public', models.BooleanField(default=False)),
                ('blob', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='blob.Blob')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
