from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('order', '0016_add_driver_cashout')]
    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_type',
            field=models.CharField(
                blank=True,
                choices=[('card', 'Card'), ('cash', 'Cash'), ('hola_wallet_cash', 'Hola Wallet Cash')],
                default='card',
                max_length=30,
                null=True,
                verbose_name='Payment Type',
            ),
        ),
        migrations.AddField(
            model_name='drivercashout',
            name='payment_type',
            field=models.CharField(
                choices=[('card', 'Card'), ('cash', 'Cash'), ('hola_wallet_cash', 'Hola Wallet Cash')],
                default='card',
                max_length=30,
                verbose_name='Payment Type',
            ),
        ),
    ]
