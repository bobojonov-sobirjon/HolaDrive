from __future__ import annotations

from asgiref.sync import sync_to_async
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from apps.common.views import AsyncAPIView
from apps.voice_call.models import VoiceCallSession
from apps.voice_call.serializers import CallActionSerializer, VoiceCallSessionListSerializer, VoiceCallSessionSerializer
from apps.voice_call.services.agora import build_rtc_token
from apps.voice_call.services.call_service import (
    CallServiceError,
    accept_call,
    end_call,
    get_call_for_user,
    list_calls_for_user,
    reject_call,
)
from apps.voice_call.views import _error_response, _serialize_call


class AdminVoiceCallsListView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=['Admin: Voice calls'],
        summary='List all voice calls',
        parameters=[
            OpenApiParameter('call_type', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: VoiceCallSessionListSerializer(many=True)},
    )
    async def get(self, request):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )

        call_type = request.query_params.get('call_type')
        call_status = request.query_params.get('status')
        page = int(request.query_params.get('page', 1))
        page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))

        def _query():
            qs = VoiceCallSession.objects.select_related(
                'caller', 'callee', 'order', 'support_room', 'recording'
            ).order_by('-created_at')
            if call_type:
                qs = qs.filter(call_type=call_type)
            if call_status:
                qs = qs.filter(status=call_status)
            total = qs.count()
            start = (page - 1) * page_size
            return list(qs[start : start + page_size]), total

        rows, total = await sync_to_async(_query)()
        ser = VoiceCallSessionListSerializer(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response(
            {
                'message': 'Voice calls retrieved',
                'status': 'success',
                'count': len(data),
                'total_count': total,
                'page': page,
                'page_size': page_size,
                'data': data,
            }
        )


class AdminVoiceCallDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        tags=['Admin: Voice calls'],
        summary='Voice call detail',
        responses={200: VoiceCallSessionSerializer},
    )
    async def get(self, request, call_id: int):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            call = await sync_to_async(get_call_for_user)(request.user, call_id)
        except CallServiceError as exc:
            return _error_response(exc, status.HTTP_404_NOT_FOUND)

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


class AdminVoiceCallAcceptView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=['Admin: Voice calls'], summary='Accept support call (admin panel)')
    async def post(self, request, call_id: int):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            result = await sync_to_async(accept_call)(user=request.user, call_id=call_id)
        except CallServiceError as exc:
            return _error_response(exc)
        data = await sync_to_async(_serialize_call)(result.call, request, result.agora)
        return Response({'message': 'Call accepted', 'status': 'success', 'data': data})


class AdminVoiceCallRejectView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=['Admin: Voice calls'], summary='Reject support call', request=CallActionSerializer)
    async def post(self, request, call_id: int):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
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


class AdminVoiceCallEndView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=['Admin: Voice calls'], summary='End call', request=CallActionSerializer)
    async def post(self, request, call_id: int):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
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


class AdminVoiceCallNoteView(AsyncAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(tags=['Admin: Voice calls'], summary='Add operator note after support call')
    async def patch(self, request, call_id: int):
        if not request.user.is_superuser:
            return Response(
                {'message': 'Only superusers can access admin panel APIs.', 'status': 'error'},
                status=status.HTTP_403_FORBIDDEN,
            )
        note = (request.data.get('operator_note') or '').strip()

        def _save():
            call = VoiceCallSession.objects.get(id=call_id)
            call.operator_note = note
            call.save(update_fields=['operator_note', 'updated_at'])
            return call

        try:
            call = await sync_to_async(_save)()
        except VoiceCallSession.DoesNotExist:
            return Response({'message': 'Call not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)

        data = await sync_to_async(_serialize_call)(call, request)
        return Response({'message': 'Note saved', 'status': 'success', 'data': data})
