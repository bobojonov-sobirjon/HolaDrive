from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0043_customuser_latlon_precision'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='firebase_uid',
            field=models.CharField(
                blank=True,
                help_text='Firebase Authentication user id (Google / Apple / Facebook via Firebase).',
                max_length=128,
                null=True,
                unique=True,
                verbose_name='Firebase UID',
            ),
        ),
        migrations.AddIndex(
            model_name='customuser',
            index=models.Index(fields=['firebase_uid'], name='user_firebase_uid_idx'),
        ),
    ]
