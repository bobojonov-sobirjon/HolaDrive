from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.views import AsyncAPIView
from apps.order.models import SavedRider
from apps.order.serializers.saved_rider import SavedRiderSerializer


class SavedRiderListCreateView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rider: Orders'],
        summary='List saved riders',
        description='Switch rider address book (Me is not stored here — it is the logged-in user).',
        responses=SavedRiderSerializer(many=True),
    )
    async def get(self, request):
        rows = await sync_to_async(list)(
            SavedRider.objects.filter(owner=request.user)
        )
        data = await sync_to_async(
            lambda: SavedRiderSerializer(rows, many=True).data
        )()
        return Response({'message': 'Saved riders', 'status': 'success', 'data': data})

    @extend_schema(
        tags=['Rider: Orders'],
        summary='Add saved rider',
        description='Add new contact (full_name, phone_number, optional email). Same phone updates the existing row.',
        request=SavedRiderSerializer,
        responses=SavedRiderSerializer,
    )
    async def post(self, request):
        serializer = SavedRiderSerializer(data=request.data, context={'request': request})
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rider = await sync_to_async(serializer.save)()
        data = await sync_to_async(lambda: SavedRiderSerializer(rider).data)()
        return Response(
            {'message': 'Saved rider added', 'status': 'success', 'data': data},
            status=status.HTTP_201_CREATED,
        )


class SavedRiderDetailView(AsyncAPIView):
    permission_classes = [IsAuthenticated]

    async def _get_owned(self, request, rider_id):
        return await SavedRider.objects.filter(id=rider_id, owner=request.user).afirst()

    @extend_schema(tags=['Rider: Orders'], summary='Saved rider detail', responses=SavedRiderSerializer)
    async def get(self, request, rider_id: int):
        rider = await self._get_owned(request, rider_id)
        if not rider:
            return Response(
                {'message': 'Saved rider not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = await sync_to_async(lambda: SavedRiderSerializer(rider).data)()
        return Response({'message': 'Saved rider', 'status': 'success', 'data': data})

    @extend_schema(
        tags=['Rider: Orders'],
        summary='Update saved rider',
        request=SavedRiderSerializer,
        responses=SavedRiderSerializer,
    )
    async def patch(self, request, rider_id: int):
        rider = await self._get_owned(request, rider_id)
        if not rider:
            return Response(
                {'message': 'Saved rider not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SavedRiderSerializer(
            rider, data=request.data, partial=True, context={'request': request}
        )
        is_valid = await sync_to_async(lambda: serializer.is_valid())()
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return Response(
                {'message': 'Validation error', 'status': 'error', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rider = await sync_to_async(serializer.save)()
        data = await sync_to_async(lambda: SavedRiderSerializer(rider).data)()
        return Response({'message': 'Saved rider updated', 'status': 'success', 'data': data})

    @extend_schema(tags=['Rider: Orders'], summary='Delete saved rider')
    async def delete(self, request, rider_id: int):
        rider = await self._get_owned(request, rider_id)
        if not rider:
            return Response(
                {'message': 'Saved rider not found', 'status': 'error'},
                status=status.HTTP_404_NOT_FOUND,
            )
        await sync_to_async(rider.delete)()
        return Response(
            {'message': 'Saved rider deleted', 'status': 'success'},
            status=status.HTTP_200_OK,
        )
