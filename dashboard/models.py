from django.db import models
from django.contrib.auth.models import User

# ==========================================
# EXTENDED USER PROFILE
# ==========================================
class UserProfile(models.Model):
    USER_TYPES = [
        ('Regular', 'Regular'),
        ('Student', 'Student'),
        ('Senior', 'Senior Citizen'),
        ('PWD', 'Person with Disability'),
    ]
    AUTH_PROVIDERS = [
        ('Local', 'Local (Email/Password)'),
        ('Google', 'Google OAuth'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    auth_provider = models.CharField(max_length=10, choices=AUTH_PROVIDERS, default='Local')
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='Regular')
    id_photo_url = models.URLField(blank=True, null=True, help_text="Link to uploaded CCA ID or PWD ID")
    is_discount_verified = models.BooleanField(default=False, help_text="Checked by Admin to approve discount")
    is_email_verified = models.BooleanField(default=False)
    email_otp = models.CharField(max_length=6, blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.user_type}"

# ==========================================
# TRICYCLE INFRASTRUCTURE
# ==========================================
class Tricycle(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
    ]
    
    body_number = models.CharField(max_length=10, primary_key=True)
    driver_name = models.CharField(max_length=100)
    operator_name = models.CharField(max_length=100, blank=True, null=True)
    toda_branch = models.CharField(max_length=50)
    plate_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"Body #{self.body_number} ({self.toda_branch})"

class FareMatrix(models.Model):
    base_fare = models.DecimalField(max_digits=6, decimal_places=2, help_text="e.g., 35.00")
    base_distance_km = models.FloatField(default=1.0)
    succeeding_km_rate = models.DecimalField(max_digits=6, decimal_places=2, help_text="e.g., 15.00")
    discount_percent = models.DecimalField(max_digits=4, decimal_places=2, help_text="e.g., 0.20 for 20%")
    effective_date = models.DateTimeField(auto_now_add=True)
    updated_by_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    # 🚀 THIS IS THE MAGIC AUTOMATION:  
    def save(self, *args, **kwargs):
        if self.is_active:
            # If the admin says THIS one is active, tell the database to instantly 
            # find every other matrix and turn them OFF before saving.
            FareMatrix.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
# ==========================================
# TRIP & TELEMETRY
# ==========================================
class Trip(models.Model):
    STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    TRIP_MODES = [
        ('Direct', 'Direct'),
        ('Special', 'Special'),
    ]

    trip_id = models.CharField(max_length=50, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
    tricycle = models.ForeignKey(Tricycle, on_delete=models.RESTRICT)
    fare_matrix = models.ForeignKey(FareMatrix, on_delete=models.RESTRICT)
    
    trip_mode = models.CharField(max_length=10, choices=TRIP_MODES, default='Direct')
    origin_address = models.CharField(max_length=255, default="Unknown Location")
    destination_address = models.CharField(max_length=255, default="Unknown Destination")
    
    total_distance_km = models.FloatField()
    stopovers_count = models.IntegerField(default=0)
    
    computed_fare = models.DecimalField(max_digits=8, decimal_places=2)
    actual_fare_charged = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    discount_applied = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    polyline_hash = models.TextField(blank=True, null=True) 
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Completed')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip {self.trip_id} (₱{self.actual_fare_charged})"

# ==========================================
# REPORTING & AUDITS
# ==========================================
class Report(models.Model):
    VIOLATION_TYPES = [
        ('Overcharging', 'Overcharging'),
        ('Refusal', 'Refusal to Convey'),
        ('Detour', 'Unnecessary Detour'),
        ('Arrogance', 'Arrogant Driver'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Investigating', 'Under Investigation'),
        ('Resolved', 'Resolved'),
        ('Dismissed', 'Dismissed'),
    ]

    report_id = models.CharField(max_length=50, primary_key=True)
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    violation_type = models.CharField(max_length=20, choices=VIOLATION_TYPES)
    passenger_comments = models.TextField()
    evidence_photo_url = models.URLField(blank=True, null=True)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    admin_remarks = models.TextField(blank=True, null=True)
    
    filed_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Report {self.report_id} - {self.get_violation_type_display()}"