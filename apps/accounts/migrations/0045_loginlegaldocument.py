# Generated manually for LoginLegalDocument

from django.db import migrations, models
import ckeditor.fields


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0044_customuser_firebase_uid'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoginLegalDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'document_type',
                    models.CharField(
                        choices=[
                            ('privacy_policy', 'Privacy Policy'),
                            ('terms_of_service', 'Terms of Service'),
                        ],
                        max_length=30,
                        unique=True,
                        verbose_name='Document type',
                    ),
                ),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                (
                    'content_format',
                    models.CharField(
                        choices=[('html', 'HTML / Rich text'), ('pdf', 'PDF file')],
                        default='html',
                        max_length=10,
                        verbose_name='Content format',
                    ),
                ),
                (
                    'html_content',
                    ckeditor.fields.RichTextField(
                        blank=True,
                        default='',
                        help_text='Used when content format is HTML.',
                        verbose_name='HTML content',
                    ),
                ),
                (
                    'pdf_file',
                    models.FileField(
                        blank=True,
                        help_text='Used when content format is PDF.',
                        null=True,
                        upload_to='legal/login/',
                        verbose_name='PDF file',
                    ),
                ),
                ('is_active', models.BooleanField(default=True, verbose_name='Is active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Login legal document',
                'verbose_name_plural': 'Login legal documents',
                'ordering': ['document_type'],
            },
        ),
    ]
