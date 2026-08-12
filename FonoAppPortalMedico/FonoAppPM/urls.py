from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/pm/medicos/', include('PmMedico.urls')),
    path('api/pm/clientes/', include('PmCliente.urls')),
    path('api/pm/citas/', include('PmCita.urls')),
    path('api/pm/videos/', include('PmVideo.urls')),
]

# Esto sirve los archivos físicos solo cuando se esta en modo desarrollo (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)