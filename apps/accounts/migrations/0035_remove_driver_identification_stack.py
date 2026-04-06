from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0034_remove_legalpage_and_acceptanceofagreement'),
    ]

    operations = [
        migrations.DeleteModel(name='DriverIdentificationUploadDocument'),
        migrations.DeleteModel(name='TermsAndConditionsAcceptance'),
        migrations.DeleteModel(name='DriverIdentificationFAQ'),
        migrations.DeleteModel(name='DriverIdentificationItems'),
        migrations.DeleteModel(name='DriverIdentification'),
        migrations.DeleteModel(name='DriverAgreement'),
    ]
