from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings             
from django.conf.urls.static import static   

admin.site.index_title = "Dashboard"       

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False), name='index'),
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)