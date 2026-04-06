from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0033_legalpage_registration_terms_kind'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AcceptanceOfAgreement',
        ),
        migrations.DeleteModel(
            name='LegalPage',
        ),
    ]
