from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0042_customuser_stripe_customer_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=14,
                help_text="Optional. Latitude of your location.",
                max_digits=22,
                null=True,
                verbose_name="Latitude",
            ),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=14,
                help_text="Optional. Longitude of your location.",
                max_digits=22,
                null=True,
                verbose_name="Longitude",
            ),
        ),
    ]

