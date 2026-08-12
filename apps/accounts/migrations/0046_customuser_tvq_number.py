# Generated manually for tvq_number (Canada provincial tax)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0045_loginlegaldocument'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='tvq_number',
            field=models.CharField(
                blank=True,
                help_text='Provincial tax number (TVQ / QST) — Quebec, Canada.',
                max_length=15,
                null=True,
                verbose_name='Tax Number (TVQ/QST)',
            ),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='tax_number',
            field=models.CharField(
                blank=True,
                help_text='Federal tax number (GST/HST) — Canada.',
                max_length=15,
                null=True,
                verbose_name='Tax Number (GST/HST)',
            ),
        ),
    ]
