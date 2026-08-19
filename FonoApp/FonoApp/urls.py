from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/usuarios/', include('FonoAppAdministracion.urls')),
    path('api/noticias/', include('FonoAppNoticias.urls')), 
    path('api/informacion/', include('FonoAppInformacion.urls')),
    path('api/cuidados/', include('FonoAppCuidados.urls')),
    path('api/info-general/', include('FonoAppInfoGeneral.urls')),
    path('api/voz/', include('FonoAppVoz.urls')),
]

# Esto sirve los archivos físicos solo cuando se esta en modo desarrollo (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)