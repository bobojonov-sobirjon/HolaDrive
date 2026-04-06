from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0030_termsandconditionsacceptance')]
    operations = [
        migrations.AddField(
            model_name='legalpage',
            name='page_kind',
            field=models.CharField(
                choices=[('terms', 'Terms and conditions'), ('legal_agreement', 'Legal agreement')],
                default='legal_agreement',
                help_text='terms = full T&C flow; legal_agreement = bulk list (Hola Agreement 1, 2)',
                max_length=30,
                verbose_name='Page kind',
            ),
        ),
    ]
