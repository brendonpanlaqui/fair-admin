from rest_framework import serializers
from .models import FareMatrix, Trip, Report

class FareMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = FareMatrix
        # Removed 'trip_mode' from the end of this list:
        fields = ['id', 'base_fare', 'base_distance_km', 'succeeding_km_rate', 'discount_percent', 'effective_date']


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        # We explicitly list every field that the React Native app is allowed to send or receive
        fields = [
            'trip_id', 'user', 'tricycle', 'fare_matrix', 
            'trip_mode', 'origin_address', 'destination_address', 
            'total_distance_km', 'computed_fare', 'actual_fare_charged',
            'discount_applied', 'polyline_hash', 'status', 'timestamp'
        ]
        read_only_fields = ['timestamp']

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'report_id', 'trip', 'user', 'manual_body_number', 'violation_type', 
            'passenger_comments', 'evidence_photo_url',
            'status', 'admin_remarks', 'filed_at', 'resolved_at'
        ]
        read_only_fields = ['filed_at', 'resolved_at']


class TripHistorySerializer(serializers.ModelSerializer):
    # 1. Pull the body number from the connected Tricycle ForeignKey
    body_number = serializers.CharField(source='tricycle.body_number', read_only=True)
    
    # 2. Map the address fields to what React Native expects
    origin_name = serializers.CharField(source='origin_address', read_only=True)
    destination_name = serializers.CharField(source='destination_address', read_only=True)
    
    # 🚀 ADD THIS LINE: Tell Django to map the fare_matrix ID to 'matrix_id'
    matrix_id = serializers.IntegerField(source='fare_matrix_id', read_only=True)
    
    # 3. Create the coordinate objects
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
        # NOTE: This assumes you added origin_lat/origin_lng to your Trip model!
        if hasattr(obj, 'origin_lat') and obj.origin_lat and obj.origin_lng:
            return {'latitude': obj.origin_lat, 'longitude': obj.origin_lng}
        return {'latitude': 15.1430, 'longitude': 120.5843} # Fallback to Angeles City Center

    def get_dest_coords(self, obj):
        if hasattr(obj, 'dest_lat') and obj.dest_lat and obj.dest_lng:
            return {'latitude': obj.dest_lat, 'longitude': obj.dest_lng}
        return {'latitude': 15.1384, 'longitude': 120.5898}


class ReportHistorySerializer(serializers.ModelSerializer):
    body_number = serializers.SerializerMethodField()
    admin_response = serializers.CharField(source='admin_remarks', read_only=True)

    class Meta:
        model = Report
        fields = [
            'report_id', 'trip', 'body_number', 'violation_type', 
            'passenger_comments', 'status', 'admin_response', 'filed_at'
        ]

    def get_body_number(self, obj):
        # 1. If it's a verified app trip, get it from the Tricycle table
        if obj.trip and hasattr(obj.trip, 'tricycle'):
            return obj.trip.tricycle.body_number
        
        # 2. 🚀 If it's a manual report, return what the user typed in
        if obj.manual_body_number:
            return obj.manual_body_number
            
        return "Unknown"