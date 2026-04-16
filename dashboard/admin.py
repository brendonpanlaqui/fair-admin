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
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe  # 🚀 Added this import for the UI previews

# ==========================================
# 1. USER PROFILE ADMIN (LGU & Superadmin)
# ==========================================
@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('get_full_name', 'user_type', 'auth_provider', 'is_discount_verified', 'id_photo_preview', 'action_button')
    list_filter = ('is_discount_verified', 'user_type', 'auth_provider')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    
    # 🚀 THE UPGRADE: Make user_type a quick-select radio button
    radio_fields = {"user_type": admin.HORIZONTAL}

    # 1. Custom Image Preview (Forced ID Card Aspect Ratio)
    def id_photo_preview(self, obj):
        if obj.id_photo_url:
            return mark_safe(f'''
                <a href="{obj.id_photo_url}" target="_blank">
                    <img src="{obj.id_photo_url}" 
                         style="width: 100px; height: 64px; object-fit: cover; border-radius: 6px; border: 1px solid #E2E8F0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" 
                         alt="ID Photo"/>
                </a>
            ''')
        return mark_safe('<span style="color: #94A3B8; font-style: italic;">No ID Uploaded</span>')
    id_photo_preview.short_description = "ID Document"

    # 2. Get the commuter's real name or email
    def get_full_name(self, obj):
        full_name = obj.user.get_full_name()
        return full_name if full_name else obj.user.email
    get_full_name.short_description = "Commuter Name"

    # 3. The UX Action Button
    def action_button(self, obj):
        url = reverse('admin:dashboard_userprofile_change', args=[obj.pk])
        
        if obj.id_photo_url and not obj.is_discount_verified:
            return mark_safe(f'<a href="{url}" style="background-color: #EF4444; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">Verify ID &rarr;</a>')
        elif obj.is_discount_verified:
            return mark_safe(f'<a href="{url}" style="background-color: #10B981; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">Verified ✔</a>')
        else:
            return mark_safe(f'<a href="{url}" style="background-color: #E2E8F0; color: #475569; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">View User</a>')
    action_button.short_description = "Action"

    # 4. Make the form look clean when they click into it
    fieldsets = (
        ("Commuter Account Details", {
            # 🚀 Moved user_type out of this section
            "fields": ('user', 'auth_provider', 'is_email_verified'),
            "classes": ["tab"],
        }),
        ("Discount Verification Center", {
            # 🚀 Moved user_type INTO this section, right above the verification checkbox
            "fields": ('user_type', 'is_discount_verified', 'id_photo_url'),
            "classes": ["tab"],
            "description": mark_safe(
                '<div class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4 mt-2">'
                '<p class="text-amber-800 font-bold mb-2 uppercase tracking-wider text-sm">⚠️ ID Verification Guidelines</p>'
                '<ol class="text-amber-700 text-xs list-decimal ml-4 space-y-1">'
                '<li>Review the uploaded ID document carefully.</li>'
                '<li><b>Confirm or Correct the User Type</b> using the buttons below to match the physical ID.</li>'
                '<li>Check the "Is discount verified" box to permanently activate their 20% fare discount.</li>'
                '</ol>'
                '</div>'
            )
        }),
    )
    readonly_fields = ('user', 'auth_provider', 'id_photo_url')

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
    # 1. Add 'review_action' to the very end of your list_display
    list_display = ('report_id', 'violation_type', 'get_body_number', 'status', 'filed_at', 'review_action')
    
    # 2. Make multiple columns clickable so they don't have to guess
    list_display_links = ('report_id', 'violation_type', 'get_body_number')
    
    list_filter = ('status', 'violation_type')
    search_fields = ('report_id', 'manual_body_number', 'trip__tricycle__body_number')
    radio_fields = {"status": admin.HORIZONTAL}
    fieldsets = (
        ("Commuter Complaint (Read-Only)", {
            "fields": ('report_id', 'user', 'trip', 'manual_body_number', 'violation_type', 'passenger_comments', 'filed_at'),
            "classes": ["tab"],
        }),
        ("PTRO Action Center", {
            "fields": ('status', 'admin_response'),
            "classes": ["tab"],
            "description": mark_safe(
                '<div class="text-center bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6 mt-2 dark:bg-blue-900/20 dark:border-blue-800">'
                '<p class="text-blue-700 font-black text-sm mb-1 uppercase tracking-wider dark:text-blue-400">⚠️ Official Resolution Portal</p>'
                '<p class="text-slate-600 text-xs font-medium dark:text-slate-400">Select the new status below and type your response. This will be sent directly to the commuter\'s mobile application.</p>'
                '</div>'
            )
        }),
    )

    readonly_fields = ('report_id', 'user', 'trip', 'manual_body_number', 'violation_type', 'passenger_comments', 'filed_at')

    def get_body_number(self, obj):
        if obj.trip and obj.trip.tricycle:
            return f"Trip: {obj.trip.tricycle.body_number}"
        return f"Manual: {obj.manual_body_number}"
    get_body_number.short_description = "Tricycle Body #"

    # 3. THIS IS THE MAGIC UX BUTTON
    def review_action(self, obj):
        # Generate the correct URL to edit this specific report
        url = reverse('admin:dashboard_report_change', args=[obj.pk])
        
        # If it is pending, show a bright red call-to-action button
        if obj.status == 'Pending' or obj.status == 'Investigating':
            return format_html(
                '<a href="{}" style="background-color: #EF4444; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block; box-shadow: 0 2px 4px rgba(239,68,68,0.2);">Review Dispute &rarr;</a>',
                url
            )
        # If it is resolved, show a quiet gray button
        else:
            return format_html(
                '<a href="{}" style="background-color: #E2E8F0; color: #475569; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">View Details</a>',
                url
            )
    review_action.short_description = "Action"

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
        return "Commuter (Mobile App)" 
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