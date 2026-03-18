from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken

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
                "email": user.email
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

    if not email or len(password) < 8:
        return Response({"error": "Invalid email or password too short"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Email is already registered"}, status=status.HTTP_400_BAD_REQUEST)

    # Create the secure Django User
    user = User.objects.create(
        username=email, 
        email=email,
        password=make_password(password)
    )
    
    # Create the linked Fair Passenger Profile
    UserProfile.objects.create(user=user, user_type='REGULAR')

    tokens = get_tokens_for_user(user)
    return Response({
        "status": "Account Created",
        "tokens": tokens
    }, status=status.HTTP_201_CREATED)

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