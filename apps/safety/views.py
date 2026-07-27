from __future__ import annotations

from asgiref.sync import sync_to_async
from django.db.models import Prefetch
from django.shortcuts import render
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.views import AsyncAPIView
from apps.safety.models import SafetyMessage, SafetyRoom, TripShareLink, TripVoiceRecording
from apps.safety.serializers import (
    SafetyMessageCreateSerializer,
    SafetyMessageSerializer,
    SafetyRoomOpenSerializer,
    SafetyRoomSerializer,
    TripShareCreateSerializer,
    TripShareLinkSerializer,
    TripVoiceRecordingSerializer,
    VoiceRecordingStartSerializer,
    VoiceRecordingStopSerializer,
)
from apps.safety.services import (
    SafetyServiceError,
    build_public_share_payload,
    create_trip_share,
    get_valid_share_link,
    open_safety_room,
    revoke_trip_share,
    start_voice_recording,
    stop_voice_recording,
)


def _is_staff(user) -> bool:
    return bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))


def _error(exc: SafetyServiceError, http_status=None):
    if http_status is None:
        http_status = status.HTTP_400_BAD_REQUEST
        if exc.code == 'not_found':
            http_status = status.HTTP_404_NOT_FOUND
        elif exc.code == 'forbidden':
            http_status = status.HTTP_403_FORBIDDEN
    return Response(
        {
            'message': exc.message,
            'status': 'error',
            'code': exc.code,
            'errors': exc.errors,
        },
        status=http_status,
    )


class SafetyToolsConfigView(AsyncAPIView):
    """Menu metadata for Safety tools UI."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Safety tools'], summary='Safety tools config')
    async def get(self, request):
        from django.conf import settings

        return Response(
            {
                'message': 'Safety tools',
                'status': 'success',
                'data': {
                    'emergency_number': getattr(settings, 'SAFETY_EMERGENCY_NUMBER', '911'),
                    'emergency_tel_uri': f"tel:{getattr(settings, 'SAFETY_EMERGENCY_NUMBER', '911')}",
                    'features': {
                        'contact_911': True,
                        'contact_safety_agent': True,
                        'voice_recording': True,
                        'share_trip_status': True,
                    },
                },
            }
        )


class TripShareCreateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Safety tools'],
        summary='Create share trip status link',
        request=TripShareCreateSerializer,
        responses={201: TripShareLinkSerializer},
    )
    async def post(self, request):
        ser = TripShareCreateSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            link = await sync_to_async(create_trip_share)(
                user=request.user,
                order_id=ser.validated_data['order_id'],
            )
        except SafetyServiceError as exc:
            return _error(exc)

        data = await sync_to_async(
            lambda: TripShareLinkSerializer(link, context={'request': request}).data
        )()
        from django.conf import settings as dj_settings

        return Response(
            {
                'message': 'Share link created',
                'status': 'success',
                'data': {
                    **data,
                    'ws_url_path': f'/ws/safety/share/{link.token}/',
                    'how_to_share': (
                        'Share share_url via system share sheet. '
                        'Recipient opens HTTPS link → tries HolaDrive app; '
                        'if not installed → App Store (iOS) / Google Play (Android). '
                        'App must handle deep_link holadrive://trip/share/<token>.'
                    ),
                    'store_urls': {
                        'ios': getattr(dj_settings, 'IOS_APP_STORE_URL', ''),
                        'android': getattr(dj_settings, 'ANDROID_PLAY_STORE_URL', ''),
                    },
                },
            },
            status=status.HTTP_201_CREATED,
        )


class TripShareMobilePageView(APIView):
    """
    Share landing page:
    1) Try open mobile app via deep link
    2) If app missing → App Store (iOS) / Google Play (Android)
    3) Optional browser tracking fallback
    URL: /trip/share/<token>/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token: str):
        from django.conf import settings

        ua = (request.META.get('HTTP_USER_AGENT') or '').lower()
        is_android = 'android' in ua
        store_url = (
            getattr(settings, 'ANDROID_PLAY_STORE_URL', '')
            if is_android
            else getattr(settings, 'IOS_APP_STORE_URL', '')
        )
        # Desktop / unknown → Play as default store button (or iOS); both shown via JS platform detect too
        if not is_android and 'iphone' not in ua and 'ipad' not in ua and 'ipod' not in ua:
            store_url = getattr(settings, 'IOS_APP_STORE_URL', '') or store_url

        scheme = getattr(settings, 'APP_DEEP_LINK_SCHEME', 'holadrive') or 'holadrive'
        deep_link = f'{scheme}://trip/share/{token}'

        try:
            link = get_valid_share_link(token)
            deep_link = link.deep_link
            ctx = {
                'token': link.token,
                'deep_link': deep_link,
                'store_url': store_url,
            }
            status_code = 200
        except SafetyServiceError as exc:
            ctx = {
                'token': token,
                'deep_link': deep_link,
                'store_url': store_url,
                'error': exc.message,
            }
            status_code = 410 if exc.code in ('share_inactive', 'trip_ended') else 404

        return render(request, 'safety/trip_share.html', ctx, status=status_code)


class TripShareListView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Safety tools'], summary='List my active share links')
    async def get(self, request):
        def _list():
            qs = (
                TripShareLink.objects.filter(created_by=request.user, is_active=True)
                .select_related('order')
                .order_by('-created_at')[:50]
            )
            return TripShareLinkSerializer(qs, many=True, context={'request': request}).data

        data = await sync_to_async(_list)()
        return Response({'message': 'OK', 'status': 'success', 'data': data})


class TripShareRevokeView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Safety tools'], summary='Revoke share link')
    async def delete(self, request, token: str):
        try:
            link = await sync_to_async(revoke_trip_share)(user=request.user, token=token)
        except SafetyServiceError as exc:
            return _error(exc)
        data = await sync_to_async(
            lambda: TripShareLinkSerializer(link, context={'request': request}).data
        )()
        return Response({'message': 'Share link revoked', 'status': 'success', 'data': data})


class TripSharePublicView(AsyncAPIView):
    """Public trip status for friends (no login)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=['Safety tools'], summary='Public share trip status (no auth)')
    async def get(self, request, token: str):
        try:
            link = await sync_to_async(get_valid_share_link)(token)
            payload = await sync_to_async(build_public_share_payload)(link)
        except SafetyServiceError as exc:
            return _error(exc)
        return Response({'message': 'OK', 'status': 'success', 'data': payload})


class SafetyRoomOpenView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Safety tools'],
        summary='Open safety agent chat',
        request=SafetyRoomOpenSerializer,
        responses={200: SafetyRoomSerializer},
    )
    async def post(self, request):
        ser = SafetyRoomOpenSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            room = await sync_to_async(open_safety_room)(
                user=request.user,
                order_id=ser.validated_data.get('order_id'),
            )
        except SafetyServiceError as exc:
            return _error(exc)

        def _ser():
            room_full = SafetyRoom.objects.prefetch_related(
                'orders',
                Prefetch('messages', queryset=SafetyMessage.objects.select_related('sender')),
            ).get(pk=room.pk)
            return SafetyRoomSerializer(room_full, context={'request': request}).data

        data = await sync_to_async(_ser)()
        return Response({'message': 'Safety room ready', 'status': 'success', 'data': data})


class SafetyRoomListView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Safety tools'], summary='List safety rooms')
    async def get(self, request):
        def _list():
            if _is_staff(request.user):
                qs = SafetyRoom.objects.all().select_related('user', 'agent').prefetch_related('orders')
            else:
                qs = (
                    SafetyRoom.objects.filter(user=request.user)
                    .select_related('user', 'agent')
                    .prefetch_related('orders')
                )
            qs = qs.order_by('-updated_at')[:100]
            return SafetyRoomSerializer(qs, many=True, context={'request': request}).data

        data = await sync_to_async(_list)()
        return Response({'message': 'OK', 'status': 'success', 'data': data})


class SafetyRoomDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Safety tools'], summary='Safety room detail')
    async def get(self, request, room_id: int):
        def _get():
            try:
                room = SafetyRoom.objects.select_related('user', 'agent').prefetch_related(
                    'orders',
                    Prefetch('messages', queryset=SafetyMessage.objects.select_related('sender')),
                ).get(pk=room_id)
            except SafetyRoom.DoesNotExist:
                return None, 'not_found'
            if room.user_id != request.user.id and room.agent_id != request.user.id and not _is_staff(request.user):
                return None, 'forbidden'
            return SafetyRoomSerializer(room, context={'request': request}).data, None

        data, err = await sync_to_async(_get)()
        if err == 'not_found':
            return Response(
                {'message': 'Room not found', 'status': 'error', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if err == 'forbidden':
            return Response(
                {'message': 'Forbidden', 'status': 'error', 'code': 'forbidden'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({'message': 'OK', 'status': 'success', 'data': data})


class SafetyRoomMessagesView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Safety tools'],
        summary='List safety messages',
        parameters=[
            OpenApiParameter('page', OpenApiTypes.INT, required=False),
            OpenApiParameter('page_size', OpenApiTypes.INT, required=False),
        ],
    )
    async def get(self, request, room_id: int):
        def _list():
            try:
                room = SafetyRoom.objects.get(pk=room_id)
            except SafetyRoom.DoesNotExist:
                return None, 'not_found'
            if room.user_id != request.user.id and room.agent_id != request.user.id and not _is_staff(request.user):
                return None, 'forbidden'
            try:
                page = max(1, int(request.query_params.get('page') or 1))
                page_size = min(100, max(1, int(request.query_params.get('page_size') or 50)))
            except ValueError:
                page, page_size = 1, 50
            qs = SafetyMessage.objects.filter(room=room).select_related('sender').order_by('-created_at')
            total = qs.count()
            start = (page - 1) * page_size
            items = list(qs[start : start + page_size])
            items.reverse()
            return {
                'count': total,
                'page': page,
                'page_size': page_size,
                'results': SafetyMessageSerializer(items, many=True).data,
            }, None

        data, err = await sync_to_async(_list)()
        if err == 'not_found':
            return Response(
                {'message': 'Room not found', 'status': 'error', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if err == 'forbidden':
            return Response(
                {'message': 'Forbidden', 'status': 'error', 'code': 'forbidden'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({'message': 'OK', 'status': 'success', 'data': data})

    @extend_schema(
        tags=['Safety tools'],
        summary='Send safety message',
        request=SafetyMessageCreateSerializer,
    )
    async def post(self, request, room_id: int):
        ser = SafetyMessageCreateSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def _send():
            try:
                room = SafetyRoom.objects.get(pk=room_id)
            except SafetyRoom.DoesNotExist:
                raise SafetyServiceError('Room not found.', code='not_found')
            if room.user_id != request.user.id and room.agent_id != request.user.id and not _is_staff(request.user):
                raise SafetyServiceError('Forbidden.', code='forbidden')

            msg_type = SafetyMessage.MessageType.AGENT if _is_staff(request.user) else SafetyMessage.MessageType.USER
            order_id = ser.validated_data.get('order_id')
            order = None
            if order_id:
                from apps.order.models import Order

                order = Order.objects.filter(pk=order_id).first()
                if order and not room.orders.filter(pk=order.pk).exists():
                    room.orders.add(order)

            msg = SafetyMessage.objects.create(
                room=room,
                sender=request.user,
                message_type=msg_type,
                message=ser.validated_data['message'],
                order=order,
            )
            room.save(update_fields=['updated_at'])

            # WS fanout
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            payload = SafetyMessageSerializer(msg).data
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'safety_room_{room.id}',
                    {'type': 'safety_chat_message', 'message': payload},
                )
            return payload

        try:
            data = await sync_to_async(_send)()
        except SafetyServiceError as exc:
            return _error(exc)
        return Response(
            {'message': 'Message sent', 'status': 'success', 'data': data},
            status=status.HTTP_201_CREATED,
        )


class VoiceRecordingStartView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Safety tools'],
        summary='Start trip voice recording',
        request=VoiceRecordingStartSerializer,
    )
    async def post(self, request):
        ser = VoiceRecordingStartSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rec = await sync_to_async(start_voice_recording)(
                user=request.user,
                order_id=ser.validated_data['order_id'],
            )
        except SafetyServiceError as exc:
            return _error(exc)
        data = await sync_to_async(
            lambda: TripVoiceRecordingSerializer(rec, context={'request': request}).data
        )()
        return Response(
            {'message': 'Recording started', 'status': 'success', 'data': data},
            status=status.HTTP_201_CREATED,
        )


class VoiceRecordingStopView(AsyncAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=['Safety tools'],
        summary='Stop trip voice recording (optional audio upload)',
        request=VoiceRecordingStopSerializer,
    )
    async def post(self, request, recording_id: int):
        ser = VoiceRecordingStopSerializer(data=request.data)
        if not await sync_to_async(lambda: ser.is_valid())():
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        audio = request.FILES.get('audio') or request.FILES.get('file')
        try:
            rec = await sync_to_async(stop_voice_recording)(
                user=request.user,
                recording_id=recording_id,
                audio_file=audio,
                duration_seconds=ser.validated_data.get('duration_seconds'),
            )
        except SafetyServiceError as exc:
            return _error(exc)
        data = await sync_to_async(
            lambda: TripVoiceRecordingSerializer(rec, context={'request': request}).data
        )()
        return Response({'message': 'Recording stopped', 'status': 'success', 'data': data})


class VoiceRecordingListView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Safety tools'],
        summary='List my trip voice recordings',
        parameters=[OpenApiParameter('order_id', OpenApiTypes.INT, required=False)],
    )
    async def get(self, request):
        def _list():
            qs = TripVoiceRecording.objects.filter(user=request.user).order_by('-created_at')
            order_id = request.query_params.get('order_id')
            if order_id:
                try:
                    qs = qs.filter(order_id=int(order_id))
                except ValueError:
                    pass
            if _is_staff(request.user) and request.query_params.get('all') == '1':
                qs = TripVoiceRecording.objects.all().order_by('-created_at')
            return TripVoiceRecordingSerializer(
                qs[:100], many=True, context={'request': request}
            ).data

        data = await sync_to_async(_list)()
        return Response({'message': 'OK', 'status': 'success', 'data': data})


class VoiceRecordingDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Safety tools'], summary='Voice recording detail')
    async def get(self, request, recording_id: int):
        def _get():
            try:
                rec = TripVoiceRecording.objects.get(pk=recording_id)
            except TripVoiceRecording.DoesNotExist:
                return None, 'not_found'
            if rec.user_id != request.user.id and not _is_staff(request.user):
                return None, 'forbidden'
            return TripVoiceRecordingSerializer(rec, context={'request': request}).data, None

        data, err = await sync_to_async(_get)()
        if err == 'not_found':
            return Response(
                {'message': 'Not found', 'status': 'error', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if err == 'forbidden':
            return Response(
                {'message': 'Forbidden', 'status': 'error', 'code': 'forbidden'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({'message': 'OK', 'status': 'success', 'data': data})
