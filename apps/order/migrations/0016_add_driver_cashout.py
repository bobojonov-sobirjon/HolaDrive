import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('order', '0015_alter_ratingfeedbacktag_options'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='DriverCashout',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Amount')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cashouts', to=settings.AUTH_USER_MODEL, verbose_name='Driver')),
            ],
            options={'verbose_name': 'Driver Cashout', 'verbose_name_plural': '15 Driver Cashouts', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(model_name='drivercashout', index=models.Index(fields=['driver'], name='dr_cashout_driver_idx')),
        migrations.AddIndex(model_name='drivercashout', index=models.Index(fields=['status'], name='dr_cashout_status_idx')),
    ]
