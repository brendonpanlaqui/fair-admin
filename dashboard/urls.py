from django.urls import path
from . import views

urlpatterns = [
    # Authentication and Authorization Routes
    path('api/auth/login/', views.mobile_login, name='api-login'),
    path('api/auth/register/', views.mobile_register, name='api-register'),
    path('api/auth/verify-otp/', views.verify_email_otp, name='api-verify-otp'),
    path('api/auth/resend-otp/', views.resend_otp, name='api-resend-otp'),
    path('api/auth/forgot-password/', views.request_password_reset, name='api-forgot-password'),
    path('api/auth/reset-password/', views.reset_password, name='api-reset-password'),
    path('api/auth/change-password/', views.change_password, name='api-change-password'),
    
    # User Profile & Account Management
    path('api/users/me/', views.get_user_profile, name='api-get-profile'),
    path('api/users/verify-id/', views.submit_id_verification, name='api-verify-id'),

    # Fare & Trips
    path('api/fare-matrix/active/', views.get_active_fare, name='api-get-active-fare'),
    path('api/trips/submit/', views.submit_trip, name='api-submit-trip'),
    path('api/trips/history/', views.get_trip_history, name='trip-history'),

    # Reports
    path('api/reports/submit/', views.submit_report, name='api-submit-report'),
    path('api/reports/history/', views.get_report_history, name='api-report-history'),

    # Tricycles
    path('api/tricycles/check/<str:body_number>/', views.check_tricycle, name='api-check-tricycle'),
]