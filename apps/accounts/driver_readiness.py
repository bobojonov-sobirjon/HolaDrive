"""
Driver onboarding / ride-ready checklist: each required step as true/false.
"""
from __future__ import annotations

from typing import Any

from apps.accounts.driver_identification_services import build_checklist_payload
from apps.accounts.models import (
    CustomUser,
    DriverIdentificationRegistrationAgreementsUserAccepted,
    DriverIdentificationRegistrationType,
    DriverPreferences,
    DriverVerification,
    PinVerificationForUser,
    VehicleDetails,
)
from apps.accounts.phone_auth import is_phone_signup_user


def _profile_complete(user: CustomUser) -> tuple[bool, dict[str, bool]]:
    has_name = bool((user.first_name or '').strip() or (user.last_name or '').strip())
    has_phone = bool((user.phone_number or '').strip())
    has_email = bool((user.email or '').strip()) and not is_phone_signup_user(user)
    has_dob = user.date_of_birth is not None
    has_address = bool((user.address or '').strip())
    parts = {
        'full_name': has_name,
        'phone_number': has_phone,
        'email': has_email or has_phone,  # phone-only signup OK until email linked
        'date_of_birth': has_dob,
        'address': has_address,
    }
    # Minimum for profile step: name + phone + DOB
    ok = has_name and has_phone and has_dob
    return ok, parts


def _identification_complete(user: CustomUser) -> tuple[bool, dict[str, Any]]:
    verification = DriverVerification.objects.filter(user=user).first()
    status = verification.status if verification else DriverVerification.Status.NOT_SUBMITTED
    approved = status == DriverVerification.Status.APPROVED

    steps = build_checklist_payload(user)
    all_steps_accepted = bool(steps) and all(bool(s.get('is_accepted')) for s in steps)
    # If admin has no checklist configured, treat checklist as N/A → rely on verification status
    if not steps:
        all_steps_accepted = approved or status in (
            DriverVerification.Status.IN_REVIEW,
            DriverVerification.Status.APPROVED,
        )

    ok = approved  # for accepting rides, admin approval is the gate
    return ok, {
        'checklist_complete': all_steps_accepted,
        'verification_status': status,
        'verification_approved': approved,
        'steps_total': len(steps),
        'steps_accepted': sum(1 for s in steps if s.get('is_accepted')),
    }


def _registration_terms_complete(user: CustomUser) -> bool:
    active = list(
        DriverIdentificationRegistrationType.objects.filter(is_active=True).values_list('id', flat=True)
    )
    if not active:
        return True
    accepted = set(
        DriverIdentificationRegistrationAgreementsUserAccepted.objects.filter(
            user=user,
            driver_identification_registration_agreements_id__in=active,
            is_accepted=True,
        ).values_list('driver_identification_registration_agreements_id', flat=True)
    )
    return all(i in accepted for i in active)


def _bank_account_complete(user: CustomUser) -> tuple[bool, dict[str, Any]]:
    acct_id = (user.stripe_connect_account_id or '').strip()
    detail: dict[str, Any] = {
        'stripe_connect_linked': bool(acct_id),
        'bank_linked': False,
        'payouts_enabled': False,
    }
    if not acct_id:
        return False, detail
    try:
        from apps.payment.services.stripe_connect_bank import build_driver_payout_profile

        profile = build_driver_payout_profile(user)
        bank = profile.get('bank') or profile.get('bank_account')
        detail['bank_linked'] = bool(bank)
        detail['payouts_enabled'] = bool(profile.get('payouts_enabled'))
        detail['onboarding_complete'] = bool(profile.get('onboarding_complete'))
        ok = bool(bank) and bool(profile.get('payouts_enabled') or profile.get('onboarding_complete'))
        return ok, detail
    except Exception as exc:
        detail['error'] = str(exc)
        # Soft: connect id present counts as partial — still false until bank confirmed
        return False, detail


def build_driver_readiness(user: CustomUser) -> dict[str, Any]:
    group_names = {g.name for g in user.groups.all()}
    is_driver = 'Driver' in group_names

    profile_ok, profile_parts = _profile_complete(user)
    avatar_ok = bool(user.avatar)
    preferences_ok = DriverPreferences.objects.filter(user=user).exists()
    vehicle_ok = VehicleDetails.objects.filter(user=user).exists()
    pin_ok = PinVerificationForUser.objects.filter(user=user).exists()
    registration_terms_ok = _registration_terms_complete(user)
    identification_ok, identification_detail = _identification_complete(user)
    bank_ok, bank_detail = _bank_account_complete(user)

    checks = {
        'profile': profile_ok,
        'profile_photo': avatar_ok,
        'identification': identification_ok,
        'registration_terms': registration_terms_ok,
        'preferences': preferences_ok,
        'vehicle': vehicle_ok,
        'pin': pin_ok,
        'bank_account': bank_ok,
    }

    # Required to accept rides (product gate)
    required_keys = [
        'profile',
        'identification',
        'preferences',
        'vehicle',
        'bank_account',
    ]
    ready_for_rides = is_driver and all(checks[k] for k in required_keys)

    completed = sum(1 for v in checks.values() if v)
    total = len(checks)
    percent = int(round((completed / total) * 100)) if total else 0

    return {
        'is_driver': is_driver,
        'ready_for_rides': ready_for_rides,
        'completion_percent': percent,
        'checks': checks,
        'details': {
            'profile': profile_parts,
            'identification': identification_detail,
            'bank_account': bank_detail,
            'required_for_rides': required_keys,
        },
    }
