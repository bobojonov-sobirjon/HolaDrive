from rest_framework import serializers
from apps.order.models import TripRating, RatingFeedbackTag, Order
from apps.accounts.models import CustomUser


class RatingFeedbackTagSerializer(serializers.ModelSerializer):
    """
    Serializer for rating feedback tags.
    """
    
    class Meta:
        model = RatingFeedbackTag
        fields = ['id', 'name', 'tag_type', 'is_active']


class TripRatingCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a trip rating.
    """
    
    order_id = serializers.IntegerField(required=True, help_text="ID of the completed order")
    rating = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=5,
        help_text="Rating from 1 to 5 stars"
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Optional comment/feedback text"
    )
    tip_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Optional tip amount for the driver"
    )
    feedback_tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="List of feedback tag IDs to associate with this rating"
    )
    
    def validate_order_id(self, value):
        """
        Validate that order exists and belongs to the user.
        """
        try:
            order = Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")
        
        # Check if order is completed
        if order.status != Order.OrderStatus.COMPLETED:
            raise serializers.ValidationError("Can only rate completed orders.")
        
        # Check if rating already exists
        if hasattr(order, 'trip_rating'):
            raise serializers.ValidationError("This order has already been rated.")
        
        return value
    
    def validate_feedback_tag_ids(self, value):
        """
        Validate that feedback tags exist and match the rating type.
        """
        if not value:
            return value
        
        # Get rating value from initial data
        rating = self.initial_data.get('rating')
        if not rating:
            return value
        
        # Determine expected tag type based on rating
        expected_tag_type = 'positive' if rating >= 4 else 'negative'
        
        # Get tags
        tags = RatingFeedbackTag.objects.filter(id__in=value, is_active=True)
        if tags.count() != len(value):
            raise serializers.ValidationError("Some feedback tags are invalid or inactive.")
        
        # Check tag types match rating
        for tag in tags:
            if tag.tag_type != expected_tag_type:
                raise serializers.ValidationError(
                    f"Tag '{tag.name}' is {tag.get_tag_type_display()} but rating is {rating} stars. "
                    f"Use {'positive' if rating >= 4 else 'negative'} tags for {rating} star rating."
                )
        
        return value


class TripRatingSerializer(serializers.ModelSerializer):
    """
    Serializer for trip rating details.
    """
    
    rider_name = serializers.CharField(source='rider.get_full_name', read_only=True)
    driver_name = serializers.CharField(source='driver.get_full_name', read_only=True)
    order_code = serializers.CharField(source='order.order_code', read_only=True)
    feedback_tags = RatingFeedbackTagSerializer(many=True, read_only=True)
    
    class Meta:
        model = TripRating
        fields = [
            'id',
            'order',
            'order_code',
            'rider',
            'rider_name',
            'driver',
            'driver_name',
            'rating',
            'comment',
            'tip_amount',
            'feedback_tags',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'rider', 'driver', 'status', 'created_at', 'updated_at']


class RatingFeedbackTagsListSerializer(serializers.Serializer):
    """
    Serializer for listing available feedback tags based on rating.
    """
    
    rating = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=5,
        help_text="Rating value (1-5) to determine which tags to show"
    )
    
    def validate_rating(self, value):
        """
        Validate rating value.
        """
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

