from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('order', '0029_scheduled_rides'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedRider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=255, verbose_name='Full Name')),
                ('email', models.EmailField(blank=True, default='', max_length=255, verbose_name='Email')),
                ('phone_number', models.CharField(max_length=32, verbose_name='Phone Number')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'owner',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='saved_riders',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Owner',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Saved Rider',
                'verbose_name_plural': '04c Saved Riders',
                'ordering': ['-updated_at', '-id'],
            },
        ),
        migrations.AddField(
            model_name='order',
            name='booked_for',
            field=models.CharField(
                choices=[('me', 'Me'), ('someone_else', 'Someone else')],
                default='me',
                help_text='me = logged-in rider is the passenger; someone_else = guest passenger (payer is still user).',
                max_length=20,
                verbose_name='Booked for',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='guest_email',
            field=models.EmailField(blank=True, default='', max_length=255, verbose_name='Guest email'),
        ),
        migrations.AddField(
            model_name='order',
            name='guest_full_name',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Guest full name'),
        ),
        migrations.AddField(
            model_name='order',
            name='guest_phone_number',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='Guest phone'),
        ),
        migrations.AddField(
            model_name='order',
            name='saved_rider',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='orders',
                to='order.savedrider',
                verbose_name='Saved rider',
            ),
        ),
        migrations.AddConstraint(
            model_name='savedrider',
            constraint=models.UniqueConstraint(
                fields=('owner', 'phone_number'),
                name='saved_rider_owner_phone_uniq',
            ),
        ),
        migrations.AddIndex(
            model_name='savedrider',
            index=models.Index(fields=['owner', 'updated_at'], name='saved_rider_owner_upd_idx'),
        ),
    ]
