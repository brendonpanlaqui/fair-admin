from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings             
from django.conf.urls.static import static   
from dashboard.views import backup_restore_view

admin.site.index_title = "Dashboard"       

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False), name='index'),
    path('admin/backup-restore/', backup_restore_view, name='backup_restore'),
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path(
        'favicon.ico',
        RedirectView.as_view(url=settings.STATIC_URL + 'images/favicon.png'),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)