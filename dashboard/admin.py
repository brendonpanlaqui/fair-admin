from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import UserProfile, Tricycle, FareMatrix, Trip, Report

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ["user", "user_type", "auth_provider", "is_verified"]
    list_filter = ["user_type", "auth_provider", "is_verified"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    list_editable = ["is_verified"] # Admins can click a checkbox right in the table

@admin.register(Tricycle)
class TricycleAdmin(ModelAdmin):
    list_display = ["body_number", "driver_name", "toda_branch", "status"]
    list_filter = ["toda_branch", "status"]
    search_fields = ["body_number", "driver_name", "plate_number"]
    list_editable = ["status"] # Admins can quickly suspend a driver

@admin.register(FareMatrix)
class FareMatrixAdmin(ModelAdmin):
    list_display = ['id', 'base_fare', 'base_distance_km', 'succeeding_km_rate', 'discount_percent', 'is_active', 'effective_date']
    list_filter = ['is_active']

    # 🚀 NEW: Organize the Add/Update form into beautiful, logical cards
    fieldsets = (
        ("Baseline Ordinance Rates", {
            "description": "Enter the legally mandated starting fare and distance for Angeles City tricycles.",
            "fields": (
                # Putting them in a tuple puts them side-by-side on the same row!
                ('base_fare', 'base_distance_km'), 
            )
        }),
        ("Variable Rates & Discounts", {
            "description": "Configure the per-kilometer increments and mandatory sector discounts (e.g., 20% for Students/Seniors).",
            "fields": (
                ('succeeding_km_rate', 'discount_percent'),
            )
        }),
        ("System Activation", {
            "description": "⚠️ WARNING: Saving a new matrix as 'Active' will permanently lock and deactivate the previous historical matrix.",
            "fields": ('is_active',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and not obj.is_active:
            return ['base_fare', 'base_distance_km', 'succeeding_km_rate', 'discount_percent', 'is_active']
        if obj and obj.is_active:
            return ['is_active']
        return []

@admin.register(Trip)
class TripAdmin(ModelAdmin):
    list_display = ["trip_id", "tricycle", "trip_mode", "total_distance_km", "computed_fare", "actual_fare_charged", "status", "timestamp"]
    list_filter = ["status", "trip_mode", "timestamp"]
    search_fields = ["trip_id", "tricycle__body_number", "origin_address", "destination_address"]
    date_hierarchy = "timestamp"
    
    # We color-code rows if actual fare is higher than computed fare (Overcharging detection)
    def get_list_display_color(self, obj):
        if obj.actual_fare_charged > obj.computed_fare:
            return 'red'
        return None

@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ["report_id", "violation_type", "trip", "status", "filed_at"]
    list_filter = ["status", "violation_type", "filed_at"]
    search_fields = ["report_id", "user__email", "trip__tricycle__body_number"]
    list_editable = ["status"] # Admins can change Pending -> Resolved easily
    date_hierarchy = "filed_at"