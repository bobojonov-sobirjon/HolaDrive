"""
Driver identification checklist: combined upload / terms / legal steps, detail, and submissions.
"""

from asgiref.sync import sync_to_async
from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from ..models import (
    DriverIdentificationLegalAgreementsUserAccepted,
    DriverIdentificationLegalType,
    DriverIdentificationTermsType,
    DriverIdentificationUploadType,
    DriverIdentificationUploadTypeItem,
    DriverIdentificationUploadTypeQuestionAnswer,
    DriverIdentificationUploadTypeUserAccepted,
)
from ..serializers.driver_identification import (
    IdentificationLegalTypeActionSerializer,
    IdentificationTermsTypeActionSerializer,
    IdentificationUploadSubmitSerializer,
)
from ..driver_identification_services import (
    apply_terms_acceptance,
    build_checklist_payload,
    legal_agreement_items,
    pick_question_answer_id_for_submit,
    question_answer_ids_by_upload_type,
    terms_agreement_items,
)
from .driver_verification import DriverVerificationBaseView


def _absolute_file_url(request, f):
    if not f or not getattr(f, 'url', None):
        return None
    return request.build_absolute_uri(f.url)


class DriverIdentificationChecklistView(DriverVerificationBaseView):
    """
    GET /api/v1/accounts/driver/identification/checklist/
    """

    @extend_schema(
        tags=['Driver Identification'],
        summary='List identification checklist steps',
        description=(
            'Returns a single ordered list for the Identification screen: **upload**, **terms**, and **legal** '
            'configurations that are active. Each row includes `kind` (`upload` | `terms` | `legal`), `id`, `title`, '
            'and `is_accepted`.\n\n'
            '**Upload (`kind=upload`):** `is_accepted` is true when every required checklist slot has a stored file '
            'and `is_accepted` on `DriverIdentificationUploadTypeUserAccepted`. If the step has no question/slot rows, '
            'one type-level submission (`question_answer` null) is used.\n\n'
            '**Terms (`kind=terms`):** `is_accepted` is true only when the user has accepted **every** '
            '`DriverIdentificationAgreementsItems` with `item_type=terms` linked to that terms type '
            '(`DriverIdentificationTermsItemUserAccepted`).\n\n'
            '**Legal (`kind=legal`):** `is_accepted` follows `DriverIdentificationLegalAgreementsUserAccepted` '
            'for that legal type (same idea as registration terms).\n\n'
            '**Role:** Driver (JWT).'
        ),
        responses={
            200: OpenApiResponse(description='Checklist rows with kind, id, title, is_accepted.'),
        },
    )
    async def get(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        data = await sync_to_async(build_checklist_payload)(request.user)

        return Response(
            {
                'message': 'Identification checklist retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class DriverIdentificationUploadTypeDetailView(DriverVerificationBaseView):
    """
    GET /api/v1/accounts/driver/identification/upload-types/<id>/
    """

    @extend_schema(
        tags=['Driver Identification'],
        summary='Get upload identification step detail',
        description=(
            'Returns one **upload** identification type with nested **items** (checklist steps) and '
            '**question_answers** (slots). Each slot includes `template_file` (admin reference) and `user_file` '
            'when the driver has submitted a file for that slot. Optional `type_user_file` is set when the step uses '
            'a single type-level upload (no slots).\n\n'
            '**Role:** Driver (JWT).'
        ),
        responses={200: OpenApiResponse(description='Upload type with items and question_answers.')},
    )
    async def get(self, request, pk):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user

        def load():
            try:
                obj = (
                    DriverIdentificationUploadType.objects.filter(
                        pk=pk,
                        is_active=True,
                        display_type='upload',
                    )
                    .prefetch_related(
                        Prefetch(
                            'items',
                            queryset=DriverIdentificationUploadTypeItem.objects.prefetch_related(
                                Prefetch(
                                    'question_answers',
                                    queryset=DriverIdentificationUploadTypeQuestionAnswer.objects.order_by(
                                        'created_at', 'id'
                                    ),
                                )
                            ).order_by('created_at', 'id'),
                        ),
                    )
                    .get()
                )
            except DriverIdentificationUploadType.DoesNotExist:
                return None

            qa_ids_for_type = question_answer_ids_by_upload_type([obj.pk]).get(obj.pk, [])
            user_rows = {
                r.question_answer_id: r
                for r in DriverIdentificationUploadTypeUserAccepted.objects.filter(
                    user=user,
                    driver_identification_upload_type=obj,
                )
            }
            type_level = user_rows.get(None)

            items_out = []
            for it in obj.items.all():
                qas_out = []
                for qa in it.question_answers.all():
                    ua = user_rows.get(qa.pk)
                    qas_out.append(
                        {
                            'id': qa.pk,
                            'question': qa.question,
                            'template_file': _absolute_file_url(request, qa.file),
                            'user_file': _absolute_file_url(request, ua.file) if ua else None,
                            'is_submitted': bool(
                                ua and ua.is_accepted and ua.file and getattr(ua.file, 'name', '')
                            ),
                            'created_at': qa.created_at,
                        }
                    )
                items_out.append(
                    {
                        'id': it.pk,
                        'title': it.item,
                        'created_at': it.created_at,
                        'question_answers': qas_out,
                    }
                )

            return {
                'id': obj.pk,
                'title': obj.title,
                'description': obj.description or '',
                'display_type': obj.display_type,
                'is_active': obj.is_active,
                'icon': _absolute_file_url(request, obj.icon),
                'type_user_file': _absolute_file_url(request, type_level.file) if type_level else None,
                'type_level_submitted': bool(
                    type_level
                    and type_level.is_accepted
                    and type_level.file
                    and getattr(type_level.file, 'name', '')
                    and not qa_ids_for_type
                ),
                'items': items_out,
            }

        data = await sync_to_async(load)()
        if data is None:
            return Response(
                {'message': 'Upload identification type not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'message': 'Upload identification detail retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class DriverIdentificationLegalTypeDetailView(DriverVerificationBaseView):
    """
    GET /api/v1/accounts/driver/identification/legal-types/<id>/
    """

    @extend_schema(
        tags=['Driver Identification'],
        summary='Get legal agreements identification detail',
        description=(
            'Returns a **legal** identification type and its `agreement_items` (`item_type=legal`).\n\n'
            '**Role:** Driver (JWT).'
        ),
        responses={200: OpenApiResponse(description='Legal type with agreement_items.')},
    )
    async def get(self, request, pk):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        def load():
            try:
                obj = DriverIdentificationLegalType.objects.get(
                    pk=pk,
                    is_active=True,
                    display_type='legal',
                )
            except DriverIdentificationLegalType.DoesNotExist:
                return None

            items_out = []
            for item in legal_agreement_items(obj):
                items_out.append(
                    {
                        'id': item.pk,
                        'title': item.title,
                        'content': item.content,
                        'file': _absolute_file_url(request, item.file),
                        'item_type': item.item_type,
                        'created_at': item.created_at,
                    }
                )

            return {
                'id': obj.pk,
                'title': obj.title,
                'description': obj.description or '',
                'display_type': obj.display_type,
                'is_active': obj.is_active,
                'agreement_items': items_out,
            }

        data = await sync_to_async(load)()
        if data is None:
            return Response(
                {'message': 'Legal identification type not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'message': 'Legal identification detail retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class DriverIdentificationTermsTypeDetailView(DriverVerificationBaseView):
    """
    GET /api/v1/accounts/driver/identification/terms-types/<id>/
    """

    @extend_schema(
        tags=['Driver Identification'],
        summary='Get terms identification detail',
        description=(
            'Returns a **terms** identification type and its `agreement_items` (`item_type=terms`).\n\n'
            '**Role:** Driver (JWT).'
        ),
        responses={200: OpenApiResponse(description='Terms type with agreement_items.')},
    )
    async def get(self, request, pk):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        def load():
            try:
                obj = DriverIdentificationTermsType.objects.get(
                    pk=pk,
                    is_active=True,
                    display_type='terms',
                )
            except DriverIdentificationTermsType.DoesNotExist:
                return None

            items_out = []
            for item in terms_agreement_items(obj):
                items_out.append(
                    {
                        'id': item.pk,
                        'title': item.title,
                        'content': item.content,
                        'file': _absolute_file_url(request, item.file),
                        'item_type': item.item_type,
                        'created_at': item.created_at,
                    }
                )

            return {
                'id': obj.pk,
                'title': obj.title,
                'description': obj.description or '',
                'display_type': obj.display_type,
                'is_active': obj.is_active,
                'agreement_items': items_out,
            }

        data = await sync_to_async(load)()
        if data is None:
            return Response(
                {'message': 'Terms identification type not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'message': 'Terms identification detail retrieved successfully',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class DriverIdentificationUploadSubmitView(DriverVerificationBaseView):
    """
    POST /api/v1/accounts/driver/identification/upload-types/submit/
    """

    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=['Driver Identification'],
        summary='Submit upload identification file',
        description=(
            'Use **multipart/form-data**: **`upload_type_id`** and **`file`** only.\n\n'
            'If the step has checklist slots, the server picks the slot in admin order: '
            'the first slot that is not yet complete; if every slot is already complete, the first slot is updated.\n\n'
            'If there are no slots, a single type-level file is stored.\n\n'
            'Creates or updates `DriverIdentificationUploadTypeUserAccepted` for `request.user` with '
            '`is_accepted=true`.\n\n'
            '**Role:** Driver (JWT).'
        ),
        request=IdentificationUploadSubmitSerializer,
        responses={
            200: OpenApiResponse(description='Submission stored; returns record id, upload_type_id, file URL, is_accepted.'),
            400: OpenApiResponse(description='Validation error.'),
        },
    )
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        user = request.user
        try:
            upload_type_id = int(request.POST.get('upload_type_id', ''))
        except (TypeError, ValueError):
            return Response(
                {'message': 'upload_type_id is required and must be an integer', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload_file = request.FILES.get('file')
        if not upload_file:
            return Response(
                {'message': 'file is required', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def submit():
            try:
                upload = DriverIdentificationUploadType.objects.get(
                    pk=upload_type_id,
                    is_active=True,
                    display_type='upload',
                )
            except DriverIdentificationUploadType.DoesNotExist:
                return None, 'Upload identification type not found'

            qa_ids = question_answer_ids_by_upload_type([upload.pk]).get(upload.pk, [])

            if qa_ids:
                qid = pick_question_answer_id_for_submit(user.pk, qa_ids)
                qa = DriverIdentificationUploadTypeQuestionAnswer.objects.get(pk=qid)
                obj, _ = DriverIdentificationUploadTypeUserAccepted.objects.update_or_create(
                    user=user,
                    question_answer=qa,
                    defaults={
                        'driver_identification_upload_type': upload,
                        'file': upload_file,
                        'is_accepted': True,
                    },
                )
                return obj, None

            obj, _ = DriverIdentificationUploadTypeUserAccepted.objects.update_or_create(
                user=user,
                driver_identification_upload_type=upload,
                question_answer=None,
                defaults={
                    'file': upload_file,
                    'is_accepted': True,
                },
            )
            return obj, None

        obj, err = await sync_to_async(submit)()
        if err:
            st = (
                status.HTTP_404_NOT_FOUND
                if err == 'Upload identification type not found'
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({'message': err, 'status': 'error'}, status=st)

        return Response(
            {
                'message': 'Upload submitted successfully',
                'status': 'success',
                'data': {
                    'id': obj.pk,
                    'upload_type_id': upload_type_id,
                    'file': _absolute_file_url(request, obj.file),
                    'is_accepted': obj.is_accepted,
                },
            },
            status=status.HTTP_200_OK,
        )


class DriverIdentificationLegalAcceptView(DriverVerificationBaseView):
    """POST .../legal-types/accept/"""

    @extend_schema(
        tags=['Driver Identification'],
        summary='Accept legal identification agreements',
        description=(
            'Same contract as registration terms: JSON body **`legal_type_id`**. '
            'Sets `DriverIdentificationLegalAgreementsUserAccepted.is_accepted=true` for the current user.\n\n'
            '**Role:** Driver (JWT).'
        ),
        request=IdentificationLegalTypeActionSerializer,
    )
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        serializer = IdentificationLegalTypeActionSerializer(data=request.data)
        valid = await sync_to_async(serializer.is_valid)(raise_exception=False)
        if not valid:
            return Response(
                {'message': 'Validation failed', 'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        lid = serializer.validated_data['legal_type_id']

        def upsert():
            obj, _ = DriverIdentificationLegalAgreementsUserAccepted.objects.update_or_create(
                user=user,
                driver_identification_legal_agreements_id=lid,
                defaults={'is_accepted': True},
            )
            return obj

        obj = await sync_to_async(upsert)()

        return Response(
            {
                'message': 'Legal agreements accepted successfully',
                'status': 'success',
                'data': {
                    'id': obj.pk,
                    'legal_type_id': lid,
                    'is_accepted': obj.is_accepted,
                },
            },
            status=status.HTTP_200_OK,
        )


class DriverIdentificationLegalDeclineView(DriverVerificationBaseView):
    """POST .../legal-types/decline/"""

    @extend_schema(
        tags=['Driver Identification'],
        summary='Decline legal identification agreements',
        description=(
            'JSON body **`legal_type_id`**. Sets `is_accepted=false` for the current user.\n\n'
            '**Role:** Driver (JWT).'
        ),
        request=IdentificationLegalTypeActionSerializer,
    )
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        serializer = IdentificationLegalTypeActionSerializer(data=request.data)
        valid = await sync_to_async(serializer.is_valid)(raise_exception=False)
        if not valid:
            return Response(
                {'message': 'Validation failed', 'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        lid = serializer.validated_data['legal_type_id']

        def upsert():
            obj, _ = DriverIdentificationLegalAgreementsUserAccepted.objects.update_or_create(
                user=user,
                driver_identification_legal_agreements_id=lid,
                defaults={'is_accepted': False},
            )
            return obj

        obj = await sync_to_async(upsert)()

        return Response(
            {
                'message': 'Legal agreements declined successfully',
                'status': 'success',
                'data': {
                    'id': obj.pk,
                    'legal_type_id': lid,
                    'is_accepted': obj.is_accepted,
                },
            },
            status=status.HTTP_200_OK,
        )


class DriverIdentificationTermsAcceptView(DriverVerificationBaseView):
    """POST .../terms-types/accept/"""

    @extend_schema(
        tags=['Driver Identification'],
        summary='Accept terms identification (all agreement items)',
        description=(
            'JSON body **`terms_type_id`**. For every `DriverIdentificationAgreementsItems` linked to that '
            'terms type with `item_type=terms`, creates or updates `DriverIdentificationTermsItemUserAccepted` '
            'with `is_accepted=true`.\n\n'
            '**Role:** Driver (JWT).'
        ),
        request=IdentificationTermsTypeActionSerializer,
    )
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        serializer = IdentificationTermsTypeActionSerializer(data=request.data)
        valid = await sync_to_async(serializer.is_valid)(raise_exception=False)
        if not valid:
            return Response(
                {'message': 'Validation failed', 'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        tid = serializer.validated_data['terms_type_id']

        def apply():
            obj = DriverIdentificationTermsType.objects.get(pk=tid)
            apply_terms_acceptance(user, obj, True)
            count = terms_agreement_items(obj).count()
            return count

        try:
            count = await sync_to_async(apply)()
        except DriverIdentificationTermsType.DoesNotExist:
            return Response(
                {'message': 'Terms identification type not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'message': 'Terms accepted successfully',
                'status': 'success',
                'data': {
                    'terms_type_id': tid,
                    'agreement_items_updated': count,
                    'is_accepted': count > 0,
                },
            },
            status=status.HTTP_200_OK,
        )


class DriverIdentificationTermsDeclineView(DriverVerificationBaseView):
    """POST .../terms-types/decline/"""

    @extend_schema(
        tags=['Driver Identification'],
        summary='Decline terms identification (all agreement items)',
        description=(
            'JSON body **`terms_type_id`**. Sets `is_accepted=false` on every linked terms agreement item '
            'for the current user.\n\n'
            '**Role:** Driver (JWT).'
        ),
        request=IdentificationTermsTypeActionSerializer,
    )
    async def post(self, request):
        permission_error = await self.check_driver_permission(request)
        if permission_error:
            return permission_error

        serializer = IdentificationTermsTypeActionSerializer(data=request.data)
        valid = await sync_to_async(serializer.is_valid)(raise_exception=False)
        if not valid:
            return Response(
                {'message': 'Validation failed', 'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        tid = serializer.validated_data['terms_type_id']

        def apply():
            obj = DriverIdentificationTermsType.objects.get(pk=tid)
            apply_terms_acceptance(user, obj, False)
            count = terms_agreement_items(obj).count()
            return count

        try:
            count = await sync_to_async(apply)()
        except DriverIdentificationTermsType.DoesNotExist:
            return Response(
                {'message': 'Terms identification type not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                'message': 'Terms declined successfully',
                'status': 'success',
                'data': {
                    'terms_type_id': tid,
                    'agreement_items_updated': count,
                    'is_accepted': False,
                },
            },
            status=status.HTTP_200_OK,
        )
