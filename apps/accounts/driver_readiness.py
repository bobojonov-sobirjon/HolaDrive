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

# Profile fields required for checks.profile === true
PROFILE_REQUIRED_FIELDS = ('full_name', 'phone_number', 'date_of_birth')

_PROFILE_FIELD_ACTIONS: dict[str, dict[str, Any]] = {
    'full_name': {
        'field': 'full_name',
        'message': 'Add first name and/or last name',
        'screen': 'edit_profile',
        'method': 'PUT',
        'path': '/api/v1/accounts/me/',
        'body_hint': {'first_name': 'John', 'last_name': 'Doe'},
    },
    'phone_number': {
        'field': 'phone_number',
        'message': 'Add and verify phone number',
        'screen': 'edit_profile',
        'method': 'PUT',
        'path': '/api/v1/accounts/me/',
        'body_hint': {'phone_number': '+15145551234'},
        'preferred_flow': {
            'request': 'POST /api/v1/accounts/me/contact/request/',
            'confirm': 'POST /api/v1/accounts/me/contact/confirm/',
        },
    },
    'date_of_birth': {
        'field': 'date_of_birth',
        'message': 'Add date of birth',
        'screen': 'edit_profile',
        'method': 'PUT',
        'path': '/api/v1/accounts/me/',
        'body_hint': {'date_of_birth': '1990-01-15'},
    },
}


def _profile_complete(user: CustomUser) -> tuple[bool, dict[str, Any]]:
    has_name = bool((user.first_name or '').strip() or (user.last_name or '').strip())
    has_phone = bool((user.phone_number or '').strip())
    has_email = bool((user.email or '').strip()) and not is_phone_signup_user(user)
    has_dob = user.date_of_birth is not None
    has_address = bool((user.address or '').strip())
    fields = {
        'full_name': has_name,
        'phone_number': has_phone,
        'email': has_email or has_phone,  # phone-only signup OK until email linked
        'date_of_birth': has_dob,
        'address': has_address,
    }
    # Minimum for profile step: name + phone + DOB
    ok = has_name and has_phone and has_dob
    missing = [f for f in PROFILE_REQUIRED_FIELDS if not fields.get(f)]
    actions = [_PROFILE_FIELD_ACTIONS[f] for f in missing if f in _PROFILE_FIELD_ACTIONS]
    return ok, {
        **fields,
        'required_fields': list(PROFILE_REQUIRED_FIELDS),
        'missing_fields': missing,
        'actions': actions,
        'next_screen': 'edit_profile' if missing else None,
        'next_path': '/api/v1/accounts/me/' if missing else None,
        'next_field': missing[0] if missing else None,
    }


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
    if approved:
        action_hint = None
        next_screen = None
    elif all_steps_accepted or status == DriverVerification.Status.IN_REVIEW:
        action_hint = 'Documents submitted — waiting for admin approval'
        next_screen = 'identification_status'
    else:
        action_hint = 'Complete identification checklist and submit documents'
        next_screen = 'identification_checklist'

    return ok, {
        'checklist_complete': all_steps_accepted,
        'verification_status': status,
        'verification_approved': approved,
        'steps_total': len(steps),
        'steps_accepted': sum(1 for s in steps if s.get('is_accepted')),
        'message': action_hint,
        'next_screen': next_screen,
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
        'next_screen': 'bank_account',
        'next_path': '/api/v1/payment/driver/stripe-connect/',
    }
    if not acct_id:
        detail['message'] = 'Link Stripe Connect and add a bank account'
        return False, detail
    try:
        from apps.payment.services.stripe_connect_bank import build_driver_payout_profile

        profile = build_driver_payout_profile(user)
        bank = profile.get('bank') or profile.get('bank_account')
        detail['bank_linked'] = bool(bank)
        detail['payouts_enabled'] = bool(profile.get('payouts_enabled'))
        detail['onboarding_complete'] = bool(profile.get('onboarding_complete'))
        ok = bool(bank) and bool(profile.get('payouts_enabled') or profile.get('onboarding_complete'))
        if not ok:
            detail['message'] = 'Finish Stripe Connect onboarding / link bank account'
        else:
            detail['message'] = None
            detail['next_screen'] = None
            detail['next_path'] = None
        return ok, detail
    except Exception as exc:
        detail['error'] = str(exc)
        detail['message'] = 'Could not verify bank account status'
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

    # Top-level navigation hints when a check is false
    step_actions: dict[str, Any] = {
        'profile': {
            'screen': 'edit_profile',
            'path': '/api/v1/accounts/me/',
            'use_details': 'details.profile.missing_fields / details.profile.actions',
        },
        'profile_photo': {
            'screen': 'edit_avatar',
            'method': 'PUT',
            'path': '/api/v1/accounts/me/avatar/',
            'message': 'Upload profile photo',
        },
        'identification': {
            'screen': identification_detail.get('next_screen') or 'identification_checklist',
            'message': identification_detail.get('message'),
            'use_details': 'details.identification.verification_status',
        },
        'registration_terms': {
            'screen': 'registration_terms',
            'path': '/api/v1/accounts/driver/registration-terms/',
            'message': 'Accept registration terms',
        },
        'preferences': {
            'screen': 'driver_preferences',
            'method': 'POST',
            'path': '/api/v1/accounts/driver/preferences/',
            'message': 'Set driver preferences',
        },
        'vehicle': {
            'screen': 'vehicle',
            'path': '/api/v1/accounts/driver/vehicles/',
            'message': 'Add a vehicle',
        },
        'pin': {
            'screen': 'pin_setup',
            'method': 'POST',
            'path': '/api/v1/accounts/pin-verification/',
            'message': 'Create a PIN',
        },
        'bank_account': {
            'screen': 'bank_account',
            'path': bank_detail.get('next_path') or '/api/v1/payment/driver/stripe-connect/',
            'message': bank_detail.get('message') or 'Link bank account',
        },
    }
    incomplete_actions = {k: step_actions[k] for k, v in checks.items() if not v and k in step_actions}

    return {
        'is_driver': is_driver,
        'ready_for_rides': ready_for_rides,
        'completion_percent': percent,
        'checks': checks,
        'incomplete_actions': incomplete_actions,
        'details': {
            'profile': profile_parts,
            'identification': identification_detail,
            'bank_account': bank_detail,
            'required_for_rides': required_keys,
        },
    }
