from asgiref.sync import sync_to_async
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.views import AsyncAPIView

from ..models import (
    DriverIdentificationAgreementsItems,
    DriverIdentificationRegistrationAgreementsUserAccepted,
    DriverIdentificationRegistrationType,
)
from ..serializers.registration_terms import RegistrationTermsActionSerializer


class RegistrationTermsBaseView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    async def check_driver_permission(self, request):
        user = request.user
        groups = await sync_to_async(list)(user.groups.all())
        group_names = [g.name for g in groups]
        if 'Driver' not in group_names:
            return Response(
                {
                    'message': 'Only drivers can access this endpoint',
                    'status': 'error',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return None


class RegistrationTermsListView(RegistrationTermsBaseView):
    """
    GET /api/v1/accounts/driver/registration-terms/
    """

    @extend_schema(
        tags=['Registration Terms'],
        summary='List registration terms',
        description=(
            'Returns all **active** driver identification **registration** configurations '
            '(registration term groups from admin), each with nested **agreement items** '
            '(HTML content, optional file). Only items with `item_type=registration` are included.\n\n'
            'On each **registration type** object, `is_accepted` reflects whether the **current user** '
            'has accepted that configuration in `DriverIdentificationRegistrationAgreementsUserAccepted` '
            '(`is_accepted=true`). If there is no row or the stored flag is false, `is_accepted` is `false`. '
            'Agreement item objects do not include `is_accepted`.\n\n'
            '**Role:** Driver (JWT).'
        ),
    )
    async def get(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

        def load():
            reg_types = list(
                DriverIdentificationRegistrationType.objects.filter(is_active=True)
                .prefetch_related(
                    Prefetch(
                        'agreement_items',
                        queryset=DriverIdentificationAgreementsItems.objects.filter(
                            item_type='registration',
                        ).order_by('created_at', 'id'),
                    ),
                )
                .order_by('id')
            )
            type_ids = [t.pk for t in reg_types]
            rows = DriverIdentificationRegistrationAgreementsUserAccepted.objects.filter(
                user=user,
                driver_identification_registration_agreements_id__in=type_ids,
            )
            accepted = {r.driver_identification_registration_agreements_id: r.is_accepted for r in rows}

            out = []
            for t in reg_types:
                type_accepted = bool(accepted.get(t.pk, False))
                items_out = []
                for item in t.agreement_items.all():
                    file_url = None
                    if item.file:
                        file_url = request.build_absolute_uri(item.file.url)
                    items_out.append(
                        {
                            'id': item.pk,
                            'title': item.title,
                            'content': item.content,
                            'file': file_url,
                            'item_type': item.item_type,
                            'created_at': item.created_at,
                        }
                    )
                out.append(
                    {
                        'id': t.pk,
                        'title': t.title,
                        'description': t.description,
                        'display_type': t.display_type,
                        'is_active': t.is_active,
                        'is_accepted': type_accepted,
                        'created_at': t.created_at,
                        'updated_at': t.updated_at,
                        'agreement_items': items_out,
                    }
                )
            return out

        data = await sync_to_async(load)()

        return Response(
            {
                'message': 'Registration terms retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class RegistrationTermsAcceptView(RegistrationTermsBaseView):
    """
    POST /api/v1/accounts/driver/registration-terms/accept/
    """

    @extend_schema(
        tags=['Registration Terms'],
        summary='Accept registration terms',
        description=(
            'Records that the authenticated **driver** has **accepted** the given registration configuration.\n\n'
            'Creates or updates `DriverIdentificationRegistrationAgreementsUserAccepted` with '
            '`is_accepted=true` for `(request.user, registration_type_id)`.\n\n'
            '**Role:** Driver (JWT).'
        ),
        request=RegistrationTermsActionSerializer,
    )
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        serializer = RegistrationTermsActionSerializer(data=request.data)
        valid = await sync_to_async(serializer.is_valid)(raise_exception=False)
        if not valid:
            return Response(
                {'message': 'Validation failed', 'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        rid = serializer.validated_data['registration_type_id']

        def do_upsert():
            obj, _ = DriverIdentificationRegistrationAgreementsUserAccepted.objects.update_or_create(
                user=user,
                driver_identification_registration_agreements_id=rid,
                defaults={'is_accepted': True},
            )
            return obj

        obj = await sync_to_async(do_upsert)()

        return Response(
            {
                'message': 'Registration terms accepted successfully',
                'status': 'success',
                'data': {
                    'id': obj.pk,
                    'registration_type_id': rid,
                    'is_accepted': obj.is_accepted,
                },
            },
            status=status.HTTP_200_OK,
        )


class RegistrationTermsDeclineView(RegistrationTermsBaseView):
    """
    POST /api/v1/accounts/driver/registration-terms/decline/
    """

    @extend_schema(
        tags=['Registration Terms'],
        summary='Decline registration terms',
        description=(
            'Records that the authenticated **driver** has **declined** (or withdrawn acceptance for) '
            'the given registration configuration.\n\n'
            'Creates or updates `DriverIdentificationRegistrationAgreementsUserAccepted` with '
            '`is_accepted=false` for `(request.user, registration_type_id)`.\n\n'
            '**Role:** Driver (JWT).'
        ),
        request=RegistrationTermsActionSerializer,
    )
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        serializer = RegistrationTermsActionSerializer(data=request.data)
        valid = await sync_to_async(serializer.is_valid)(raise_exception=False)
        if not valid:
            return Response(
                {'message': 'Validation failed', 'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        rid = serializer.validated_data['registration_type_id']

        def do_upsert():
            obj, _ = DriverIdentificationRegistrationAgreementsUserAccepted.objects.update_or_create(
                user=user,
                driver_identification_registration_agreements_id=rid,
                defaults={'is_accepted': False},
            )
            return obj

        obj = await sync_to_async(do_upsert)()

        return Response(
            {
                'message': 'Registration terms declined successfully',
                'status': 'success',
                'data': {
                    'id': obj.pk,
                    'registration_type_id': rid,
                    'is_accepted': obj.is_accepted,
                },
            },
            status=status.HTTP_200_OK,
        )
