"""
Seed driver identification checklist (upload steps + legal agreements) from HolaDrive Figma.

Usage:
    python manage.py seed_driver_identification
    python manage.py seed_driver_identification --force
    python manage.py seed_driver_identification --dry-run

Icons: placeholder 1x1 PNG is set automatically — replace via admin panel later.
"""
from __future__ import annotations

import base64
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.driver_identification_services import legal_content_type
from apps.accounts.models import (
    DriverIdentification,
    DriverIdentificationAgreementsItems,
    DriverIdentificationLegalType,
    DriverIdentificationUploadType,
)

# 1x1 transparent PNG
PLACEHOLDER_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)

UPLOAD_STEPS = [
    {
        'title': "Driver's License",
        'description': "Take a photo of your Driver's License. Ensure all text is clear and readable.",
    },
    {
        'title': 'Profile Photo',
        'description': (
            'Take your profile photo. Use good lighting, face the camera directly, '
            'and make sure your face is clearly visible.'
        ),
    },
    {
        'title': 'Proof of Work Eligibility',
        'description': "Take a photo of your Proof of Work Eligibility document.",
    },
    {
        'title': 'Background Check',
        'description': (
            "Take a photo of your Background Check document. "
            "Make sure the full document is visible."
        ),
    },
    {
        'title': 'Alberta Driver Abstract',
        'description': (
            "Take a photo of your Alberta Driver Abstract. "
            "Ensure the document is not expired and all details are readable."
        ),
    },
    {
        'title': 'City of Calgary TNDL',
        'description': "Take a photo of your City of Calgary TNDL.",
    },
    {
        'title': 'TNDL Certificate',
        'description': "Take a photo of your TNDL Certificate.",
    },
    {
        'title': 'Vehicle Insurance',
        'description': (
            "Take a photo of your Vehicle Insurance. "
            "Your name, VIN, and policy dates must be clearly visible."
        ),
    },
    {
        'title': 'Livery Vehicle Registration',
        'description': (
            'Take a photo of your Livery Vehicle Registration (Class 1–55).'
        ),
    },
    {
        'title': 'Vehicle Inspection Form',
        'description': "Take a photo of your ELVIS Vehicle Inspection Form.",
    },
]

LEGAL_STEP = {
    'title': 'Terms and Conditions',
    'description': 'Review and accept the HolaDrive driver agreements.',
    'agreements': [
        {
            'title': 'Hola Agreement 1',
            'content': (
                '<p>Hola Agreement 1 — replace this text in admin panel with your full legal content.</p>'
            ),
        },
        {
            'title': 'Hola Agreement 2',
            'content': (
                '<p>Hola Agreement 2 — replace this text in admin panel with your full legal content.</p>'
            ),
        },
    ],
}

ALL_SEED_TITLES = [s['title'] for s in UPLOAD_STEPS] + [LEGAL_STEP['title']]


def _icon_filename(title: str) -> str:
    safe = ''.join(c if c.isalnum() else '_' for c in title.lower()).strip('_')
    return f'placeholder_{safe[:60] or "upload"}.png'


def _set_created_at(obj_pk: int, when) -> None:
    DriverIdentification.objects.filter(pk=obj_pk).update(created_at=when, updated_at=when)


class Command(BaseCommand):
    help = 'Seed driver identification upload steps and legal agreements (Figma checklist).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete existing seeded upload/legal types (by title) and recreate.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without writing to the database.',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no database changes.'))
            for step in UPLOAD_STEPS:
                self.stdout.write(f'  would create upload: {step["title"]}')
            self.stdout.write(
                f'  would create legal: {LEGAL_STEP["title"]} '
                f'({len(LEGAL_STEP["agreements"])} agreements)'
            )
            self.stdout.write(self.style.SUCCESS(f'Done. would create {len(UPLOAD_STEPS)} uploads + 1 legal type.'))
            return

        if force:
            self._delete_seeded()

        created_uploads = 0
        skipped_uploads = 0
        created_legal = False
        skipped_legal = False

        base_time = timezone.now()

        with transaction.atomic():
            for index, step in enumerate(UPLOAD_STEPS):
                title = step['title']
                exists = DriverIdentificationUploadType.objects.filter(title=title).exists()
                if exists and not force:
                    skipped_uploads += 1
                    self.stdout.write(f'  skip upload: {title}')
                    continue

                if exists and force:
                    DriverIdentificationUploadType.objects.filter(title=title).delete()

                upload = DriverIdentificationUploadType(
                    title=title,
                    description=step['description'],
                    display_type='upload',
                    is_active=True,
                )
                upload.save()
                upload.icon.save(_icon_filename(title), ContentFile(PLACEHOLDER_PNG), save=True)
                _set_created_at(upload.pk, base_time + timedelta(seconds=index))
                created_uploads += 1
                self.stdout.write(self.style.SUCCESS(f'  created upload: {title} (id={upload.pk})'))

            legal_title = LEGAL_STEP['title']
            legal_exists = DriverIdentificationLegalType.objects.filter(title=legal_title).exists()

            if legal_exists and not force:
                skipped_legal = True
                self.stdout.write(f'  skip legal: {legal_title}')
            else:
                if legal_exists and force:
                    DriverIdentificationLegalType.objects.filter(title=legal_title).delete()

                legal = DriverIdentificationLegalType.objects.create(
                    title=legal_title,
                    description=LEGAL_STEP['description'],
                    display_type='legal',
                    is_active=True,
                )
                legal_index = len(UPLOAD_STEPS)
                _set_created_at(legal.pk, base_time + timedelta(seconds=legal_index))

                ct = legal_content_type()
                for ag in LEGAL_STEP['agreements']:
                    DriverIdentificationAgreementsItems.objects.create(
                        title=ag['title'],
                        content=ag['content'],
                        item_type='legal',
                        content_type=ct,
                        object_id=legal.pk,
                    )

                created_legal = True
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  created legal: {legal_title} (id={legal.pk}, '
                        f'{len(LEGAL_STEP["agreements"])} agreements)'
                    )
                )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. uploads created={created_uploads}, skipped={skipped_uploads}, '
                f'legal created={created_legal}, legal skipped={skipped_legal}'
            )
        )
        self.stdout.write(
            'Replace placeholder icons in admin: Upload — driver identification.'
        )

    def _delete_seeded(self) -> None:
        deleted_u = DriverIdentificationUploadType.objects.filter(title__in=ALL_SEED_TITLES).count()
        DriverIdentificationUploadType.objects.filter(title__in=[s['title'] for s in UPLOAD_STEPS]).delete()
        DriverIdentificationLegalType.objects.filter(title=LEGAL_STEP['title']).delete()
        self.stdout.write(self.style.WARNING(f'Removed {deleted_u} seeded identification row(s).'))
