from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
import random
from django.core.mail import send_mail
from django.conf import settings

# Import all your models and serializers
from .models import FareMatrix, Trip, Report, UserProfile
from .serializers import FareMatrixSerializer, TripSerializer, ReportSerializer

# ==========================================
# 1. FARE & ORDINANCE ENDPOINTS
# ==========================================
@api_view(['GET'])
def get_active_fare(request):
    try:
        # Ask the database for the ONE row where is_active is True
        active_matrix = FareMatrix.objects.get(is_active=True)
        
        # Translate it to JSON
        serializer = FareMatrixSerializer(active_matrix)
        
        # Send it to the mobile app
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except FareMatrix.DoesNotExist:
        # Safety net: If the Admin forgot to set an active matrix
        return Response(
            {"error": "No active fare matrix found in the system. Contact LGU."}, 
            status=status.HTTP_404_NOT_FOUND
        )

# ==========================================
# 2. AUTHENTICATION ENDPOINTS (JWT)
# ==========================================
def get_tokens_for_user(user):
    """Helper function to generate secure tokens"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@api_view(['POST'])
@permission_classes([AllowAny]) # Allows users to log in without a token
def mobile_login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({"error": "Please provide both email and password"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        if user.check_password(password):
            tokens = get_tokens_for_user(user)
            return Response({
                "status": "Success",
                "tokens": tokens,
                "user_id": user.id,
                "email": user.email,
                "first_name": user.first_name,  
                "last_name": user.last_name
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)
            
    except User.DoesNotExist:
        return Response({"error": "No account found with this email"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_register(request):
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not email or len(password) < 8:
        return Response({"error": "Invalid email or password too short"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Email is already registered"}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Create the secure Django User
    user = User.objects.create(
        username=email, 
        email=email,
        password=make_password(password),
        first_name=first_name,
        last_name=last_name
    )
    
    # 2. Generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # 3. Create the linked Profile with the OTP
    UserProfile.objects.create(
        user=user, 
        user_type='Regular',
        email_otp=otp,
        is_email_verified=False
    )

    # 4. "Send" the email (Will print to terminal for now)
    try:
        send_mail(
            subject='Verify your Fair App Account',
            message=f'Hello {first_name},\n\nYour verification code is: {otp}\n\nPlease enter this in the app to verify your account.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        print(f"SUCCESS: Email sent to {email}")
    except Exception as e:
        print(f"\n--- EMAIL FAILED TO SEND ---")
        print(f"Error: {str(e)}")
        print(f"The OTP for {email} is: {otp}\n----------------------------\n")

    # 5. Always return success if the user was created in the database
    return Response({
        "status": "Account Created",
        "message": "Please check your email for the verification code."
    }, status=status.HTTP_201_CREATED)


# ==========================================
# NEW ENDPOINT: VERIFY OTP
# ==========================================
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_otp(request):
    # 1. Grab the data from React Native
    email = request.data.get('email')
    otp = request.data.get('otp')

    # X-RAY DEBUGGING: Print exactly what we received to the terminal
    print(f"\n--- OTP VERIFICATION ATTEMPT ---")
    print(f"Email from App: '{email}'")
    print(f"OTP from App: '{otp}'")

    try:
        user = User.objects.get(email=email)
        profile = user.profile

        print(f"OTP in Database: '{profile.email_otp}'")

        if profile.is_email_verified:
            print("Result: ALREADY VERIFIED (Issuing tokens anyway)")
            # Issue the login tokens even if they double-tapped!
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
        # 2. BULLETPROOF CHECK: Force both to be strings and strip any invisible spaces
        db_otp_clean = str(profile.email_otp).strip()
        app_otp_clean = str(otp).strip()

        if db_otp_clean == app_otp_clean:
            print("Result: EXACT MATCH! Logging user in.")
            
            profile.is_email_verified = True
            profile.email_otp = None
            profile.save()

            # Issue the login tokens
            tokens = get_tokens_for_user(user)
            return Response({
                "status": "Verified",
                "tokens": tokens,
                "user_id": user.id,
                "email": user.email
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
def request_password_reset(request):
    email = request.data.get('email')
    
    try:
        user = User.objects.get(email=email)
        # Generate a new 6-digit code
        otp = str(random.randint(100000, 999999))
        user.profile.email_otp = otp
        user.profile.save()

        # Hackathon Safety Net
        try:
            send_mail(
                'Reset your Fair App Password',
                f'Your password reset code is: {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"\n--- FORGOT PASSWORD EMAIL FAILED ---")
            print(f"HACKATHON FALLBACK -> Reset OTP for {email} is: {otp}\n")

        # Security best practice: Always return a generic success message 
        # so hackers can't use this to guess registered emails.
        return Response({"message": "If an account exists, a code was sent."}, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({"message": "If an account exists, a code was sent."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
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

# ==========================================
# 3. TRIP & REPORT ENDPOINTS
# ==========================================
@api_view(['POST'])
def submit_trip(request):
    """Logs the final GPS distance and fare to the LGU database"""
    serializer = TripSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"status": "Success", "message": "Trip recorded securely.", "trip_id": serializer.data['trip_id']}, 
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def submit_report(request):
    """Logs an overcharging or arrogant driver complaint"""
    serializer = ReportSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"status": "Success", "message": "Violation report filed. TMO will review."}, 
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)