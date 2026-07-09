from django.db import migrations, models


def apply_figma_sort_order(apps, schema_editor):
    RideType = apps.get_model('order', 'RideType')
    order_by_slug = {
        'hola': 1,
        'hola_large': 2,
        'premium': 3,
        'premium_large': 4,
        'hola_ev': 5,
        'hola_ev_large': 6,
        'Economy': 1,
        'Comfort': 2,
        'XL': 2,
    }
    for slug, sort_order in order_by_slug.items():
        RideType.objects.filter(name=slug).update(sort_order=sort_order)
    # Match by display label when slug differs
    label_order = {
        'Hola': 1,
        'Hola Large': 2,
        'Premium': 3,
        'Premium Large': 4,
        'Hola EV': 5,
        'Hola EV Large': 6,
    }
    for label, sort_order in label_order.items():
        RideType.objects.filter(name_large=label).update(sort_order=sort_order)


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0025_latlon_precision_18'),
    ]

    operations = [
        migrations.AddField(
            model_name='ridetype',
            name='sort_order',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Display order in rider app and admin (lower = first). Figma: Hola → Hola Large → Premium → …',
                verbose_name='Sort order',
            ),
        ),
        migrations.AddIndex(
            model_name='ridetype',
            index=models.Index(fields=['sort_order'], name='ride_type_sort_idx'),
        ),
        migrations.AddIndex(
            model_name='ridetype',
            index=models.Index(fields=['is_active', 'sort_order'], name='ride_type_active_sort_idx'),
        ),
        migrations.RunPython(apply_figma_sort_order, migrations.RunPython.noop),
    ]
