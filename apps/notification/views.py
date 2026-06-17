from __future__ import annotations

from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.views import AsyncAPIView
from apps.notification.models import Notification
from apps.notification.serializers import NotificationSerializer


class NotificationListView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Notifications'],
        summary='List my notifications',
        description='Returns notifications for authenticated user. Supports filters and pagination.',
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description='unread|read'),
            OpenApiParameter('type', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description='chat_message|order_update|system|promotion|other'),
            OpenApiParameter('page', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('page_size', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        ],
    )
    async def get(self, request):
        status_filter = (request.query_params.get('status') or '').strip().lower()
        type_filter = (request.query_params.get('type') or '').strip().lower()
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size

        def _qs():
            qs = Notification.objects.filter(user=request.user).order_by('-created_at')
            if status_filter in ('unread', 'read'):
                qs = qs.filter(status=status_filter)
            if type_filter:
                qs = qs.filter(notification_type=type_filter)
            return qs

        qs = _qs()
        total = await sync_to_async(qs.count)()
        rows = await sync_to_async(list)(qs[start:end])
        ser = NotificationSerializer(rows, many=True, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response(
            {
                'message': 'OK',
                'status': 'success',
                'data': data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total,
                    'total_pages': (total + page_size - 1) // page_size,
                },
            },
            status=status.HTTP_200_OK,
        )


class NotificationMarkReadView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Notifications'],
        summary='Mark notification as read',
    )
    async def post(self, request, notification_id: int):
        try:
            n = await Notification.objects.aget(pk=notification_id, user=request.user)
        except Notification.DoesNotExist:
            return Response({'message': 'Not found', 'status': 'error'}, status=status.HTTP_404_NOT_FOUND)
        await sync_to_async(n.mark_as_read)()
        ser = NotificationSerializer(n, context={'request': request})
        data = await sync_to_async(lambda: ser.data)()
        return Response({'message': 'OK', 'status': 'success', 'data': data}, status=status.HTTP_200_OK)
