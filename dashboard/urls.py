from django.urls import path
from . import views

urlpatterns = [
    # --- AUTHENTICATION & AUTHORIZATION ---
    path('api/auth/login/', views.mobile_login, name='api-login'),
    path('api/auth/register/', views.mobile_register, name='api-register'),
    path('api/auth/guest-login/', views.GuestLoginView.as_view(), name='guest-login'),
    path('api/auth/verify-otp/', views.verify_email_otp, name='api-verify-otp'),
    path('api/auth/resend-otp/', views.resend_otp, name='api-resend-otp'),
    path('api/auth/forgot-password/', views.request_password_reset, name='api-forgot-password'),
    path('api/auth/reset-password/', views.reset_password, name='api-reset-password'),
    path('api/auth/change-password/', views.change_password, name='api-change-password'),
    
    # --- USER PROFILE & ACCOUNT MANAGEMENT ---
    path('api/users/me/', views.get_user_profile, name='api-get-profile'),
    path('api/users/verify-id/', views.submit_id_verification, name='api-verify-id'),
    path('api/users/apply-driver/', views.apply_driver, name='api-apply-driver'),
    path('api/driver/location/update/', views.update_driver_location, name='api-driver-location-update'),

    # --- PUSH NOTIFICATIONS ---
    path('api/fcm/tokens/update/', views.update_fcm_token, name='api-update-fcm-token'),
    path('api/fcm/tokens/clear/', views.clear_fcm_token, name='api-clear-fcm-token'),

    # --- FARE & TRICYCLE DATA ---
    path('api/fare-matrix/active/', views.get_active_fare, name='api-get-active-fare'),
    path('api/tricycles/check/<str:body_number>/', views.check_tricycle, name='api-check-tricycle'),

    # --- TRIP LIFECYCLE & DIGITAL HANDSHAKE ---
    path('api/trips/request/', views.request_trip, name='api-request-trip'),
    path('api/trips/<str:trip_id>/status/', views.check_trip_status, name='api-check-trip-status'),
    path('api/trips/<str:trip_id>/approve/', views.approve_trip, name='api-approve-trip'),
    path('api/trips/<str:trip_id>/decline/', views.decline_trip, name='api-decline-trip'),
    path('api/trips/<str:trip_id>/cancel/', views.cancel_trip, name='api-cancel-trip'),
    path('api/trips/<str:trip_id>/complete/', views.complete_trip, name='api-complete-trip'),
    path('api/trips/<str:trip_id>/force-end/', views.commuter_force_end, name='api-commuter-force-end'),
    path('api/trips/driver/current/', views.get_current_driver_trip, name='api-driver-current-trip'),
    path('api/trips/commuter/current/', views.get_current_commuter_trip, name='current-commuter-trip'),
    
    # --- HISTORY & REPORTING ---
    path('api/trips/submit/', views.submit_trip, name='api-submit-trip'),
    path('api/trips/history/', views.get_trip_history, name='trip-history'),
    path('api/reports/submit/', views.submit_report, name='api-submit-report'),
    path('api/reports/history/', views.get_report_history, name='api-report-history'),
]