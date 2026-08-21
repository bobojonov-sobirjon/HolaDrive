from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0047_phone_max_length_international'),
    ]

    operations = [
        migrations.AlterField(
            model_name='verificationcode',
            name='code',
            field=models.CharField(max_length=8, verbose_name='Verification Code'),
        ),
        migrations.AlterField(
            model_name='pinverificationforuser',
            name='pin',
            field=models.CharField(help_text='Hashed 4-digit PIN', max_length=128, verbose_name='PIN'),
        ),
        migrations.RemoveIndex(
            model_name='pinverificationforuser',
            name='pin_code_idx',
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['is_online', 'is_active'], name='user_online_active_idx'),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['latitude', 'longitude'], name='user_lat_lon_idx'),
        ),
    ]
