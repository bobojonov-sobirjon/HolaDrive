from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("order", "0022_merge_0019_orderitem_latlon_precision_0021_order_stripe_trip_payment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="surgepricing",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=14,
                max_digits=22,
                null=True,
                verbose_name="Latitude",
            ),
        ),
        migrations.AlterField(
            model_name="surgepricing",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=14,
                max_digits=22,
                null=True,
                verbose_name="Longitude",
            ),
        ),
    ]

