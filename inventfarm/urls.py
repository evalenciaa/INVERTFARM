"""
URL configuration for inventfarm project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('farmacia.urls')),
    path('enfermeria/', include('enfermeria.urls')),
]  # ✅ CERRAR AQUÍ

# ✅ CONFIGURACIÓN PARA SERVIR ARCHIVOS ESTÁTICOS EN DESARROLLO
# ✅ ESTE IF DEBE ESTAR FUERA DE urlpatterns
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
