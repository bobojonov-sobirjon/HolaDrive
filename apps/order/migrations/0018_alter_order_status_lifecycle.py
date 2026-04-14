from django.db import migrations, models


def forwards_order_status(apps, schema_editor):
    Order = apps.get_model('order', 'Order')
    Order.objects.filter(status='confirmed').update(status='accepted')
    Order.objects.filter(status='refunded').update(status='cancelled')
    Order.objects.filter(status='failed').update(status='rejected')


def backwards_order_status(apps, schema_editor):
    Order = apps.get_model('order', 'Order')
    Order.objects.filter(status='accepted').update(status='confirmed')
    Order.objects.filter(status='rejected').update(status='failed')
    Order.objects.filter(status__in=('on_the_way', 'arrived')).update(status='confirmed')


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0017_add_payment_type'),
    ]

    operations = [
        migrations.RunPython(forwards_order_status, backwards_order_status),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('accepted', 'Accepted'),
                    ('on_the_way', 'On the way'),
                    ('arrived', 'Arrived'),
                    ('in_progress', 'In progress'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
