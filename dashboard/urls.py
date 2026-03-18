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
]