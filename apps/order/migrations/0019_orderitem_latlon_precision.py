from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("order", "0018_alter_order_status_lifecycle"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="latitude_from",
            field=models.DecimalField(
                blank=True,
                decimal_places=14,
                max_digits=22,
                null=True,
                verbose_name="Latitude From",
            ),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="longitude_from",
            field=models.DecimalField(
                blank=True,
                decimal_places=14,
                max_digits=22,
                null=True,
                verbose_name="Longitude From",
            ),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="latitude_to",
            field=models.DecimalField(
                blank=True,
                decimal_places=14,
                max_digits=22,
                null=True,
                verbose_name="Latitude To",
            ),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="longitude_to",
            field=models.DecimalField(
                blank=True,
                decimal_places=14,
                max_digits=22,
                null=True,
                verbose_name="Longitude To",
            ),
        ),
    ]

