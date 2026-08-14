# Generated for phone max_length bump (international E.164)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0046_customuser_tvq_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='phone_number',
            field=models.CharField(
                blank=True,
                help_text='Optional. Enter your phone number.',
                max_length=20,
                null=True,
                verbose_name='Phone Number',
            ),
        ),
        migrations.AlterField(
            model_name='verificationcode',
            name='phone_number',
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                verbose_name='Phone Number',
            ),
        ),
    ]
