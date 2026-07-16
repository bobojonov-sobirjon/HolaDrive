from __future__ import annotations

from asgiref.sync import sync_to_async
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.views import AsyncAPIView
from apps.voice_call.serializers import (
    CallActionSerializer,
    SupportCallInitiateSerializer,
    SupportDirectCallInitiateSerializer,
    SupportDutySerializer,
    TripCallInitiateSerializer,
    VoiceCallSessionListSerializer,
    VoiceCallSessionSerializer,
)
from apps.voice_call.services.agora import build_rtc_token
from apps.voice_call.services.call_service import (
    CallServiceError,
    accept_call,
    cancel_call,
    end_call,
    get_call_for_user,
    initiate_support_call,
    initiate_trip_call,
    list_calls_for_user,
    reject_call,
    set_support_duty,
)


def _error_response(exc: CallServiceError, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            'message': exc.message,
            'status': 'error',
            'code': exc.code,
            'errors': exc.errors,
        },
        status=http_status,
    )


def _serialize_call(call, request, agora=None):
    ser = VoiceCallSessionSerializer(call, context={'request': request, 'agora': agora})
    return ser.data


class TripCallInitiateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Voice calls'],
        summary='Start trip call (rider→driver or driver→rider)',
        request=TripCallInitiateSerializer,
        responses={201: VoiceCallSessionSerializer},
    )
    async def post(self, request):
        ser = TripCallInitiateSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = await sync_to_async(initiate_trip_call)(
                user=request.user,
                order_id=ser.validated_data['order_id'],
            )
        except CallServiceError as exc:
            code = status.HTTP_404_NOT_FOUND if exc.code == 'not_found' else status.HTTP_400_BAD_REQUEST
            if exc.code == 'forbidden':
                code = status.HTTP_403_FORBIDDEN
            return _error_response(exc, code)

        data = await sync_to_async(_serialize_call)(result.call, request, result.agora)
        return Response(
            {'message': 'Call initiated', 'status': 'success', 'data': data},
            status=status.HTTP_201_CREATED,
        )


class SupportCallInitiateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Voice calls'],
        summary='Start support call (optional order)',
        description=(
            'Rider/driver → admin. '
            '`order_id` optional: send it to attach call to an order, or omit / null for general support. '
            'For a dedicated order-less endpoint see POST /api/v1/voice-call/support/direct/.'
        ),
        request=SupportCallInitiateSerializer,
        responses={201: VoiceCallSessionSerializer},
    )
    async def post(self, request):
        ser = SupportCallInitiateSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = await sync_to_async(initiate_support_call)(
                user=request.user,
                order_id=ser.validated_data.get('order_id'),
            )
        except CallServiceError as exc:
            code = status.HTTP_403_FORBIDDEN if exc.code == 'forbidden' else status.HTTP_400_BAD_REQUEST
            return _error_response(exc, code)

        data = await sync_to_async(_serialize_call)(result.call, request, result.agora)
        return Response(
            {'message': 'Support call initiated', 'status': 'success', 'data': data},
            status=status.HTTP_201_CREATED,
        )


class SupportDirectCallInitiateView(AsyncAPIView):
    """General support call with no order (rider/driver → admin)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Voice calls'],
        summary='Start support call without order',
        description=(
            'Rider or driver calls support/admin with no order context. '
            'Body may be empty `{}`. Same accept/reject/end flow as other support calls.'
        ),
        request=SupportDirectCallInitiateSerializer,
        responses={201: VoiceCallSessionSerializer},
    )
    async def post(self, request):
        try:
            result = await sync_to_async(initiate_support_call)(
                user=request.user,
                order_id=None,
            )
        except CallServiceError as exc:
            code = status.HTTP_403_FORBIDDEN if exc.code == 'forbidden' else status.HTTP_400_BAD_REQUEST
            return _error_response(exc, code)

        data = await sync_to_async(_serialize_call)(result.call, request, result.agora)
        return Response(
            {
                'message': 'Support call initiated (no order)',
                'status': 'success',
                'data': data,
            },
            status=status.HTTP_201_CREATED,
        )


class CallAcceptView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Voice calls'], summary='Accept incoming call', responses={200: VoiceCallSessionSerializer})
    async def post(self, request, call_id: int):
        try:
            result = await sync_to_async(accept_call)(user=request.user, call_id=call_id)
        except CallServiceError as exc:
            code = status.HTTP_404_NOT_FOUND if exc.code == 'not_found' else status.HTTP_400_BAD_REQUEST
            if exc.code == 'forbidden':
                code = status.HTTP_403_FORBIDDEN
            return _error_response(exc, code)
        data = await sync_to_async(_serialize_call)(result.call, request, result.agora)
        return Response({'message': 'Call accepted', 'status': 'success', 'data': data})


class CallRejectView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Voice calls'], summary='Reject incoming call', request=CallActionSerializer)
    async def post(self, request, call_id: int):
        ser = CallActionSerializer(data=request.data)
        await sync_to_async(lambda: ser.is_valid(raise_exception=True))()
        try:
            call = await sync_to_async(reject_call)(
                user=request.user,
                call_id=call_id,
                reason=ser.validated_data.get('reason', ''),
            )
        except CallServiceError as exc:
            return _error_response(exc)
        data = await sync_to_async(_serialize_call)(call, request)
        return Response({'message': 'Call rejected', 'status': 'success', 'data': data})


class CallCancelView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Voice calls'], summary='Cancel outgoing ringing call', request=CallActionSerializer)
    async def post(self, request, call_id: int):
        ser = CallActionSerializer(data=request.data)
        await sync_to_async(lambda: ser.is_valid(raise_exception=True))()
        try:
            call = await sync_to_async(cancel_call)(
                user=request.user,
                call_id=call_id,
                reason=ser.validated_data.get('reason', ''),
            )
        except CallServiceError as exc:
            return _error_response(exc)
        data = await sync_to_async(_serialize_call)(call, request)
        return Response({'message': 'Call cancelled', 'status': 'success', 'data': data})


class CallEndView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Voice calls'], summary='End active or ringing call', request=CallActionSerializer)
    async def post(self, request, call_id: int):
        ser = CallActionSerializer(data=request.data)
        await sync_to_async(lambda: ser.is_valid(raise_exception=True))()
        try:
            call = await sync_to_async(end_call)(
                user=request.user,
                call_id=call_id,
                reason=ser.validated_data.get('reason', ''),
            )
        except CallServiceError as exc:
            return _error_response(exc)
        data = await sync_to_async(_serialize_call)(call, request)
        return Response({'message': 'Call ended', 'status': 'success', 'data': data})


class CallDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Voice calls'], summary='Call detail + fresh Agora token if active', responses={200: VoiceCallSessionSerializer})
    async def get(self, request, call_id: int):
        try:
            call = await sync_to_async(get_call_for_user)(request.user, call_id)
        except CallServiceError as exc:
            code = status.HTTP_404_NOT_FOUND if exc.code == 'not_found' else status.HTTP_403_FORBIDDEN
            return _error_response(exc, code)

        agora = None
        if call.status in ('ringing', 'answered'):
            try:
                agora = await sync_to_async(build_rtc_token)(
                    channel_name=call.agora_channel_name,
                    user_id=request.user.id,
                )
            except Exception:
                agora = None

        data = await sync_to_async(_serialize_call)(call, request, agora)
        return Response({'message': 'OK', 'status': 'success', 'data': data})


class CallHistoryView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Voice calls'],
        summary='Call history',
        parameters=[
            OpenApiParameter('call_type', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: VoiceCallSessionListSerializer(many=True)},
    )
    async def get(self, request):
        call_type = request.query_params.get('call_type')
        page = int(request.query_params.get('page', 1))
        page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))

        rows, total = await sync_to_async(list_calls_for_user)(
            request.user,
            call_type=call_type,
            page=page,
            page_size=page_size,
        )
        ser = VoiceCallSessionListSerializer(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response(
            {
                'message': 'Call history',
                'status': 'success',
                'count': len(data),
                'total_count': total,
                'page': page,
                'page_size': page_size,
                'data': data,
            }
        )


class SupportDutyView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Voice calls — Admin'], summary='Set support on-duty status', request=SupportDutySerializer)
    async def post(self, request):
        ser = SupportDutySerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            duty = await sync_to_async(set_support_duty)(
                admin=request.user,
                is_on_duty=ser.validated_data['is_on_duty'],
            )
        except CallServiceError as exc:
            return _error_response(exc, status.HTTP_403_FORBIDDEN)

        return Response(
            {
                'message': 'Support duty updated',
                'status': 'success',
                'data': {
                    'admin_id': duty.admin_id,
                    'is_on_duty': duty.is_on_duty,
                    'updated_at': duty.updated_at,
                },
            }
        )

    @extend_schema(tags=['Voice calls — Admin'], summary='Get my support on-duty status')
    async def get(self, request):
        from apps.voice_call.models import SupportAgentDuty

        duty = await sync_to_async(
            lambda: SupportAgentDuty.objects.filter(admin=request.user).first()
        )()
        return Response(
            {
                'message': 'OK',
                'status': 'success',
                'data': {
                    'admin_id': request.user.id,
                    'is_on_duty': bool(duty and duty.is_on_duty),
                    'updated_at': duty.updated_at if duty else None,
                },
            }
        )
