from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    """to extend default Django auth User model."""
    USER_TYPES = [
        ('Regular', 'Regular'),
        ('Student', 'Student'),
        ('Senior', 'Senior Citizen'),
        ('PWD', 'Person with Disability'),
        ('Pending Driver', 'Pending Driver Verification'),
        ('Driver', 'Tricycle Driver'), 
    ]
    AUTH_PROVIDERS = [
        ('Local', 'Local (Email/Password)'),
        ('Google', 'Google OAuth'),
    ]

    # links to the built-in User model
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    auth_provider = models.CharField(max_length=10, choices=AUTH_PROVIDERS, default='Local')
    user_type = models.CharField(max_length=15, choices=USER_TYPES, default='Regular') 
    
    # store ID photo for discount verification
    id_photo = models.ImageField(upload_to='id_photos/', blank=True, null=True, help_text="Photo upload of Student ID, Senior Citizen ID, PWD ID, Solo Parents ID, or Franchice/TODA ID for drivers")
    is_discount_verified = models.BooleanField(default=False, help_text="Checked by Admin for verified approval")
    
    # tracking OTP and Email verification 
    is_email_verified = models.BooleanField(default=False)
    email_otp = models.CharField(max_length=6, blank=True, null=True)

    # --- DIGITAL HANDSHAKE & FCM ---
    fcm_token = models.CharField(max_length=255, blank=True, null=True, help_text="Firebase device token for push notifications")
    active_tricycle = models.ForeignKey('Tricycle', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_drivers', help_text="The tricycle the driver is currently operating")

    # GPS coordinates. max_digits=9 and decimal_places=6 gives accuracy down to ~11 centimeters.
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Driver's last known latitude")
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Driver's last known longitude")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.user_type}"
    
    def save(self, *args, **kwargs):
        # save profile to database for latest info
        super().save(*args, **kwargs)

        # check if the user is an official approved driver and has an active tricycle assigned
        if self.user_type == 'Driver' and self.active_tricycle:
            
            real_name = self.user.get_full_name().strip()
            if not real_name:
                real_name = self.user.email

            needs_update = False

            # check if the name needs fixing
            if self.active_tricycle.driver_name != real_name:
                self.active_tricycle.driver_name = real_name
                needs_update = True
            
            # check if the status is stuck on Unverified
            if self.active_tricycle.status != 'Active':
                self.active_tricycle.status = 'Active'
                needs_update = True

            if needs_update:
                self.active_tricycle.save()


# TRICYCLE INFRASTRUCTURE
class Tricycle(models.Model):
    """
    this represents a physical tricycle unit registered in the LGU system. pwede auto-created para sa 'Unverified' if a user reports a non-registered body number.
    """
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
        ('Unverified', 'Unverified (Colorum/Pending)'), 
    ]
    
    # the LGU-assigned body number acts as the unique identifier
    body_number = models.CharField(max_length=10, primary_key=True)
    
    # an auto-created tricycle won't have this info yet (nullable).
    driver_name = models.CharField(max_length=100, blank=True, null=True, default="Unknown Driver")
    operator_name = models.CharField(max_length=100, blank=True, null=True)
    toda_branch = models.CharField(max_length=50, blank=True, null=True, default="Unknown TODA")
    plate_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"Body #{self.body_number} ({self.toda_branch})"


class FareMatrix(models.Model):
    """
    defines the official pricing rules set by the local ordinance.
    Only one matrix should be marked as 'is_active=True' at a time.
    """
    base_fare = models.DecimalField(max_digits=6, decimal_places=2, help_text="e.g., 35.00")
    base_distance_km = models.FloatField(default=1.0)
    succeeding_km_rate = models.DecimalField(max_digits=6, decimal_places=2, help_text="e.g., 15.00")
    discount_percent = models.DecimalField(max_digits=4, decimal_places=2, help_text="e.g., 0.20 for 20%")
    
    effective_date = models.DateTimeField(auto_now_add=True)
    updated_by_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tricycle Fare Ordinance"
        verbose_name_plural = "Tricycle Fare Ordinances"

    def __str__(self):
        # IMPROVED DISPLAY NAME
        status = "ACTIVE" if self.is_active else "Archived"
        date_str = self.effective_date.strftime('%b %d, %Y')
        return f"₱{self.base_fare} Base - {status} ({date_str})"

    def save(self, *args, **kwargs):
        # ensure one active matrix at a time
        if self.is_active:
            FareMatrix.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


# TRIP & TELEMETRY
class Trip(models.Model):
    """
    logs individual rides, connecting a Commuter, a Tricycle, and the Fare Matrix, used to calculate the cost at that specific point in time.
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending Approval'), 
        ('Active', 'Active Ride'),      
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    TRIP_MODES = [
        ('Direct', 'Direct'),
        ('Special', 'Special'),
    ]

    trip_id = models.CharField(max_length=50, primary_key=True)
    
    # foreign Keys connecting the trip to its entities
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
    
    # --- ADDED: Explicit link to the Driver User who approved the trip ---
    driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='driven_trips')
    
    tricycle = models.ForeignKey(Tricycle, on_delete=models.RESTRICT)
    fare_matrix = models.ForeignKey(FareMatrix, on_delete=models.RESTRICT)
    
    # trip details and routing
    trip_mode = models.CharField(max_length=10, choices=TRIP_MODES, default='Direct')
    origin_address = models.CharField(max_length=255, default="Unknown Location")
    destination_address = models.CharField(max_length=255, default="Unknown Destination")
    
    total_distance_km = models.FloatField()
    stopovers_count = models.IntegerField(default=0)
    
    # financial data
    computed_fare = models.DecimalField(max_digits=8, decimal_places=2)
    actual_fare_charged = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    discount_applied = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    # a GPS Telemetry and Meta
    polyline_hash = models.TextField(blank=True, null=True) 
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending') # Changed default to Pending
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # raw coordinates
    origin_lat = models.FloatField(null=True, blank=True)
    origin_lng = models.FloatField(null=True, blank=True)
    dest_lat = models.FloatField(null=True, blank=True)
    dest_lng = models.FloatField(null=True, blank=True)
    dest_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Trip {self.trip_id} (₱{self.actual_fare_charged})"


# REPORTING & AUDITS
class Report(models.Model):
    """
    handles dispute tickets filed by commuters against drivers for violations like overcharging, arrogance, or lacking a matrix.
    """
    VIOLATION_TYPES = [
        ('Overcharging', 'Overcharging'),
        ('Refusal', 'Refusal to Convey'),
        ('No_Matrix', 'Missing Fare Matrix'),
        ('No_Discount', 'Denied 20% Discount'),
        ('Others', 'Other Violation (See Comments)'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Investigating', 'Under Investigation'),
        ('Resolved', 'Resolved'),
        ('Dismissed', 'Dismissed'),
    ]

    report_id = models.CharField(max_length=50, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # a report can either be linked to a tracked Trip, or manually entered
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True)
    manual_body_number = models.CharField(max_length=10, blank=True, null=True, help_text="Used when trip is not linked to the app")
    
    # evidence and comments
    evidence_photo = models.ImageField(upload_to='evidence_photos/', null=True, blank=True)
    violation_type = models.CharField(max_length=20, choices=VIOLATION_TYPES)
    passenger_comments = models.TextField(blank=True, null=True, help_text="The complaint details from the commuter.")    
    
    # admin resolution tracking
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    admin_response = models.TextField(blank=True, null=True, help_text="Official PTRO resolution sent back to the commuter.")    
    
    # timestamps
    filed_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Report {self.report_id} - {self.get_violation_type_display()}"