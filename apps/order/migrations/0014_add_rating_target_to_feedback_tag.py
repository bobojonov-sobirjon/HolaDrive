# Add rating_target to RatingFeedbackTag: rider_to_driver vs driver_to_rider

from django.db import migrations, models


def set_driver_to_rider_tags(apps, schema_editor):
    RatingFeedbackTag = apps.get_model('order', 'RatingFeedbackTag')
    names = ['Conversation', 'Calm', 'Kind', 'Punctual', 'Fun']
    RatingFeedbackTag.objects.filter(name__in=names).update(rating_target='driver_to_rider')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0013_add_rider_rating_feedback_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='ratingfeedbacktag',
            name='rating_target',
            field=models.CharField(
                choices=[('rider_to_driver', 'Rider → Driver'), ('driver_to_rider', 'Driver → Rider')],
                default='rider_to_driver',
                help_text="rider_to_driver = rider driverga; driver_to_rider = driver riderga",
                max_length=20,
                verbose_name='Rating Target',
            ),
        ),
        migrations.AlterField(
            model_name='ratingfeedbacktag',
            name='name',
            field=models.CharField(help_text="Tag name (e.g., 'Professionalism', 'Poor route', 'Dirty')", max_length=100, verbose_name='Tag Name'),
        ),
        migrations.AlterUniqueTogether(
            name='ratingfeedbacktag',
            unique_together={('name', 'rating_target')},
        ),
        migrations.AddIndex(
            model_name='ratingfeedbacktag',
            index=models.Index(fields=['rating_target'], name='rating_tag_target_idx'),
        ),
        migrations.RunPython(set_driver_to_rider_tags, noop),
    ]
