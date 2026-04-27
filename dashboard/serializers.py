import re
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import FareMatrix, Report, Trip

# AUTHENTICATION & USER MANAGEMENT
class UserUpdateSerializer(serializers.ModelSerializer):
    """for updating first and last name from the user profile."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

class ChangePasswordSerializer(serializers.Serializer):
    """for validating password change requests from the app."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_new_password(self, value):
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&.])[A-Za-z\d@$!%*?&.]{8,}$', value):
            raise serializers.ValidationError("Password must contain uppercase, number, and symbol.")
        return value
    

# ORDINANCE & FARES
class FareMatrixSerializer(serializers.ModelSerializer):
    """sends the active LGU ordinance and pricing to the mobile app."""
    class Meta:
        model = FareMatrix
        fields = ['id', 'base_fare', 'base_distance_km', 'succeeding_km_rate', 'discount_percent', 'effective_date']


# COMMUTE & TRIP LOGS
class TripSerializer(serializers.ModelSerializer):
    """to handle submission of trips from the mobile app."""
    class Meta:
        model = Trip
        # allowed to send for security
        fields = [
            'trip_id', 'user', 'tricycle', 'fare_matrix', 
            'trip_mode', 'origin_address', 'destination_address', 
            'total_distance_km', 'computed_fare', 'actual_fare_charged',
            'discount_applied', 'polyline_hash', 'status', 'timestamp'
        ]
        read_only_fields = ['timestamp']

class TripHistorySerializer(serializers.ModelSerializer):
    """Read-only serializer specifically formatted for rendering the app's History tab."""
    # body number from foreign key relationship with Tricycle model
    body_number = serializers.CharField(source='tricycle.body_number', read_only=True)
    
    # map the address fields to what the app expects for display
    origin_name = serializers.CharField(source='origin_address', read_only=True)
    destination_name = serializers.CharField(source='destination_address', read_only=True)
    
    # map fare_matrix to matrix_id for easier handling on the app side
    matrix_id = serializers.IntegerField(source='fare_matrix_id', read_only=True)
    
    # coordinates
    origin_coords = serializers.SerializerMethodField()
    dest_coords = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'trip_id', 'body_number', 'matrix_id', 'trip_mode',
            'total_distance_km', 'computed_fare', 'discount_applied',
            'status', 'timestamp', 'origin_name', 'destination_name',
            'origin_coords', 'dest_coords', 'polyline_hash'
        ]

    def get_origin_coords(self, obj):
        if hasattr(obj, 'origin_lat') and obj.origin_lat and obj.origin_lng:
            return {'latitude': obj.origin_lat, 'longitude': obj.origin_lng}
        return {'latitude': 15.1430, 'longitude': 120.5843} # center of angeles city 

    def get_dest_coords(self, obj):
        if hasattr(obj, 'dest_lat') and obj.dest_lat and obj.dest_lng:
            return {'latitude': obj.dest_lat, 'longitude': obj.dest_lng}
        return {'latitude': 15.1384, 'longitude': 120.5898}


# AUDITS & DISPUTE REPORTS
class ReportSerializer(serializers.ModelSerializer):
    """handles the creation of new dispute tickets by the commuter."""
    class Meta:
        model = Report
        fields = [
            'report_id', 'trip', 'user', 'manual_body_number', 'violation_type', 
            'passenger_comments', 'evidence_photo_url',
            'status', 'admin_response', 'filed_at', 'resolved_at'
        ]
        read_only_fields = ['filed_at', 'resolved_at']

class ReportHistorySerializer(serializers.ModelSerializer):
    """for displaying user complaints in their app history."""
    body_number = serializers.SerializerMethodField()
    admin_response = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = [
            'report_id', 
            'trip', 
            'body_number', 
            'violation_type', 
            'passenger_comments', 
            'status', 
            'admin_response', 
            'filed_at'
        ]

    def get_body_number(self, obj):
        # if it's a verified app trip, get it from the Tricycle table
        if obj.trip and hasattr(obj.trip, 'tricycle'):
            return obj.trip.tricycle.body_number
        
        # 2. if it's a manual report, return what the user typed in
        if obj.manual_body_number:
            return obj.manual_body_number
            
        return "Unknown"