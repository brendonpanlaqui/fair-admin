import uuid
import random
import math
import os
import requests

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.files.storage import default_storage
from django.utils import timezone
from datetime import timedelta

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

# --- ADDED: Import Firebase Messaging ---
from firebase_admin import messaging

from .models import (
    FareMatrix, 
    Trip, 
    Report, 
    UserProfile, 
    Tricycle
)
from .serializers import (
    FareMatrixSerializer, 
    TripSerializer, 
    ReportSerializer, 
    ReportHistorySerializer, 
    TripHistorySerializer, 
    UserUpdateSerializer, 
    ChangePasswordSerializer
)

# ADMIN DASHBOARD & UI HELPERS
# data rendering for Unfold
def pending_reports_badge(request):
    """Returns the count of pending reports for the admin sidebar badge."""
    count = Report.objects.filter(status='Pending').count()
    return str(count) if count > 0 else None 

def unfold_dashboard_callback(request, context):
    """Populates the custom dashboard view in the Unfold admin panel."""
    today = timezone.now().date()
    
    active_matrix = FareMatrix.objects.filter(is_active=True).first()
    pending_reports = Report.objects.filter(status='Pending')
    
    context['is_super'] = request.user.is_superuser
    context['pending_reports_count'] = pending_reports.count()
    context['resolved_today_count'] = Report.objects.filter(status='Resolved', filed_at__date=today).count()
    context['trips_today_count'] = Trip.objects.filter(timestamp__date=today).count()
    context['active_matrix'] = active_matrix
    context['priority_reports'] = pending_reports.order_by('-filed_at')[:3]
    context['recent_trips'] = Trip.objects.all().order_by('-timestamp')[:5]

    return context


# AUTHENTICATION & SECURITY ENDPOINTS (JWT)
# handles login, registration, OTP verification, and password management
def get_tokens_for_user(user):
    """Helper function to generate secure tokens"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@api_view(['POST'])
@permission_classes([AllowAny]) # allows users to log in without a token
def mobile_login(request):
    """Authenticates a user and returns JWT tokens."""
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({"error": "Please provide both email and password"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        if user.check_password(password):
            if not user.profile.is_email_verified:
                return Response({
                    "error": "Account not verified. Please check your email for the OTP.",
                    "requires_otp": True, 
                    "email": email 
                }, status=status.HTTP_403_FORBIDDEN)

            # if verified, issue tokens as normal
            tokens = get_tokens_for_user(user)
            return Response({
                "status": "Success",
                "tokens": tokens,
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,  
                "last_name": user.last_name,
                "user_type": user.profile.user_type
                
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)
            
    except User.DoesNotExist:
        return Response({"error": "No account found with this email"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_register(request):
    """Registers a new user, creates a profile, and sends an OTP."""
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not email or len(password) < 8:
        return Response({"error": "Invalid email or password too short"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Email is already registered"}, status=status.HTTP_400_BAD_REQUEST)

    # secured user
    user = User.objects.create(
        username=email, 
        email=email,
        password=make_password(password),
        first_name=first_name,
        last_name=last_name
    )
    
    # generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # create the linked Profile with the OTP
    UserProfile.objects.create(
        user=user, 
        user_type='Regular',
        email_otp=otp,
        is_email_verified=False
    )

    # send the email via Brevo REST API
    try:
        subject = 'Welcome to Fair App - Verify Your Account'
        message = f"""Hello {first_name},

Welcome to the Fair App! We are excited to help you commute safely and fairly around Angeles City.

To complete your registration and secure your account, please enter the following 6-digit verification code in the app:

VERIFICATION CODE: {otp}

This code is valid for 5 minutes. If you did not create this account, please ignore this email. 

Safe travels,
The Fair App Team
"""
        brevo_api_key = os.environ.get("BREVO_API_KEY")
        url = "https://api.brevo.com/v3/smtp/email"
        
        payload = {
            "sender": {
                "name": "Fair App Support", 
                "email": "fairapp.angeles@gmail.com" 
            },
            "to": [{"email": email}],
            "subject": subject,
            "textContent": message
        }
        
        headers = {
            "accept": "application/json",
            "api-key": brevo_api_key,
            "content-type": "application/json"
        }
        
        # timeout added to prevent Gunicorn workers from hanging if Brevo is slow
        email_response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Brevo API Response: {email_response.status_code} - {email_response.text}")

    except Exception as e:
        print(f"\n--- BREVO API FAILED TO SEND ---")
        print(f"Error: {str(e)}")
        print(f"The OTP for {email} is: {otp}\n----------------------------\n")

    # always return success if the user was created in the database
    return Response({
        "status": "Account Created",
        "message": "Please check your email for the verification code."
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_otp(request):
    """Verifies the OTP sent to the user during registration."""
    email = request.data.get('email')
    otp = request.data.get('otp')

    print(f"\n--- OTP VERIFICATION ATTEMPT ---")
    print(f"Email from App: '{email}'")
    print(f"OTP from App: '{otp}'")

    try:
        user = User.objects.get(email=email)
        profile = user.profile

        print(f"OTP in Database: '{profile.email_otp}'")

        if profile.is_email_verified:
            print("Result: ALREADY VERIFIED (Issuing tokens anyway)")
            # issue the login tokens even if they double-tapped!
            tokens = get_tokens_for_user(user)
            return Response({
                "status": "Verified",
                "message": "Email is already verified.",
                "tokens": tokens,
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,  
                "last_name": user.last_name
            }, status=status.HTTP_200_OK)
            
        # strings and strips any whitespaces
        db_otp_clean = str(profile.email_otp).strip()
        app_otp_clean = str(otp).strip()

        if db_otp_clean == app_otp_clean:
            print("Result: EXACT MATCH! Logging user in.")
            
            profile.is_email_verified = True
            profile.email_otp = None
            profile.save()

            # issue the login tokens
            tokens = get_tokens_for_user(user)
            return Response({
                "status": "Verified",
                "tokens": tokens,
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,  
                "last_name": user.last_name
            }, status=status.HTTP_200_OK)
        else:
            print(f"Result: MISMATCH. '{app_otp_clean}' does not equal '{db_otp_clean}'")
            return Response({"error": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)

    except User.DoesNotExist:
        print("Result: USER NOT FOUND IN DB")
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Result: SYSTEM CRASH - {str(e)}")
        return Response({"error": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp(request):
    """Generates and sends a new OTP if the user requests one."""
    email = request.data.get('email')

    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        
        new_otp = str(random.randint(100000, 999999))
        
        # save to the exact place where verify function looks for it
        user.profile.email_otp = new_otp
        user.profile.save()

        # send email via Brevo REST API
        try:
            subject = 'Fair App - New Verification Code'
            message = f"""Hello {user.first_name},

You requested a new verification code for your Fair App account.

NEW VERIFICATION CODE: {new_otp}

This code is valid for 5 minutes.

Safe travels,
The Fair App Team
"""
            brevo_api_key = os.environ.get("BREVO_API_KEY")
            url = "https://api.brevo.com/v3/smtp/email"
            
            payload = {
                "sender": {
                    "name": "Fair App Support", 
                    "email": "fairapp.angeles@gmail.com" 
                },
                "to": [{"email": email}],
                "subject": subject,
                "textContent": message
            }
            
            headers = {
                "accept": "application/json",
                "api-key": brevo_api_key,
                "content-type": "application/json"
            }
            
            email_response = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"Brevo API Response: {email_response.status_code} - {email_response.text}")
            
        except Exception as e:
            print(f"\n--- NEW OTP EMAIL FAILED TO SEND ---")
            print(f"Error: {str(e)}")
            print(f"The New OTP for {email} is: {new_otp}\n----------------------------\n")

        return Response({"message": "New OTP sent successfully."}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response(
            {"message": "If this email is registered, a new code has been sent."}, 
            status=status.HTTP_200_OK
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """Initiates a password reset by sending an OTP to the provided email."""
    email = request.data.get('email')
    
    try:
        user = User.objects.get(email=email)
        otp = str(random.randint(100000, 999999))
        user.profile.email_otp = otp
        user.profile.save()

        try:
            subject = 'Fair App - Password Reset Request'
            message = f"""Hello,

We received a request to reset the password for the Fair App account associated with this email address.

Your password reset code is: {otp}

Please enter this code in the app to proceed with creating a new password. For your security, do not share this code with anyone, including Fair App staff or PTRO officials.

If you did not request this reset, your account is still secure, and you can safely ignore this email.

Best regards,
Fair App Security Team
"""
            brevo_api_key = os.environ.get("BREVO_API_KEY")
            url = "https://api.brevo.com/v3/smtp/email"
            
            payload = {
                "sender": {
                    "name": "Fair App Support", 
                    "email": "fairapp.angeles@gmail.com" 
                },
                "to": [{"email": email}],
                "subject": subject,
                "textContent": message
            }
            
            headers = {
                "accept": "application/json",
                "api-key": brevo_api_key,
                "content-type": "application/json"
            }
            
            email_response = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"Brevo API Response: {email_response.status_code} - {email_response.text}")
            
        except Exception as e:
            print(f"\n--- FORGOT PASSWORD EMAIL FAILED ---")
            print(f"Error: {str(e)}")
            print(f"The Reset OTP for {email} is: {otp}\n----------------------------\n")

        # hackers can't use this to guess registered emails.
        return Response({"message": "If an account exists, a code was sent."}, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({"message": "If an account exists, a code was sent."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """Verifies the reset OTP and assigns the new password."""
    email = request.data.get('email')
    otp = request.data.get('otp')
    new_password = request.data.get('newPassword')

    print(f"\n--- PASSWORD RESET ATTEMPT ---")
    print(f"Email: {email} | App OTP: {otp}")

    try:
        user = User.objects.get(email=email)
        db_otp_clean = str(user.profile.email_otp).strip()
        app_otp_clean = str(otp).strip()

        if db_otp_clean == app_otp_clean and db_otp_clean != "None":
            print("Result: EXACT MATCH! Resetting password.")
            user.set_password(new_password)
            user.save()
            
            # Clear the OTP so it can't be reused
            user.profile.email_otp = None
            user.profile.save()
            
            return Response({"status": "Success", "message": "Password reset successfully."}, status=status.HTTP_200_OK)
        else:
            print("Result: INVALID RESET CODE")
            return Response({"error": "Invalid reset code."}, status=status.HTTP_400_BAD_REQUEST)
            
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Verifies old password and sets new password for logged-in users"""
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        # check old password
        if not user.check_password(serializer.data.get("old_password")):
            return Response({"error": "Incorrect current password."}, status=status.HTTP_400_BAD_REQUEST)
        
        # set new password
        user.set_password(serializer.data.get("new_password"))
        user.save()
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# USER PROFILE & VERIFICATION
# handles retrieving profiles, updating details, and uploading IDs
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """Fetches or updates the currently authenticated user's profile."""
    user = request.user
    
    # --- HANDLE UPDATING (PATCH) ---
    if request.method == 'PATCH':
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "Success",
                "message": "Profile updated successfully",
                "first_name": user.first_name,
                "last_name": user.last_name
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # --- HANDLE FETCHING (GET) ---
    try:
        profile = user.profile

        tricycle_body_number = None
        if profile.active_tricycle:
            tricycle_body_number = profile.active_tricycle.body_number
            
        return Response({
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_type": profile.user_type,
            "is_discount_verified": profile.is_discount_verified,
            "active_tricycle_body_number": tricycle_body_number
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": "Failed to fetch profile."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser]) # expect a file, for DRF
def submit_id_verification(request):
    """Accepts a photo ID upload for discount verification."""
    user = request.user
    
    # grab data from the multipart/form-data request
    discount_type = request.data.get('discount_type') 
    id_photo = request.FILES.get('id_photo') # the physical file

    if not discount_type or not id_photo:
        return Response({"error": "Missing ID type or photo."}, status=status.HTTP_400_BAD_REQUEST)

    type_mapping = {
        'student': 'Student',
        'senior': 'Senior',
        'pwd': 'PWD'
    }
    mapped_type = type_mapping.get(discount_type, 'Regular')

    try:
        profile = user.profile

        # automatically handles the 'id_photos/' folder, unique names, and storage.
        profile.user_type = mapped_type
        profile.id_photo = id_photo 
        profile.is_discount_verified = False # ensures LGU admin must manually approve it
        profile.save()

        return Response({
            "status": "Success",
            "message": "ID submitted successfully for LGU review."
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error saving ID upload: {str(e)}")
        return Response({"error": "Failed to upload ID to server."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def apply_driver(request):
    """Processes a commuter's application to become a verified driver."""
    user = request.user
    body_number = request.data.get('body_number')
    franchise_photo = request.FILES.get('franchise_photo')
    toda_branch = request.data.get('toda_branch')

    if not body_number or not franchise_photo:
        return Response({"error": "Missing body number or Franchise/TODA ID photo."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. Find the tricycle (or create it as Unverified if it's new to the system)
        tricycle, created = Tricycle.objects.get_or_create(
            body_number=body_number,
            defaults={
                'status': 'Unverified',
                'driver_name': f"{user.first_name} {user.last_name}",
                'toda_branch': toda_branch
            }
        )

        # 2. Update the user's profile
        profile = user.profile
        profile.user_type = 'Pending Driver'
        profile.id_photo = franchise_photo
        profile.active_tricycle = tricycle
        profile.save()

        return Response({
            "status": "Success",
            "message": "Driver application submitted successfully."
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"\n--- CLOUDINARY UPLOAD ERROR --- \n{str(e)}\n-------------------------------\n")
        
        return Response({"error": f"Failed to submit application: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 4. FARE & ORDINANCE ENDPOINTS
# handles retrieving the active ordinance/fare logic

@api_view(['GET'])
def get_active_fare(request):
    """Fetches the currently active fare matrix set by the LGU."""
    try:
        # ask the database for the ONE row where is_active is True
        active_matrix = FareMatrix.objects.get(is_active=True)
        
        # translate it to JSON
        serializer = FareMatrixSerializer(active_matrix)
        
        # send it to the mobile app
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except FareMatrix.DoesNotExist:
        # if the Admin forgot to set an active matrix
        return Response(
            {"error": "No active fare matrix found in the system. Contact LGU."}, 
            status=status.HTTP_404_NOT_FOUND
        )


# TRICYCLE ENDPOINTS
# handles validation and querying of registered tricycles
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_tricycle(request, body_number):
    """Quick check for the React Native app after a ride to ensure legitimacy."""
    try:
        tricycle = Tricycle.objects.get(body_number=body_number)
        return Response({"status": tricycle.status}, status=status.HTTP_200_OK)
    except Tricycle.DoesNotExist:
        # return 404 so the app knows to throw the Unregistered warning
        return Response({"error": "Tricycle not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_fcm_token(request):
    fcm_token = request.data.get('fcm_token')
    if fcm_token:
        profile = request.user.profile
        profile.fcm_token = fcm_token
        profile.save()
        return Response({"status": "Token updated successfully"})
    return Response({"error": "No token provided"}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_fcm_token(request):
    profile = request.user.profile
    profile.fcm_token = None  # Or use "" if your model uses a CharField without null=True
    profile.save()
    return Response({"status": "Token cleared successfully"})

# (Haversine Formula) 
def calculate_distance(lat1, lon1, lat2, lon2):
    """Returns the distance between two GPS points in meters."""
    R = 6371e3 # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# COMMUTER REQUESTS RIDE 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_trip(request):
    """Processes the QR/Manual entry, checks 50m proximity, and notifies the driver."""
    user = request.user
    data = request.data
    body_number = data.get('body_number')

    if not body_number:
        return Response({"error": "Missing tricycle body number."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # find the Tricycle and active driver
        tricycle = Tricycle.objects.get(body_number=body_number)
        driver_profile = UserProfile.objects.filter(active_tricycle=tricycle, user_type='Driver').first()
        
        if not driver_profile or not driver_profile.fcm_token:
            return Response({"error": "Driver is not available or offline."}, status=status.HTTP_404_NOT_FOUND)

        # 2. The 50-Meter Proximity Lock
        commuter_lat = float(data.get('commuter_lat', 0))
        commuter_lng = float(data.get('commuter_lng', 0))
        
        # Note: Ensure your UserProfile model has current_lat and current_lng fields!
        driver_lat = getattr(driver_profile, 'current_lat', None)
        driver_lng = getattr(driver_profile, 'current_lng', None)
        
        if driver_lat and driver_lng and commuter_lat and commuter_lng:
            distance_meters = calculate_distance(commuter_lat, commuter_lng, float(driver_lat), float(driver_lng))
            if distance_meters > 50:
                return Response({
                    "error": "You must be near the tricycle to link the ride."
                }, status=status.HTTP_403_FORBIDDEN)
        # If no driver GPS is found, we allow it to pass ONLY for testing purposes. 
        # In production, you would block this if driver_lat is None.

        # 3. Create the Pending Trip
        active_matrix = FareMatrix.objects.filter(is_active=True).first()
        pending_trip_id = str(uuid.uuid4())

        new_trip = Trip.objects.create(
            trip_id=pending_trip_id,
            user=user,
            driver=driver_profile.user,
            tricycle=tricycle,
            fare_matrix=active_matrix,
            status='Pending',
            dest_lat=data.get('destination_lat'),
            dest_lng=data.get('destination_lng'),
            computed_fare=data.get('fare', 0.00),
            total_distance_km=data.get('distance', 0.0),
            actual_fare_charged=0.00
        )

        try:
            expo_push_url = 'https://exp.host/--/api/v2/push/send'
            push_payload = {
                "to": driver_profile.fcm_token,  # Expo push token stored in db
                "title": "New Ride Request! 🛺",
                "body": f"{user.first_name} is requesting a ride.",
                "sound": "default",
                "data": {
                    'type': 'TRIP_REQUEST',
                    'action': 'APPROVE_TRIP',
                    'trip_id': pending_trip_id,
                    'commuter_name': f"{user.first_name} {user.last_name}",
                }
            }
            
            response = requests.post(expo_push_url, json=push_payload)
            print(f"Expo Push Response: {response.status_code} - {response.text}")
            
        except Exception as push_err:
            print(f"Failed to send Push to Driver: {str(push_err)}")
        # ---------------------------------------------------------

        return Response({
            "status": "Success", 
            "message": "Linking request sent to the driver.",
            "trip_id": pending_trip_id
        }, status=status.HTTP_200_OK)

    except Tricycle.DoesNotExist:
        return Response({"error": "Tricycle not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": f"Server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# COMMUTER POLLS STATUS 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_trip_status(request, trip_id):
    """The commuter's app calls this every 3 seconds to see if the driver answered."""
    trip = get_object_or_404(Trip, trip_id=trip_id, user=request.user)
    return Response({"status": trip.status}, status=status.HTTP_200_OK)


# DRIVER APPROVES 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_trip(request, trip_id):
    """The driver presses 'Approve' on their popup."""
    trip = get_object_or_404(Trip, trip_id=trip_id, driver=request.user)
    
    if trip.status == 'Pending':
        trip.status = 'Active'
        trip.save()
        return Response({"status": "Success", "message": "Trip approved!"})
    
    return Response({"error": "Trip is no longer pending."}, status=status.HTTP_400_BAD_REQUEST)


# DRIVER DECLINES 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_trip(request, trip_id):
    """The driver presses 'Decline' on their popup."""
    trip = get_object_or_404(Trip, trip_id=trip_id, driver=request.user)
    
    if trip.status == 'Pending':
        trip.status = 'Declined'
        trip.save()
        return Response({"status": "Success", "message": "Trip declined."})
        
    return Response({"error": "Trip is no longer pending."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_driver_trip(request):
    """Checks if the driver currently has an active passenger."""
    if request.user.profile.user_type != 'Driver':
        return Response({"error": "Not a driver"}, status=status.HTTP_403_FORBIDDEN)
        
    # Find any trip where this user is the driver and it is currently 'Active'
    active_trip = Trip.objects.filter(driver=request.user, status='Active').first()
    
    if active_trip:
        return Response({
            "has_active_trip": True,
            "trip_id": active_trip.trip_id,
            "fare": active_trip.computed_fare,
            "commuter_name": active_trip.user.first_name if active_trip.user else "Passenger"
        }, status=status.HTTP_200_OK)
        
    return Response({"has_active_trip": False}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_trip(request, trip_id):
    """The driver presses 'Drop Off' to finalize the ride."""
    trip = get_object_or_404(Trip, trip_id=trip_id, driver=request.user)
    
    if trip.status == 'Active':
        trip.status = 'Completed'
        # Finalize the transaction
        trip.actual_fare_charged = trip.computed_fare 
        trip.save()
        
        return Response({"status": "Success", "message": "Trip successfully completed."})
        
    return Response({"error": "Trip is not active or already completed."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_driver_location(request):
    """Periodically called by the driver app to keep their active GPS coordinates fresh."""
    profile = request.user.profile
    if profile.user_type != 'Driver':
        return Response({"error": "Only drivers can update transit locations."}, status=403)
        
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    
    if lat and lng:
        profile.current_lat = lat
        profile.current_lng = lng
        profile.save()
        return Response({"status": "Location updated"})
        
    return Response({"error": "Invalid coordinates"}, status=400)

# TRIP & REPORT ENDPOINTS
# handles user commutes, saving GPS logs, and filing dispute reports
@api_view(['POST'])
def submit_trip(request):
    """Logs the final GPS distance and fare to the LGU database. 
    Updates the existing handshake trip, or creates a new one for offline rides."""
    
    body_number = request.data.get('tricycle')
    trip_id = request.data.get('trip_id')

    # 1. Silently auto-create 'Unverified' tricycles if they don't exist
    if body_number:
        Tricycle.objects.get_or_create(
            body_number=body_number,
            defaults={
                'status': 'Unverified',
                'driver_name': 'Unknown (Flagged via App)',
                'toda_branch': 'Unknown'
            }
        )

    # 2. Check if this Trip ID already exists in the database (from the Handshake)
    existing_trip = None
    if trip_id:
        existing_trip = Trip.objects.filter(trip_id=trip_id).first()

    # 3. If it exists, UPDATE it. If not, CREATE it.
    if existing_trip:
        # Passing 'instance' and 'partial=True' tells DRF to perform an UPDATE (PATCH)
        serializer = TripSerializer(existing_trip, data=request.data, partial=True)
        success_status = status.HTTP_200_OK
    else:
        # Creating a brand new trip (Used for Offline Mode saves)
        serializer = TripSerializer(data=request.data)
        success_status = status.HTTP_201_CREATED
    
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"status": "Success", "message": "Trip recorded securely.", "trip_id": serializer.data['trip_id']}, 
            status=success_status
        )
        
    # If the data is invalid, print the errors to the console so you can debug easily
    print("Serializer Errors:", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_trip_history(request):
    """Fetches the ride history for the currently logged-in user"""
    try:
        # get all trips belonging to the logged-in user, newest first
        trips = Trip.objects.filter(user=request.user).order_by('-timestamp')
        
        # serialize the data into the format React Native needs
        serializer = TripHistorySerializer(trips, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error fetching history: {str(e)}")
        return Response(
            {"error": "Failed to fetch trip history."}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser]) # parsed photo
def submit_report(request):
    """Logs an overcharging or arrogant driver complaint"""
    user = request.user
    trip_id = request.data.get('trip')
    manual_body_number = request.data.get('manual_body_number')

    # SPAM PREVENTION & RATE LIMITING
    if trip_id:
        if Report.objects.filter(user=user, trip_id=trip_id).exists():
            return Response(
                {"error": "You have already filed a report for this specific trip."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    elif manual_body_number:
        time_limit = timezone.now() - timedelta(hours=24)
        if Report.objects.filter(user=user, manual_body_number=manual_body_number, filed_at__gte=time_limit).exists():
            return Response(
                {"error": "You recently reported this driver. Please wait 24 hours before filing another manual report."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    # force the authenticated user ID into the data to prevent spoofing
    data = request.data.copy()
    data['user'] = user.id

    serializer = ReportSerializer(data=data)
    
    if serializer.is_valid():
        report = serializer.save()
        
        # CROWDSOURCE FLAGGING LOGIC
        if manual_body_number:
            unique_reporters = Report.objects.filter(
                manual_body_number=manual_body_number
            ).values('user').distinct().count()
            
            # if 3 or more different commuters report the same unverified driver, automatically escalate/flag the tricycle
            if unique_reporters >= 3:
                tricycle, created = Tricycle.objects.get_or_create(
                    body_number=manual_body_number,
                    defaults={
                        'status': 'Unverified',
                        'driver_name': 'Unknown (Flagged via App)',
                        'toda_branch': 'Unknown'
                    }
                )
                
                if tricycle.status != 'Suspended':
                    tricycle.driver_name = '⚠️ URGENT REVIEW (3+ Reports)'
                    tricycle.save()

        # send confirmation email to the user via Brevo
        try:
            subject = f"Dispute Report Received - Ticket #{report.report_id}"
            message = f"""Hello {user.first_name},

This email confirms that your digital report regarding Tricycle Body #{report.trip.tricycle.body_number if report.trip else 'N/A'} has been received.

TICKET ID: {report.report_id}
VIOLATION: {report.violation_type}
DATE FILED: {report.filed_at.strftime('%B %d, %Y %I:%M %p')}

Your report has been securely transmitted to the LGU Admin Dashboard. The Public Transportation Regulatory Office (PTRO) will investigate this dispute using the GPS map-trace data provided by your app.

You can track the live status of this ticket in the 'History' tab of your Fair App.

Thank you for helping us maintain fair and safe commutes in Angeles City.

Regards,
Fair App Monitoring System
"""
            brevo_api_key = os.environ.get("BREVO_API_KEY")
            url = "https://api.brevo.com/v3/smtp/email"
            
            payload = {
                "sender": {
                    "name": "Fair App Support", 
                    "email": "fairapp.angeles@gmail.com" 
                },
                "to": [{"email": user.email}],
                "subject": subject,
                "textContent": message
            }
            
            headers = {
                "accept": "application/json",
                "api-key": brevo_api_key,
                "content-type": "application/json"
            }
            
            email_response = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"Brevo API Response: {email_response.status_code} - {email_response.text}")
            
        except Exception as e:
            print(f"\n--- REPORT SUBMIT BREVO API FAILED ---")
            print(f"Error: {str(e)}")
            pass

        return Response(
            {"status": "Success", "message": "Violation report filed. TMO will review."}, 
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_report_history(request):
    """Fetches all filed complaints for the currently logged-in user"""
    try:
        reports = Report.objects.filter(user=request.user).order_by('-filed_at')
        serializer = ReportHistorySerializer(reports, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error fetching reports: {str(e)}")
        return Response(
            {"error": "Failed to fetch reports."}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )