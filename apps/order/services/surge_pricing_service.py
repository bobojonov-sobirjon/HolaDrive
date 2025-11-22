from datetime import time
from django.utils import timezone
from math import radians, cos, sin, asin, sqrt
from decimal import Decimal

from ..models import SurgePricing


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on the earth (in kilometers)
    Using Haversine formula
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


class SurgePricingService:
    @staticmethod
    def get_multiplier(latitude, longitude, available_drivers_count=None):
        """
        Get multiplier based on time, location and driver count
        """
        now = timezone.now()
        current_time = now.time()
        current_day = now.weekday()
        
        # Get all active surge pricing rules
        surge_pricings = SurgePricing.objects.filter(is_active=True).order_by('-priority')
        
        multiplier = Decimal('1.00')  # Default
        
        for surge in surge_pricings:
            matches = True
            
            # Time check
            if surge.start_time and surge.end_time:
                if not (surge.start_time <= current_time <= surge.end_time):
                    matches = False
            
            # Day check
            if surge.days_of_week:
                if current_day not in surge.days_of_week:
                    matches = False
            
            # Zone check
            if surge.latitude and surge.longitude:
                distance = calculate_distance(
                    float(latitude), float(longitude),
                    float(surge.latitude), float(surge.longitude)
                )
                if distance > float(surge.radius_km):
                    matches = False
            
            # Driver count check
            if available_drivers_count is not None:
                if surge.min_available_drivers and available_drivers_count >= surge.min_available_drivers:
                    matches = False
                if surge.max_available_drivers and available_drivers_count <= surge.max_available_drivers:
                    matches = False
            
            if matches:
                multiplier = surge.multiplier
                break  # Take the first matching rule
        
        return float(multiplier)

