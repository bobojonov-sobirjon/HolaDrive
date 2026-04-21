from asgiref.sync import sync_to_async
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.views import AsyncAPIView


class StripeCustomerMeView(AsyncAPIView):
    """
    Returns (and optionally creates) Stripe customer id for authenticated user.
    Frontend can call this once and then reuse the returned cus_… for SetupIntent/PaymentMethods.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Payment: Stripe'],
        summary='Get/create Stripe customer id (me)',
        description=(
            'Returns the Stripe customer id (cus_…) for the authenticated user. '
            'If missing and Stripe is configured, backend creates one and stores it on the user.'
        ),
        examples=[
            OpenApiExample(
                'Response',
                value={'status': 'success', 'data': {'stripe_customer_id': 'cus_xxx', 'created': True}},
                response_only=True,
            )
        ],
    )
    async def get(self, request):
        cid = (getattr(request.user, 'stripe_customer_id', '') or '').strip()
        if cid:
            return Response(
                {'status': 'success', 'data': {'stripe_customer_id': cid, 'created': False}},
                status=status.HTTP_200_OK,
            )

        if not (getattr(settings, 'STRIPE_SECRET_KEY', '') or ''):
            return Response(
                {'status': 'error', 'message': 'Stripe is not configured on the server.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        def _create():
            from apps.accounts.models import CustomUser
            from apps.payment.services.stripe_cards import get_or_create_stripe_customer_id

            u = CustomUser.objects.get(pk=request.user.pk)
            cid2 = get_or_create_stripe_customer_id(u)
            # ensure persisted
            if not (u.stripe_customer_id or '').strip():
                u.stripe_customer_id = cid2
                u.save(update_fields=['stripe_customer_id'])
            return cid2

        try:
            created_id = await sync_to_async(_create)()
        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {'status': 'success', 'data': {'stripe_customer_id': created_id, 'created': True}},
            status=status.HTTP_200_OK,
        )

