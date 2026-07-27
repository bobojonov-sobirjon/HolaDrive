"""
Create / update a fully verified local driver account (profile, vehicle, fake KYC).

Usage:
    python manage.py seed_full_driver
    python manage.py seed_full_driver --email user@example.com --password secret123
"""
from __future__ import annotations

import base64
from datetime import date

from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import (
    CustomUser,
    DriverIdentificationLegalAgreementsUserAccepted,
    DriverIdentificationLegalType,
    DriverIdentificationRegistrationAgreementsUserAccepted,
    DriverIdentificationRegistrationType,
    DriverIdentificationTermsType,
    DriverIdentificationTermsUserAccepted,
    DriverIdentificationUploadType,
    DriverIdentificationUploadTypeQuestionAnswer,
    DriverIdentificationUploadTypeUserAccepted,
    DriverPreferences,
    DriverVerification,
    VehicleDetails,
)
from apps.order.models import RideType

PLACEHOLDER_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


class Command(BaseCommand):
    help = 'Seed a fully verified driver (profile + vehicle + fake document acceptances).'

    def add_arguments(self, parser):
        parser.add_argument('--email', default='msbobojomov2000@gmail.com')
        parser.add_argument('--password', default='05769452s')
        parser.add_argument('--first-name', default='Muzaffar')
        parser.add_argument('--last-name', default='Bobojomov')

    @transaction.atomic
    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']

        driver_group = Group.objects.filter(name='Driver').first()
        if not driver_group:
            raise CommandError('Group "Driver" not found. Create auth groups first.')

        user = CustomUser.objects.filter(email__iexact=email).first()
        created = False
        if user is None:
            username = email.split('@')[0][:140]
            base_username = username
            n = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f'{base_username}{n}'
                n += 1
            user = CustomUser(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            created = True

        user.first_name = first_name
        user.last_name = last_name
        user.phone_number = user.phone_number or '+14035550199'
        user.date_of_birth = user.date_of_birth or date(1995, 5, 15)
        user.gender = user.gender or CustomUser.Gender.MALE
        user.address = user.address or '123 Fake St, Calgary, AB T2P 1J9'
        user.latitude = user.latitude or '51.04470000000000'
        user.longitude = user.longitude or '-114.07190000000000'
        user.tax_number = user.tax_number or '123456789'
        user.is_verified = True
        user.is_active = True
        user.is_online = False
        user.set_password(password)
        user.save()

        if not user.groups.filter(pk=driver_group.pk).exists():
            user.groups.add(driver_group)

        DriverPreferences.objects.update_or_create(
            user=user,
            defaults={
                'trip_type_preference': DriverPreferences.TripTypePreference.ANY,
                'maximum_pickup_distance': DriverPreferences.MaximumPickupDistance.TEN_KM,
                'preferred_working_hours': DriverPreferences.PreferredWorkingHours.ANY,
                'notification_intensity': DriverPreferences.NotificationIntensity.MODERATE,
            },
        )

        ride_types = list(RideType.objects.filter(is_active=True).order_by('id'))
        if not ride_types:
            raise CommandError('No active RideType found.')

        # Prefer unique names: take first of each name
        seen_names = set()
        unique_types = []
        for rt in ride_types:
            if rt.name in seen_names:
                continue
            seen_names.add(rt.name)
            unique_types.append(rt)
        default_rt = unique_types[0]

        vehicle, v_created = VehicleDetails.objects.get_or_create(
            user=user,
            vin='1HGBH41JXMN109999',
            defaults={
                'brand': 'Toyota',
                'model': 'Camry',
                'year_of_manufacture': 2020,
                'plate_number': 'ABC 123',
                'color': 'White',
                'vehicle_condition': VehicleDetails.VehicleCondition.GOOD,
                'default_ride_type': default_rt,
            },
        )
        if not v_created:
            vehicle.brand = 'Toyota'
            vehicle.model = 'Camry'
            vehicle.year_of_manufacture = 2020
            vehicle.plate_number = 'ABC 123'
            vehicle.color = 'White'
            vehicle.vehicle_condition = VehicleDetails.VehicleCondition.GOOD
            vehicle.default_ride_type = default_rt
            vehicle.save()
        vehicle.supported_ride_types.set(unique_types)

        # Second fake car
        vehicle2, _ = VehicleDetails.objects.get_or_create(
            user=user,
            vin='2T1BURHE0JC123456',
            defaults={
                'brand': 'Honda',
                'model': 'Civic',
                'year_of_manufacture': 2019,
                'plate_number': 'XYZ 789',
                'color': 'Black',
                'vehicle_condition': VehicleDetails.VehicleCondition.EXCELLENT,
                'default_ride_type': default_rt,
            },
        )
        vehicle2.supported_ride_types.set(unique_types)

        # Legal / registration / terms acceptances
        for legal in DriverIdentificationLegalType.objects.all():
            DriverIdentificationLegalAgreementsUserAccepted.objects.update_or_create(
                user=user,
                driver_identification_legal_agreements=legal,
                defaults={'is_accepted': True},
            )
        for reg in DriverIdentificationRegistrationType.objects.all():
            DriverIdentificationRegistrationAgreementsUserAccepted.objects.update_or_create(
                user=user,
                driver_identification_registration_agreements=reg,
                defaults={'is_accepted': True},
            )
        for terms in DriverIdentificationTermsType.objects.all():
            DriverIdentificationTermsUserAccepted.objects.update_or_create(
                user=user,
                driver_identification_terms=terms,
                defaults={'is_accepted': True},
            )

        # Upload steps: per-slot QA if present, else whole-type file
        for upload_type in DriverIdentificationUploadType.objects.all():
            qas = list(
                DriverIdentificationUploadTypeQuestionAnswer.objects.filter(
                    driver_identification_upload_type_item__driver_identification_upload_type=upload_type
                )
            )
            if qas:
                for qa in qas:
                    acc, _ = DriverIdentificationUploadTypeUserAccepted.objects.get_or_create(
                        user=user,
                        question_answer=qa,
                        defaults={
                            'driver_identification_upload_type': upload_type,
                            'is_accepted': True,
                        },
                    )
                    if not acc.file:
                        acc.file.save(
                            f'fake_upload_{upload_type.pk}_{qa.pk}.png',
                            ContentFile(PLACEHOLDER_PNG),
                            save=False,
                        )
                    acc.driver_identification_upload_type = upload_type
                    acc.is_accepted = True
                    acc.save()
            else:
                acc, _ = DriverIdentificationUploadTypeUserAccepted.objects.get_or_create(
                    user=user,
                    driver_identification_upload_type=upload_type,
                    question_answer=None,
                    defaults={'is_accepted': True},
                )
                if not acc.file:
                    acc.file.save(
                        f'fake_upload_{upload_type.pk}.png',
                        ContentFile(PLACEHOLDER_PNG),
                        save=False,
                    )
                acc.is_accepted = True
                acc.save()

        verification, _ = DriverVerification.objects.get_or_create(user=user)
        verification.status = DriverVerification.Status.APPROVED
        verification.comment = 'Seeded full driver — local fake approval'
        verification.reviewed_at = timezone.now()
        verification.save()

        self.stdout.write(self.style.SUCCESS(
            f'{"Created" if created else "Updated"} driver {user.email} '
            f'(id={user.pk}, vehicles={user.vehicle_details.count()}, '
            f'verification={verification.status})'
        ))
        self.stdout.write(f'  password: {password}')
        self.stdout.write(f'  groups: {list(user.groups.values_list("name", flat=True))}')
        self.stdout.write(f'  ride types: {[r.name for r in unique_types]}')
