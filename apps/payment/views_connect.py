"""Stripe Connect + driver payout APIs (AutoHandy-style, HolaDrive paths)."""
import stripe
from asgiref.sync import sync_to_async
from django.conf import settings
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import CustomUser
from apps.common.views import AsyncAPIView

from .serializers_connect import (
    StripeConnectBankDeleteSerializer,
    StripeConnectBankWriteSerializer,
    StripeConnectCompleteSetupSerializer,
)
from .utils import holder_role_for_user


def _stripe_ok() -> bool:
    return bool(getattr(settings, 'STRIPE_SECRET_KEY', '') or '')


async def _require_driver(user) -> bool:
    role = await sync_to_async(holder_role_for_user)(user)
    return role == 'driver'


class DriverStripeConnectBankAccountView(AsyncAPIView):
    """GET/POST/DELETE /api/v1/payment/driver/stripe-connect/bank-account/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Stripe — Driver'],
        summary='Direct deposit — linked bank & Connect status',
        description='Returns Connect account id, capabilities, masked bank, agreement URL.',
    )
    async def get(self, request):
        if not await _require_driver(request.user):
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=403)
        if not _stripe_ok():
            return Response({'message': 'Stripe is not configured.', 'status': 'error'}, status=503)

        from .services.stripe_connect_bank import build_driver_payout_profile

        data = await sync_to_async(build_driver_payout_profile)(request.user)
        return Response({'message': 'OK', 'status': 'success', 'data': data}, status=200)

    @extend_schema(
        tags=['Stripe — Driver'],
        summary='Direct deposit — save bank (routing + account)',
        description=(
            'Creates Connect account (if needed), links US bank, and enables payouts.\n\n'
            '**Test mode (`sk_test_…`):** only `routing_number`, `account_number`, `accept_agreement` — '
            'DOB/SSN filled server-side.\n\n'
            '**Live mode (`sk_live_…`):** also required: `dob_year`, `dob_month`, `dob_day`, '
            '`ssn_last4` (9-digit US SSN). Sent to Stripe only — not stored in DB.'
        ),
        request=StripeConnectBankWriteSerializer,
        examples=[
            OpenApiExample(
                'Test mode — minimal bank',
                value={
                    'routing_number': '110000000',
                    'account_number': '000123456789',
                    'accept_agreement': True,
                },
                request_only=True,
            ),
            OpenApiExample(
                'Live mode — bank + DOB + SSN (required)',
                value={
                    'routing_number': '121000358',
                    'account_number': 'XXXXXXXX',
                    'account_holder_name': 'Jane Driver',
                    'account_holder_type': 'individual',
                    'accept_agreement': True,
                    'dob_year': 1987,
                    'dob_month': 3,
                    'dob_day': 2,
                    'ssn_last4': '123456789',
                },
                request_only=True,
            ),
        ],
    )
    async def post(self, request):
        if not await _require_driver(request.user):
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=403)
        if not _stripe_ok():
            return Response({'message': 'Stripe is not configured.', 'status': 'error'}, status=503)

        ser = StripeConnectBankWriteSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response({'message': 'Validation error', 'status': 'error', 'errors': ser.errors}, status=400)

        vd = ser.validated_data
        if not vd.get('accept_agreement'):
            return Response(
                {'message': 'accept_agreement must be true', 'status': 'error'},
                status=400,
            )

        from .services.stripe_connect_bank import ensure_connect_and_add_bank

        def _run():
            u = CustomUser.objects.get(pk=request.user.pk)
            return ensure_connect_and_add_bank(
                u,
                routing_number=vd['routing_number'],
                account_number=vd['account_number'],
                account_holder_name=vd.get('account_holder_name') or '',
                account_holder_type=vd.get('account_holder_type') or 'individual',
                accept_agreement=True,
                dob_year=vd.get('dob_year'),
                dob_month=vd.get('dob_month'),
                dob_day=vd.get('dob_day'),
                ssn_last4=vd.get('ssn_last4') or None,
            )

        try:
            data = await sync_to_async(_run)()
        except ValueError as e:
            return Response({'message': str(e), 'status': 'error'}, status=400)
        except stripe.error.StripeError as e:
            return Response(
                {'message': getattr(e, 'user_message', None) or str(e), 'status': 'error'},
                status=400,
            )

        return Response({'message': 'Bank account saved', 'status': 'success', 'data': data}, status=200)

    @extend_schema(
        tags=['Stripe — Driver'],
        summary='Direct deposit — remove bank',
        request=StripeConnectBankDeleteSerializer,
    )
    async def delete(self, request):
        if not await _require_driver(request.user):
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=403)
        if not _stripe_ok():
            return Response({'message': 'Stripe is not configured.', 'status': 'error'}, status=503)

        bank_id = (request.data.get('bank_account_id') or '').strip() or None
        from .services.stripe_connect_bank import remove_bank_account

        try:
            data = await sync_to_async(remove_bank_account)(request.user, bank_id)
        except ValueError as e:
            return Response({'message': str(e), 'status': 'error'}, status=400)
        except stripe.error.StripeError as e:
            return Response(
                {'message': getattr(e, 'user_message', None) or str(e), 'status': 'error'},
                status=400,
            )
        return Response({'message': 'Bank removed', 'status': 'success', 'data': data}, status=200)


class DriverStripeConnectCompleteSetupView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Stripe — Driver'],
        summary='Stripe Connect — complete setup (enable account)',
        description=(
            'Use when bank is already linked but account is still **Restricted**. '
            'Sends agreement + DOB + SSN to Stripe (not stored in DB).\n\n'
            '**Test:** only `accept_agreement: true`.\n'
            '**Live:** `accept_agreement`, `dob_year`, `dob_month`, `dob_day`, `ssn_last4` (9 digits).'
        ),
        request=StripeConnectCompleteSetupSerializer,
        examples=[
            OpenApiExample(
                'Test mode — agreement only',
                value={'accept_agreement': True},
                request_only=True,
            ),
            OpenApiExample(
                'Live mode — DOB + SSN (required)',
                value={
                    'accept_agreement': True,
                    'dob_year': 1987,
                    'dob_month': 3,
                    'dob_day': 2,
                    'ssn_last4': '123456789',
                },
                request_only=True,
            ),
        ],
    )
    async def post(self, request):
        if not await _require_driver(request.user):
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=403)
        if not _stripe_ok():
            return Response({'message': 'Stripe is not configured.', 'status': 'error'}, status=503)

        ser = StripeConnectCompleteSetupSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response({'message': 'Validation error', 'status': 'error', 'errors': ser.errors}, status=400)
        vd = ser.validated_data

        acct_id = (getattr(request.user, 'stripe_connect_account_id', None) or '').strip()
        if not acct_id:
            return Response(
                {'message': 'No Connect account. POST bank-account first.', 'status': 'error'},
                status=400,
            )

        from .services.stripe_connect_setup import complete_connect_account_setup
        from .services.stripe_connect_bank import build_driver_payout_profile

        def _run():
            u = CustomUser.objects.get(pk=request.user.pk)
            complete_connect_account_setup(
                acct_id,
                user=u,
                accept_agreement=vd['accept_agreement'],
                dob_year=vd.get('dob_year'),
                dob_month=vd.get('dob_month'),
                dob_day=vd.get('dob_day'),
                ssn_last4=vd.get('ssn_last4') or None,
            )
            return build_driver_payout_profile(u)

        try:
            data = await sync_to_async(_run)()
        except ValueError as e:
            return Response({'message': str(e), 'status': 'error'}, status=400)
        except stripe.error.StripeError as e:
            return Response(
                {'message': getattr(e, 'user_message', None) or str(e), 'status': 'error'},
                status=400,
            )
        return Response({'message': 'Setup completed', 'status': 'success', 'data': data}, status=200)


class DriverStripeBalanceView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Stripe — Driver'],
        summary='Stripe Connect balance (pending / available) & recent bank payouts',
        description=(
            'Read-only. Shows pending and available Connect balance plus recent automatic bank payouts. '
            'Stripe deposits available funds to the linked bank on the weekly schedule — no manual cash-out.'
        ),
    )
    async def get(self, request):
        if not await _require_driver(request.user):
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=403)
        if not _stripe_ok():
            return Response({'message': 'Stripe is not configured.', 'status': 'error'}, status=503)

        from .services.connect_balance import fetch_connect_balance_and_payouts

        try:
            data = await sync_to_async(fetch_connect_balance_and_payouts)(request.user)
        except ValueError as e:
            return Response({'message': str(e), 'status': 'error'}, status=400)
        except stripe.error.StripeError as e:
            return Response(
                {'message': getattr(e, 'user_message', None) or str(e), 'status': 'error'},
                status=400,
            )
        return Response({'message': 'Balance retrieved', 'status': 'success', 'data': data}, status=200)


class DriverCheckoutHistoryView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Stripe — Driver'],
        summary='Checkout / payment history (orders + Stripe ledger)',
        description=(
            'Completed card trips from DB plus Stripe Connect BalanceTransaction ledger. '
            'Use stripe_starting_after for the next ledger page.'
        ),
        parameters=[
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('stripe_tx_limit', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('stripe_starting_after', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
    )
    async def get(self, request):
        if not await _require_driver(request.user):
            return Response({'message': 'Only drivers can access this endpoint', 'status': 'error'}, status=403)

        from .services.connect_checkout_history import build_checkout_history

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        stripe_tx_limit = int(request.query_params.get('stripe_tx_limit', 30))
        stripe_starting_after = (request.query_params.get('stripe_starting_after') or '').strip() or None

        def _run():
            u = CustomUser.objects.get(pk=request.user.pk)
            return build_checkout_history(
                u,
                page=page,
                page_size=page_size,
                stripe_tx_limit=stripe_tx_limit,
                stripe_starting_after=stripe_starting_after,
            )

        try:
            data = await sync_to_async(_run)()
        except stripe.error.StripeError as e:
            return Response(
                {'message': getattr(e, 'user_message', None) or str(e), 'status': 'error'},
                status=400,
            )
        return Response({'message': 'History retrieved', 'status': 'success', 'data': data}, status=200)
