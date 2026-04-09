from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from .models import UserProfile, Tricycle, FareMatrix, Trip, Report
from django import forms
from django.contrib.admin.models import LogEntry

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
# 6. CUSTOM USER ADMIN (2-TIER STAFF MVP)
# ==========================================
admin.site.unregister(User)
admin.site.unregister(Group)

# 🚀 1. Strictly Staff Roles Only
ROLE_CHOICES = [
    ('lgu', 'LGU / PTRO Official (Web Portal Access)'),
    ('superadmin', 'IT Developer (Full System Control)'),
]

class CustomUserForm(UserChangeForm):
    account_role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect,
        help_text="Select the exact access level for this official."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if self.instance.is_superuser:
                self.fields['account_role'].initial = 'superadmin'
            elif self.instance.is_staff:
                self.fields['account_role'].initial = 'lgu'

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = CustomUserForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    filter_horizontal = ()

    list_display = ("username", "email", "get_custom_role", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active")
    
    def get_custom_role(self, obj):
        # 🚀 We still keep the passenger text here so if IT looks at the 
        # main list, they can easily identify mobile users vs officials.
        if obj.is_superuser: return "IT Developer"
        if obj.is_staff: return "LGU Official"
    get_custom_role.short_description = "System Role"

    fieldsets = (
        ("1. System Role & Access", {
            "fields": (
                "account_role", # 🚀 Moved to the very top!
            ),
        }),
        ("2. Account Credentials", {
            "description": "The login details used to access the Fair web portal.",
            "fields": ("username", "password")
        }),
        ("3. Official's Information", {
            "description": "Legal name and contact details of the officer.",
            "fields": ("first_name", "last_name", "email")
        }),
        ("4. Account Status", {
            "fields": (
                "is_active", # 🚀 Tucked safely at the bottom
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        role = form.cleaned_data.get('account_role')
        
        # 🚀 Enforce the exact boolean flags based on the single radio selection
        if role == 'superadmin':
            obj.is_staff = True
            obj.is_superuser = True
        elif role == 'lgu':
            obj.is_staff = True
            obj.is_superuser = False
            
        super().save_model(request, obj, form, change)

    # Only IT can see the user management screen
    def has_module_permission(self, request): return request.user.is_superuser
    def has_view_permission(self, request, obj=None): return request.user.is_superuser
    def has_change_permission(self, request, obj=None): return request.user.is_superuser

# ==========================================
# 7. GLOBAL AUDIT LOGS (SUPERADMIN ONLY)
# ==========================================
@admin.register(LogEntry)
class LogEntryAdmin(ModelAdmin):
    # 1. Reordered for a natural reading flow (When -> Who -> What -> Action)
    list_display = ['action_time', 'user', 'get_content_type', 'get_object_repr', 'get_action']
    list_filter = ['action_flag', 'user', 'content_type']
    
    # Expanded search to include email just in case usernames are forgotten
    search_fields = ['user__username', 'user__email', 'object_repr', 'change_message']
    date_hierarchy = 'action_time'

    # 2. Translating Django jargon into clear IT terms
    def get_content_type(self, obj):
        if obj.content_type:
            return obj.content_type.name.title()
        return "Unknown"
    get_content_type.short_description = "System Module"

    def get_object_repr(self, obj):
        return obj.object_repr
    get_object_repr.short_description = "Record Affected"

    # 3. Professional, emoji-free action labels
    def get_action(self, obj):
        if obj.action_flag == 1: return "Created"
        if obj.action_flag == 2: return "Updated"
        if obj.action_flag == 3: return "Deleted"
        return "Unknown"
    get_action.short_description = "Action Performed"

    # 4. SECURITY: STRICTLY READ-ONLY
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
    
    # 5. Only IT Developer can view the logs
    def has_view_permission(self, request, obj=None): return request.user.is_superuser
    def has_module_permission(self, request): return request.user.is_superuser