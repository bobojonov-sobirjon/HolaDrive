# Generated manually for GenericForeignKey parent link on agreement items.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('accounts', '0036_driver_identification_agreements_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='driveridentificationagreementsitems',
            name='content_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='+',
                to='contenttypes.contenttype',
            ),
        ),
        migrations.AddField(
            model_name='driveridentificationagreementsitems',
            name='object_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='driveridentificationagreementsitems',
            index=models.Index(fields=['content_type', 'object_id'], name='drv_id_agg_parent_idx'),
        ),
    ]
