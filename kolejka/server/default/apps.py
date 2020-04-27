from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_groups(**kwargs):
    from django.contrib.auth.models import Group, Permission
    
    groups = {
        'Clients'    : [ 'task.add_task', 'blob.add_reference', 'blob.view_reference', 'blob.view_blob', ],
        'Processors' : [ 'task.process_task', 'blob.add_reference', 'blob.view_reference', 'blob.view_blob', ],
        'Inspectors' : [ 'blob.view_reference', 'blob.view_blob', 'task.view_task', 'task.view_result', ],
        'Managers'   : [ 'blob.view_reference', 'blob.delete_reference', 'blob.view_blob', 'blob.delete_blob', 'task.view_task', 'task.delete_task', 'task.view_result', 'task.delete_result', ],
    }

    for group_name, privileges in groups.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        for perm in privileges:
            app_label = perm.split('.')[0]
            codename = perm.split('.')[1]
            try:
                permission = Permission.objects.get(codename=codename, content_type__app_label=app_label)
                group.permissions.add(permission)
            except:
                return
        group.save()

class DefaultConfig(AppConfig):
    name='kolejka.server.default'
    def ready(self):
        post_migrate.connect(
            create_groups,
            dispatch_uid='kolejka.server.default.apps.create_groups'
        )
