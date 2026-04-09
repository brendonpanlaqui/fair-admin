from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import UserProfile, Tricycle, FareMatrix, Trip, Report

# name='TODA' means everyone can see, unless they are TODA
# ==========================================
# 1. USER PROFILE ADMIN (LGU & Superadmin)
# ==========================================
@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ["user", "user_type", "auth_provider", "is_discount_verified"]
    list_filter = ["user_type", "auth_provider", "is_discount_verified"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    list_editable = ["is_discount_verified"]

    def has_module_permission(self, request):
        return not request.user.groups.filter(name='TODA').exists()

    def has_view_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()

    def has_change_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()

# ==========================================
# 2. TRICYCLE ADMIN (Shared Access)
# ==========================================
@admin.register(Tricycle)
class TricycleAdmin(ModelAdmin):
    list_display = ["body_number", "driver_name", "toda_branch", "status"]
    list_filter = ["toda_branch", "status"]
    search_fields = ["body_number", "driver_name", "plate_number"]
    list_editable = ["status"] 

    # TODA can only change the 'status'
    def get_readonly_fields(self, request, obj=None):
        if request.user.groups.filter(name='TODA').exists():
            return ['body_number', 'driver_name', 'toda_branch', 'plate_number']
        return []

    # 🚀 FIX: explicitly allow everyone to view and change
    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True
        
    def has_add_permission(self, request):
        # Only LGU and Superadmin can register brand new tricycles
        return not request.user.groups.filter(name='TODA').exists()

    def has_delete_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()

# ==========================================
# 3. FARE MATRIX ADMIN (LGU & Superadmin)
# ==========================================
@admin.register(FareMatrix)
class FareMatrixAdmin(ModelAdmin):
    list_display = ['id', 'base_fare', 'base_distance_km', 'succeeding_km_rate', 'discount_percent', 'is_active', 'effective_date']
    list_filter = ['is_active']

    fieldsets = (
        ("Baseline Ordinance Rates", {
            "description": "Enter the legally mandated starting fare and distance for Angeles City tricycles.",
            "fields": (('base_fare', 'base_distance_km'),)
        }),
        ("Variable Rates & Discounts", {
            "description": "Configure the per-kilometer increments and mandatory sector discounts (e.g., 20% for Students/Seniors).",
            "fields": (('succeeding_km_rate', 'discount_percent'),)
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

    def has_module_permission(self, request):
        return not request.user.groups.filter(name='TODA').exists()

    def has_view_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()

    def has_change_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()
    
    def has_add_permission(self, request):
        # LGU must be able to add new matrices when new ordinances are passed!
        return not request.user.groups.filter(name='TODA').exists()

# ==========================================
# 4. TRIP ADMIN (Strict Audit Trail)
# ==========================================
@admin.register(Trip)
class TripAdmin(ModelAdmin):
    list_display = ["trip_id", "tricycle", "trip_mode", "total_distance_km", "computed_fare", "actual_fare_charged", "status", "timestamp"]
    list_filter = ["status", "trip_mode", "timestamp"]
    search_fields = ["trip_id", "tricycle__body_number", "origin_address", "destination_address"]
    date_hierarchy = "timestamp"
    
    def get_list_display_color(self, obj):
        if obj.actual_fare_charged > obj.computed_fare:
            return 'red'
        return None

    def has_module_permission(self, request):
        return not request.user.groups.filter(name='TODA').exists()

    def has_view_permission(self, request, obj=None):
        # LGU can view
        return not request.user.groups.filter(name='TODA').exists()

    def has_add_permission(self, request):
        # Nobody can add fake trips manually, not even LGU
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

# ==========================================
# 5. REPORT ADMIN (LGU & Superadmin)
# ==========================================
@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ["report_id", "violation_type", "trip", "status", "filed_at"]
    list_filter = ["status", "violation_type", "filed_at"]
    search_fields = ["report_id", "user__email", "trip__tricycle__body_number"]
    list_editable = ["status"] 
    date_hierarchy = "filed_at"

    def has_module_permission(self, request):
        return not request.user.groups.filter(name='TODA').exists()

    def has_view_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()

    def has_change_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()

# ==========================================
# 6. UNFOLD FIX FOR NATIVE USERS & GROUPS
# ==========================================
admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    filter_horizontal = ()

    # 🚀 Renaming columns for the main list view
    list_display = ("username", "email", "display_groups", "get_user_type", "is_staff")
    
    # Custom Labels for the Table Header
    def is_staff_status(self, obj): return obj.is_staff
    is_staff_status.boolean = True
    is_staff_status.short_description = 'Has Portal Access'

    def display_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    display_groups.short_description = 'Official Role (LGU/TODA)'

    def get_user_type(self, obj):
        try: return obj.userprofile.user_type
        except: return "Official"
    get_user_type.short_description = 'Account Category'

    # 🚀 BEAUTIFIED FORM LAYOUT
    fieldsets = (
        ("Account Credentials", {
            "fields": ("username", "password"),
            "description": "The login details used to access the Fair ecosystem."
        }),
        ("Official's Information", {
            "fields": ("first_name", "last_name", "email"),
            "description": "Legal name and contact details of the officer or president."
        }),
        ("Permissions & Roles", {
            "description": "Configure what this person is allowed to do within the Fair system.",
            "fields": (
                "is_active", 
                "is_staff", # We'll label this 'Portal Access' via the form
                "is_superuser", 
                "groups",
            ),
        }),
    )

    # 🚀 THE "SECRET SAUCE": Changing the labels on the fly
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "is_staff" in form.base_fields:
            form.base_fields["is_staff"].label = "Grant Web Portal Access"
            form.base_fields["is_staff"].help_text = "Check this ONLY for LGU Officials or TODA Presidents."
        if "is_superuser" in form.base_fields:
            form.base_fields["is_superuser"].label = "Developer / IT Admin Status"
            form.base_fields["is_superuser"].help_text = "Grants total control over the entire system (IT only)."
        if "is_active" in form.base_fields:
            form.base_fields["is_active"].label = "Account is Active"
        if "groups" in form.base_fields:
            form.base_fields["groups"].label = "Assigned Official Group"
        return form

    def has_module_permission(self, request):
        return request.user.is_superuser
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    fields = ('name',)
    
    def has_module_permission(self, request):
        return request.user.is_superuser
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser