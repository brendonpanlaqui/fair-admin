from django.urls import path
from . import views

urlpatterns = [
    # Fare and Trip routes
    path('api/fare-matrix/active/', views.get_active_fare, name='api-get-active-fare'),
    path('api/trips/submit/', views.submit_trip, name='api-submit-trip'),
    path('api/reports/submit/', views.submit_report, name='api-submit-report'),
    
    # Auth routes (This is what Postman is looking for!)
    path('api/auth/login/', views.mobile_login, name='api-login'),
    path('api/auth/register/', views.mobile_register, name='api-register'),
    path('api/auth/verify-otp/', views.verify_email_otp, name='api-verify-otp'),
    path('api/auth/forgot-password/', views.request_password_reset, name='api-forgot-password'),
    path('api/auth/reset-password/', views.reset_password, name='api-reset-password'),

    path('api/trips/history/', views.get_trip_history, name='trip-history'),
    path('api/reports/history/', views.get_report_history, name='api-report-history'),
]