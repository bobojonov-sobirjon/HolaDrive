from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0028_perf_indexes_accept_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('scheduled', 'Scheduled'),
                    ('pending', 'Pending'),
                    ('accepted', 'Accepted'),
                    ('on_the_way', 'On the way'),
                    ('arrived', 'Arrived'),
                    ('in_progress', 'In progress'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='orderschedule',
            name='scheduled_at',
            field=models.DateTimeField(
                blank=True,
                help_text='ISO instant the rider picked (pickup_at or arrive-by).',
                null=True,
                verbose_name='Rider chosen datetime',
            ),
        ),
        migrations.AddField(
            model_name='orderschedule',
            name='pickup_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the driver should collect the rider (dispatch clock).',
                null=True,
                verbose_name='Pickup datetime',
            ),
        ),
        migrations.AddField(
            model_name='orderschedule',
            name='dropoff_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Arrive-by datetime',
            ),
        ),
        migrations.AddField(
            model_name='orderschedule',
            name='dispatched_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='orderschedule',
            index=models.Index(fields=['pickup_at'], name='ord_sched_pickup_at_idx'),
        ),
    ]
