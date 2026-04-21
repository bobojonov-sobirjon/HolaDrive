import stripe
from asgiref.sync import sync_to_async
from django.conf import settings
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.views import AsyncAPIView

from .models import SavedCard
from .serializers import (
    SavedCardCreateSerializer,
    SavedCardSerializer,
    SavedCardUpdateSerializer,
)
from .services import stripe_cards
from .utils import holder_role_for_user


def _stripe_configured() -> bool:
    return bool(getattr(settings, 'STRIPE_SECRET_KEY', '') or '')


class SavedCardListCreateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Payment: Saved cards'],
        summary='List saved cards',
        description=(
            'Returns active saved cards for the authenticated user. '
            'Scope is chosen from the user’s groups: **Driver** → driver cards; otherwise rider cards.'
        ),
        responses={200: SavedCardSerializer(many=True)},
    )
    async def get(self, request):
        if not _stripe_configured():
            return Response(
                {
                    'message': 'Stripe is not configured on the server.',
                    'status': 'error',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        role = await sync_to_async(holder_role_for_user)(request.user)
        qs = (
            SavedCard.objects.filter(
                user=request.user,
                is_active=True,
                holder_role=role,
            )
            .order_by('-is_default', '-created_at')
        )

        cards = await sync_to_async(list)(qs)
        ser = SavedCardSerializer(cards, many=True)
        data = await sync_to_async(lambda: ser.data)()
        return Response(
            {
                'message': 'Saved cards retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=['Payment: Saved cards'],
        summary='Add saved card',
        description=(
            'Body: only ``payment_method_id`` (``pm_…``). '
            'Rider vs driver scope is taken from ``request.user`` groups (**Driver** → driver; else rider). '
            'First card in that scope becomes default automatically; use PUT to change default.'
        ),
        request=SavedCardCreateSerializer,
        examples=[
            OpenApiExample(
                'Add card',
                value={'payment_method_id': 'pm_xxxxxxxxxxxxxxxxxxxxxxxx'},
                request_only=True,
            ),
        ],
        responses={201: SavedCardSerializer},
    )
    async def post(self, request):
        if not _stripe_configured():
            return Response(
                {
                    'message': 'Stripe is not configured on the server.',
                    'status': 'error',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        ser_in = SavedCardCreateSerializer(data=request.data)
        valid = await sync_to_async(lambda: ser_in.is_valid())()
        if not valid:
            errors = await sync_to_async(lambda: ser_in.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vd = ser_in.validated_data
        pm_id = vd['payment_method_id'].strip()
        incoming_customer = (vd.get('stripe_customer_id') or '').strip()
        holder_role = await sync_to_async(holder_role_for_user)(request.user)

        def _do_save():
            # If frontend already created a customer (mobile SDK flows), store it on user and reuse.
            if incoming_customer:
                from apps.accounts.models import CustomUser

                u = CustomUser.objects.get(pk=request.user.pk)
                current = (getattr(u, 'stripe_customer_id', '') or '').strip()
                if current and current != incoming_customer:
                    raise ValueError(
                        'Stripe customer mismatch for this account. Please clear saved cards and re-add.'
                    )
                if not current:
                    u.stripe_customer_id = incoming_customer
                    u.save(update_fields=['stripe_customer_id'])

            return stripe_cards.save_card_for_user(
                request.user,
                payment_method_id=pm_id,
                holder_role=holder_role,
                nickname='',
                is_default=None,
            )

        try:
            obj = await sync_to_async(_do_save)()
        except RuntimeError as e:
            return Response(
                {'message': str(e), 'status': 'error'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ValueError as e:
            return Response(
                {'message': str(e), 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.StripeError as e:
            return Response(
                {
                    'message': getattr(e, 'user_message', None) or str(e),
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = SavedCardSerializer(obj)
        data = await sync_to_async(lambda: out.data)()
        return Response(
            {
                'message': 'Card saved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_201_CREATED,
        )


class SavedCardDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Payment: Saved cards'],
        summary='Set default saved card',
        description='Body: ``{ "is_default": true }`` to make this card the default for your role (driver/rider from groups).',
        request=SavedCardUpdateSerializer,
        responses={200: SavedCardSerializer},
    )
    async def put(self, request, pk):
        if not _stripe_configured():
            return Response(
                {
                    'message': 'Stripe is not configured on the server.',
                    'status': 'error',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        role = await sync_to_async(holder_role_for_user)(request.user)
        try:
            card = await SavedCard.objects.aget(
                pk=pk, user=request.user, is_active=True, holder_role=role
            )
        except SavedCard.DoesNotExist:
            return Response(
                {'message': 'Saved card not found.', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        ser_in = SavedCardUpdateSerializer(data=request.data)
        valid = await sync_to_async(lambda: ser_in.is_valid())()
        if not valid:
            errors = await sync_to_async(lambda: ser_in.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vd = ser_in.validated_data
        if not vd.get('is_default'):
            return Response(
                {
                    'message': 'Only is_default: true is supported (set this card as default).',
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        def _do_update():
            return stripe_cards.update_saved_card(card, is_default=True)

        try:
            obj = await sync_to_async(_do_update)()
        except RuntimeError as e:
            return Response(
                {'message': str(e), 'status': 'error'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        out = SavedCardSerializer(obj)
        data = await sync_to_async(lambda: out.data)()
        return Response(
            {
                'message': 'Saved card updated successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=['Payment: Saved cards'],
        summary='Remove saved card',
        description='Detaches the PaymentMethod in Stripe and marks the row inactive.',
        responses={200: None},
    )
    async def delete(self, request, pk):
        if not _stripe_configured():
            return Response(
                {
                    'message': 'Stripe is not configured on the server.',
                    'status': 'error',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        role = await sync_to_async(holder_role_for_user)(request.user)
        try:
            card = await SavedCard.objects.aget(
                pk=pk, user=request.user, is_active=True, holder_role=role
            )
        except SavedCard.DoesNotExist:
            return Response(
                {'message': 'Saved card not found.', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        def _do_delete():
            stripe_cards.soft_delete_saved_card(card)

        try:
            await sync_to_async(_do_delete)()
        except RuntimeError as e:
            return Response(
                {'message': str(e), 'status': 'error'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except stripe.error.StripeError as e:
            return Response(
                {
                    'message': getattr(e, 'user_message', None) or str(e),
                    'status': 'error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {'message': 'Saved card removed successfully', 'status': 'success'},
            status=status.HTTP_200_OK,
        )
