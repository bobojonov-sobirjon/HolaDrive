from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0041_customuser_stripe_connect_account_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="stripe_customer_id",
            field=models.CharField(
                blank=True,
                help_text="Stripe Customer id (cus_…) used for saving cards / charging rider trips.",
                max_length=255,
                verbose_name="Stripe Customer id",
            ),
        ),
    ]

