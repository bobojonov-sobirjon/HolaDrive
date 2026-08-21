from django.db import migrations, models


def dedupe_accepted_order_drivers(apps, schema_editor):
    OrderDriver = apps.get_model('order', 'OrderDriver')
    seen = set()
    qs = OrderDriver.objects.filter(status='accepted').order_by('order_id', 'id')
    for row in qs.iterator():
        if row.order_id in seen:
            row.status = 'rejected'
            row.save(update_fields=['status'])
        else:
            seen.add(row.order_id)


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0027_initial_safety_tools'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user', 'status'], name='order_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', 'created_at'], name='order_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='orderdriver',
            index=models.Index(fields=['driver', 'status'], name='order_driver_drv_st_idx'),
        ),
        migrations.AddIndex(
            model_name='orderdriver',
            index=models.Index(fields=['order', 'status'], name='order_driver_ord_st_idx'),
        ),
        migrations.RunPython(dedupe_accepted_order_drivers, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='orderdriver',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status', 'accepted')),
                fields=('order',),
                name='unique_accepted_driver_per_order',
            ),
        ),
    ]
