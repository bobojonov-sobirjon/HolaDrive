# Data migration: add Figma rider rating tags (Conversation, Calm, Kind, Punctual, Fun)

from django.db import migrations


RIDER_TAGS = [
    ('Conversation', 'positive'),
    ('Calm', 'positive'),
    ('Kind', 'positive'),
    ('Punctual', 'positive'),
    ('Fun', 'positive'),
]


def add_rider_tags(apps, schema_editor):
    RatingFeedbackTag = apps.get_model('order', 'RatingFeedbackTag')
    for name, tag_type in RIDER_TAGS:
        RatingFeedbackTag.objects.get_or_create(name=name, defaults={'tag_type': tag_type, 'is_active': True})


def remove_rider_tags(apps, schema_editor):
    RatingFeedbackTag = apps.get_model('order', 'RatingFeedbackTag')
    names = [n for n, _ in RIDER_TAGS]
    RatingFeedbackTag.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0012_add_driver_rider_rating'),
    ]

    operations = [
        migrations.RunPython(add_rider_tags, remove_rider_tags),
    ]
