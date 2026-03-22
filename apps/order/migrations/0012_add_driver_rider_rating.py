# Generated manually for DriverRiderRating (driver rates rider)

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0011_add_order_chat'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverRiderRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(help_text='Rating from 1 to 5 stars', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='Rating')),
                ('comment', models.TextField(blank=True, help_text='Optional comment (Add comment screen)', null=True, verbose_name='Comment')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='approved', max_length=20, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('driver', models.ForeignKey(help_text='Driver who gave this rating', on_delete=django.db.models.deletion.CASCADE, related_name='rider_ratings_given', to=settings.AUTH_USER_MODEL, verbose_name='Driver')),
                ('order', models.OneToOneField(help_text='Completed order for this rating', on_delete=django.db.models.deletion.CASCADE, related_name='driver_rider_rating', to='order.order', verbose_name='Order')),
                ('feedback_tags', models.ManyToManyField(blank=True, help_text='Tags like Conversation, Calm, Kind, Punctual, Fun', related_name='driver_rider_ratings', to='order.ratingfeedbacktag', verbose_name='Feedback Tags')),
                ('rider', models.ForeignKey(help_text='Rider who received this rating', on_delete=django.db.models.deletion.CASCADE, related_name='rider_ratings_received', to=settings.AUTH_USER_MODEL, verbose_name='Rider')),
            ],
            options={
                'verbose_name': 'Driver Rider Rating',
                'verbose_name_plural': '14 Driver Rider Ratings',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='driverriderrating',
            index=models.Index(fields=['order'], name='dr_rider_rating_order_idx'),
        ),
        migrations.AddIndex(
            model_name='driverriderrating',
            index=models.Index(fields=['driver'], name='dr_rider_rating_driver_idx'),
        ),
        migrations.AddIndex(
            model_name='driverriderrating',
            index=models.Index(fields=['rider'], name='dr_rider_rating_rider_idx'),
        ),
    ]
