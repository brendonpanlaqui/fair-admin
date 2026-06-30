from django import forms
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin, UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe 
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import (
    FareMatrix, 
    Report, 
    Tricycle, 
    Trip, 
    UserProfile
)

# USER PROFILE ADMIN (LGU & Superadmin)
@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    """Admin interface for managing commuter profiles and ID verifications."""
    list_display = ('get_full_name', 'user_type', 'auth_provider', 'is_discount_verified', 'id_photo_preview', 'action_button')
    list_filter = ('is_discount_verified', 'user_type', 'auth_provider')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    
    # to select user type
    radio_fields = {"user_type": admin.HORIZONTAL}

    def id_photo_preview(self, obj):
        if obj.id_photo:
            return mark_safe(f'''
                <a href="{obj.id_photo.url}" target="_blank">
                    <img src="{obj.id_photo.url}" 
                         style="width: 100px; height: 64px; object-fit: cover; border-radius: 6px; border: 1px solid #E2E8F0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" 
                         alt="ID Photo"/>
                </a>
            ''')
        return mark_safe('<span style="color: #94A3B8; font-style: italic;">No ID Uploaded</span>')
    id_photo_preview.short_description = "ID Document"

    # grab real name of commuter
    def get_full_name(self, obj):
        full_name = obj.user.get_full_name()
        return full_name if full_name else obj.user.email
    get_full_name.short_description = "Commuter Name"

    # button to view profile and verify ID
    def action_button(self, obj):
        url = reverse('admin:dashboard_userprofile_change', args=[obj.pk])
        if obj.user_type == 'Pending Driver':
            return mark_safe(f'<a href="{url}" style="background-color: #F59E0B; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">Review Driver App &rarr;</a>')
        
        elif obj.user_type == 'Driver':
            return mark_safe(f'<a href="{url}" style="background-color: #3B82F6; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">Driver Active 🚕</a>')
        
        elif obj.id_photo and not obj.is_discount_verified:
            return mark_safe(f'<a href="{url}" style="background-color: #EF4444; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">Verify ID &rarr;</a>')
        elif obj.is_discount_verified:
            return mark_safe(f'<a href="{url}" style="background-color: #10B981; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">Verified ✔</a>')
        else:
            return mark_safe(f'<a href="{url}" style="background-color: #E2E8F0; color: #475569; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block;">View User</a>')
    action_button.short_description = "Action"

    # cleaned form
    fieldsets = (
        ("Commuter Account Details", {
            "fields": ('user', 'auth_provider', 'is_email_verified'),
            "classes": ["tab"],
        }),
        ("Discount Verification Center", {
            # user_type moved to this section
            "fields": ('user_type', 'is_discount_verified', 'id_photo'),
            "classes": ["tab"],
            "description": mark_safe(
                '<div class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4 mt-2">'
                '<p class="text-amber-800 font-bold mb-2 uppercase tracking-wider text-sm">⚠️ ID Verification Guidelines</p>'
                '<ol class="text-amber-700 text-xs list-decimal ml-4 space-y-1">'
                '<li>Review the uploaded ID document carefully.</li>'
                '<li><b>Confirm or Correct the User Type</b> using the buttons below to match the physical ID.</li>'
                '<li>Check the "Is verified?" box to permanently approve their account.</li>'
                '</ol>'
                '</div>'
            )
        }),
        # --- ADDED: DRIVER ASSIGNMENT TAB ---
        ("Driver Assignment (PTRO Only)", {
            "fields": ('active_tricycle',),
            "classes": ["tab"],
            "description": mark_safe(
                '<div class="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 mt-2">'
                '<p class="text-blue-800 font-bold mb-2 uppercase tracking-wider text-sm">🚕 Driver Linking</p>'
                '<p class="text-blue-700 text-xs">Select the registered tricycle this driver is currently operating. This is required for the QR Digital Handshake and GPS tracking to function correctly.</p>'
                '</div>'
            )
        }),
    )
    
    readonly_fields = ('user', 'auth_provider', 'id_photo')

    def has_module_permission(self, request):
        return not request.user.groups.filter(name='TODA').exists()

    def has_view_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()

    def has_change_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()


# TRICYCLE ADMIN (Shared Access)
@admin.register(Tricycle)
class TricycleAdmin(ModelAdmin):
    """Admin interface for managing registered and flagged tricycle units."""
    list_display = ["body_number", "driver_name", "toda_branch", "get_status_badge"]
    list_filter = ["toda_branch", "status"]
    search_fields = ["body_number", "driver_name", "plate_number"]
    list_editable = []

    def get_status_badge(self, obj):
        if obj.status == 'Unverified':
            return format_html('<span style="background-color: #EF4444; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>', '⚠️ UNVERIFIED')
        elif obj.status == 'Suspended':
            return format_html('<span style="background-color: #F59E0B; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>', 'SUSPENDED')
        else:
            return format_html('<span style="background-color: #10B981; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>', 'ACTIVE')
    get_status_badge.short_description = "Status"

    # LGU/PTRO can only change the 'status'
    def get_readonly_fields(self, request, obj=None):
        if request.user.groups.filter(name='TODA').exists():
            return ['body_number', 'driver_name', 'toda_branch', 'plate_number']
        return []

    # explicitly allow everyone to view and change
    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True
        
    def has_add_permission(self, request):
        # only LGU and Superadmin can register brand new tricycles
        return not request.user.groups.filter(name='TODA').exists()

    def has_delete_permission(self, request, obj=None):
        return not request.user.groups.filter(name='TODA').exists()


# FARE MATRIX ADMIN (LGU & Superadmin)
@admin.register(FareMatrix)
class FareMatrixAdmin(ModelAdmin):
    """Admin interface for creating and activating local fare ordinances."""
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


# TRIP ADMIN (Strict Audit Trail)
@admin.register(Trip)
class TripAdmin(ModelAdmin):
    """Read-only audit trail for all trips logged by the system."""
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
        # nobody can add fake trips manually, not even LGU
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# REPORT ADMIN (LGU & Superadmin)
@admin.register(Report)
class ReportAdmin(ModelAdmin):
    """Admin interface for the PTRO to investigate and resolve dispute tickets."""
    list_display = ('report_id', 'violation_type', 'get_body_number', 'status', 'evidence_thumbnail', 'filed_at', 'review_action')
    list_display_links = ('report_id', 'violation_type', 'get_body_number')
    list_filter = ('status', 'violation_type')
    search_fields = ('report_id', 'manual_body_number', 'trip__tricycle__body_number')
    radio_fields = {"status": admin.HORIZONTAL}
    
    fieldsets = (
        ("Commuter Complaint (Read-Only)", {
            "fields": ('report_id', 'user', 'trip', 'manual_body_number', 'violation_type', 'passenger_comments', 'evidence_preview', 'filed_at'),
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

    readonly_fields = ('report_id', 'user', 'trip', 'manual_body_number', 'violation_type', 'passenger_comments', 'evidence_preview', 'filed_at')

    def get_body_number(self, obj):
        if obj.trip and obj.trip.tricycle:
            return format_html('<b>{}</b> <span style="color: #10B981; font-size: 11px; margin-left: 4px;">(Linked)</span>', obj.trip.tricycle.body_number)
        return format_html('<b>{}</b> <span style="color: #F59E0B; font-size: 11px; margin-left: 4px;">(Manual)</span>', obj.manual_body_number)
    get_body_number.short_description = "Tricycle Body #"

    def evidence_thumbnail(self, obj):
        """Displays a small square thumbnail in the main list view."""
        if obj.evidence_photo:
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px; border: 1px solid #E2E8F0;" />', obj.evidence_photo.url)
        return mark_safe('<span style="color: #94A3B8; font-style: italic;">No Photo</span>')
    evidence_thumbnail.short_description = 'Photo'

    def evidence_preview(self, obj):
        """Displays a larger clickable preview inside the ticket details."""
        if obj.evidence_photo:
            return format_html(
                '<a href="{0}" target="_blank">'
                '<img src="{0}" style="max-width: 300px; max-height: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #E2E8F0;" />'
                '</a>'
                '<br><small style="color: #64748B; margin-top: 6px; display: block;">Click image to view full resolution</small>', 
                obj.evidence_photo.url
            )
        return mark_safe('<span style="color: #94A3B8; font-style: italic;">No evidence attached by the commuter.</span>')
    evidence_preview.short_description = 'Attached Evidence'

    def review_action(self, obj):
        # to edit this specific report
        url = reverse('admin:dashboard_report_change', args=[obj.pk])
        
        # if pending, show a bright red call-to-action button
        if obj.status == 'Pending' or obj.status == 'Investigating':
            return format_html(
                '<a href="{}" style="background-color: #EF4444; color: white; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 12px; text-decoration: none; display: inline-block; box-shadow: 0 2px 4px rgba(239,68,68,0.2);">Review Dispute &rarr;</a>',
                url
            )
        # if resolved, show a quiet gray button
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


# CUSTOM USER ADMIN 
# unregister default models
admin.site.unregister(User)
admin.site.unregister(Group)

# admin roles only, no passengers allowed here
ROLE_CHOICES = [
    ('lgu', 'LGU / PTRO Official (Web Portal Access)'),
    ('superadmin', 'IT Developer (Full System Control)'),
]

class CustomUserForm(UserChangeForm):
    """Custom form to handle role assignments without exposing raw boolean flags."""
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
    """Overrides default User admin to strictly manage LGU vs IT staff roles."""
    form = CustomUserForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    filter_horizontal = ()

    list_display = ("username", "email", "get_custom_role", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active")
    
    def get_custom_role(self, obj):
        # identify roles
        if obj.is_superuser: return "IT Developer"
        if obj.is_staff: return "LGU Official"
        return "Commuter (Mobile App)" 
    get_custom_role.short_description = "System Role"

    fieldsets = (
        ("1. System Role & Access", {
            "fields": (
                "account_role", 
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
                "is_active",
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        role = form.cleaned_data.get('account_role')
        
        # selection of role
        if role == 'superadmin':
            obj.is_staff = True
            obj.is_superuser = True
        elif role == 'lgu':
            obj.is_staff = True
            obj.is_superuser = False
            
        super().save_model(request, obj, form, change)

    # user management (only superadmins)
    def has_module_permission(self, request): return request.user.is_superuser
    def has_view_permission(self, request, obj=None): return request.user.is_superuser
    def has_change_permission(self, request, obj=None): return request.user.is_superuser


# GLOBAL AUDIT LOGS (SUPERADMIN ONLY)
@admin.register(LogEntry)
class LogEntryAdmin(ModelAdmin):
    """Read-only audit log for IT developers to track system changes."""
    # ordered for a natural reading flow (When -> Who -> What -> Action)
    list_display = ['action_time', 'user', 'get_content_type', 'get_object_repr', 'get_action']
    list_filter = ['action_flag', 'user', 'content_type']
    
    # include email just in case usernames are forgotten
    search_fields = ['user__username', 'user__email', 'object_repr', 'change_message']
    date_hierarchy = 'action_time'

    # for easy terms for non-technical admins
    def get_content_type(self, obj):
        if obj.content_type:
            return obj.content_type.name.title()
        return "Unknown"
    get_content_type.short_description = "System Module"

    def get_object_repr(self, obj):
        return obj.object_repr
    get_object_repr.short_description = "Record Affected"

    def get_action(self, obj):
        if obj.action_flag == 1: return "Created"
        if obj.action_flag == 2: return "Updated"
        if obj.action_flag == 3: return "Deleted"
        return "Unknown"
    get_action.short_description = "Action Performed"

    # STRICTLY READ-ONLY
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
    
    # only superadmins can view the logs
    def has_view_permission(self, request, obj=None): return request.user.is_superuser
    def has_module_permission(self, request): return request.user.is_superuser