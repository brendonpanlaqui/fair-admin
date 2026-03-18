from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

admin.site.index_title = "Dashboard"       

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False), name='index'),
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
]
