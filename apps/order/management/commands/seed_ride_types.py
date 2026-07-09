"""
Seed Figma ride types for price-estimate / Choose your plan screen.

Usage:
    python manage.py seed_ride_types
    python manage.py seed_ride_types --force
    python manage.py seed_ride_types --dry-run

Prices use base_price + (price_per_km * distance_km) * surge.
Tariffs below are tuned so ~2.5 km trips match Figma list prices ($7, $12, $35, …).
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.order.models import RideType

# name = stable slug (admin / seed key); name_large = rider UI label (Figma)
# Reference ~2.46 km: Hola≈$7, Hola Large≈$12, Premium≈$35, Premium Large≈$39, EV≈$18, EV Large≈$24
FIGMA_RIDE_TYPES = [
    {
        'name': 'hola',
        'name_large': 'Hola',
        'sort_order': 1,
        'base_price': Decimal('2.50'),
        'price_per_km': Decimal('1.85'),
        'capacity': 4,
        'icon': 'hola',
        'is_premium': False,
        'is_ev': False,
    },
    {
        'name': 'hola_large',
        'name_large': 'Hola Large',
        'sort_order': 2,
        'base_price': Decimal('4.00'),
        'price_per_km': Decimal('3.25'),
        'capacity': 8,
        'icon': 'hola_large',
        'is_premium': False,
        'is_ev': False,
    },
    {
        'name': 'premium',
        'name_large': 'Premium',
        'sort_order': 3,
        'base_price': Decimal('20.00'),
        'price_per_km': Decimal('6.10'),
        'capacity': 6,
        'icon': 'premium',
        'is_premium': True,
        'is_ev': False,
    },
    {
        'name': 'premium_large',
        'name_large': 'Premium Large',
        'sort_order': 4,
        'base_price': Decimal('22.00'),
        'price_per_km': Decimal('6.91'),
        'capacity': 6,
        'icon': 'premium_large',
        'is_premium': True,
        'is_ev': False,
    },
    {
        'name': 'hola_ev',
        'name_large': 'Hola EV',
        'sort_order': 5,
        'base_price': Decimal('8.00'),
        'price_per_km': Decimal('4.07'),
        'capacity': 6,
        'icon': 'hola_ev',
        'is_premium': False,
        'is_ev': True,
    },
    {
        'name': 'hola_ev_large',
        'name_large': 'Hola EV Large',
        'sort_order': 6,
        'base_price': Decimal('10.00'),
        'price_per_km': Decimal('5.69'),
        'capacity': 6,
        'icon': 'hola_ev_large',
        'is_premium': False,
        'is_ev': True,
    },
]

# Old seed names — deactivated when Figma set is applied
LEGACY_RIDE_TYPE_NAMES = ('Economy', 'Comfort', 'XL')


class Command(BaseCommand):
    help = 'Seed Figma ride types (Hola, Hola Large, Premium, …) for rider price estimate.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update existing ride types matched by name slug.',
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
            for row in FIGMA_RIDE_TYPES:
                self.stdout.write(
                    f'  would upsert: {row["name_large"]} ({row["name"]}) '
                    f'base={row["base_price"]} per_km={row["price_per_km"]} '
                    f'cap={row["capacity"]} premium={row["is_premium"]} ev={row["is_ev"]}'
                )
            self.stdout.write(
                self.style.WARNING(f'  would deactivate legacy: {", ".join(LEGACY_RIDE_TYPE_NAMES)}')
            )
            self.stdout.write(self.style.SUCCESS(f'Done. would seed {len(FIGMA_RIDE_TYPES)} ride type(s).'))
            return

        created = 0
        updated = 0
        skipped = 0

        with transaction.atomic():
            for row in FIGMA_RIDE_TYPES:
                name = row['name']
                existing = RideType.objects.filter(name=name).first()
                if not existing:
                    existing = RideType.objects.filter(name_large=row['name_large']).first()

                if existing and not force:
                    if existing.base_price and existing.price_per_km and existing.is_active:
                        skipped += 1
                        self.stdout.write(f'  skip: {row["name_large"]} (already configured)')
                        continue
                    force_row = True
                else:
                    force_row = force or existing is not None

                if existing and force_row:
                    for key, value in row.items():
                        setattr(existing, key, value)
                    existing.is_active = True
                    existing.save()
                    updated += 1
                    self.stdout.write(self.style.SUCCESS(f'  updated: {row["name_large"]} (id={existing.pk})'))
                    continue

                if existing and not force_row:
                    skipped += 1
                    self.stdout.write(f'  skip: {row["name_large"]}')
                    continue

                obj = RideType.objects.create(is_active=True, **row)
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  created: {row["name_large"]} (id={obj.pk})'))

            legacy_qs = RideType.objects.filter(name__in=LEGACY_RIDE_TYPE_NAMES, is_active=True)
            legacy_count = legacy_qs.count()
            if legacy_count:
                legacy_qs.update(is_active=False)
                self.stdout.write(
                    self.style.WARNING(f'  deactivated legacy types: {legacy_count} ({", ".join(LEGACY_RIDE_TYPE_NAMES)})')
                )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. created={created}, updated={updated}, skipped={skipped}. '
                'Edit tariffs in admin: ride-types.'
            )
        )
