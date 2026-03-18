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
            'report_id', 'trip', 'user', 'violation_type', 
            'passenger_comments', 'evidence_photo_url',
            'status', 'admin_remarks', 'filed_at', 'resolved_at'
        ]
        read_only_fields = ['filed_at', 'resolved_at']