# Generated by Django 3.0.5 on 2020-04-22 09:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('blob', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True)),
                ('description', models.TextField()),
                ('time_create', models.DateTimeField(auto_now_add=True)),
                ('time_assign', models.DateTimeField(null=True)),
                ('assignee', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kolejka_assignments', to=settings.AUTH_USER_MODEL)),
                ('files', models.ManyToManyField(to='blob.Reference')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kolejka_tasks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': [('process_task', 'Can process task')],
            },
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField()),
                ('time_create', models.DateTimeField(auto_now_add=True)),
                ('files', models.ManyToManyField(to='blob.Reference')),
                ('task', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='task.Task')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kolejka_results', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
