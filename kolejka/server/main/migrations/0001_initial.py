from django.db import migrations

def install_groups(apps, schema_editor):

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    
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
            permission = Permission.objects.get(codename=codename, content_type__app_label=app_label)
            group.permissions.add(permission)
        group.save()

class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.RunPython(install_groups),
    ]
