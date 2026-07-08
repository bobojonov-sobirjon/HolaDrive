"""
Seed default ride types for price-estimate / Choose your plan screen.

Usage:
    python manage.py seed_ride_types
    python manage.py seed_ride_types --force
    python manage.py seed_ride_types --dry-run
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.order.models import RideType

DEFAULT_RIDE_TYPES = [
    {
        'name': 'Economy',
        'name_large': 'Hola Economy',
        'base_price': Decimal('3.50'),
        'price_per_km': Decimal('1.20'),
        'capacity': 4,
        'icon': 'economy',
        'is_premium': False,
        'is_ev': False,
    },
    {
        'name': 'Comfort',
        'name_large': 'Hola Comfort',
        'base_price': Decimal('5.00'),
        'price_per_km': Decimal('1.50'),
        'capacity': 4,
        'icon': 'comfort',
        'is_premium': True,
        'is_ev': False,
    },
    {
        'name': 'XL',
        'name_large': 'Hola XL',
        'base_price': Decimal('6.00'),
        'price_per_km': Decimal('1.80'),
        'capacity': 6,
        'icon': 'xl',
        'is_premium': False,
        'is_ev': False,
    },
]


class Command(BaseCommand):
    help = 'Seed active ride types with base_price and price_per_km (rider price estimate).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update existing ride types matched by name (or recreate if only blank names exist).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be created without writing to the database.',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no database changes.'))
            for row in DEFAULT_RIDE_TYPES:
                self.stdout.write(
                    f'  would upsert: {row["name"]} '
                    f'(base={row["base_price"]}, per_km={row["price_per_km"]})'
                )
            self.stdout.write(self.style.SUCCESS(f'Done. would seed {len(DEFAULT_RIDE_TYPES)} ride type(s).'))
            return

        created = 0
        updated = 0
        skipped = 0

        with transaction.atomic():
            for row in DEFAULT_RIDE_TYPES:
                name = row['name']
                existing = RideType.objects.filter(name=name).first()
                if existing and not force:
                    if existing.base_price and existing.price_per_km and existing.is_active:
                        skipped += 1
                        self.stdout.write(f'  skip: {name} (already configured)')
                        continue
                    force_row = True
                else:
                    force_row = force

                if existing and force_row:
                    for key, value in row.items():
                        setattr(existing, key, value)
                    existing.is_active = True
                    existing.save()
                    updated += 1
                    self.stdout.write(self.style.SUCCESS(f'  updated: {name} (id={existing.pk})'))
                    continue

                if existing and not force_row:
                    skipped += 1
                    self.stdout.write(f'  skip: {name}')
                    continue

                obj = RideType.objects.create(is_active=True, **row)
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  created: {name} (id={obj.pk})'))

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. created={created}, updated={updated}, skipped={skipped}. '
                'Adjust prices in admin: ride-types.'
            )
        )
