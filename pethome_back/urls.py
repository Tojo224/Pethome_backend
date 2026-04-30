from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.AutenticacionySeguridad.urls")),
    path("api/gestion/clientes/", include("apps.GestionClientesyMascotas.urls")),
    path("api/servicios/", include("apps.GestionServiciosyReserva.urls")),
    path("api/gestion/servicios/", include("apps.GestionServiciosyReserva.urls")),
    path("api/gestion/clinica/", include("apps.GestionarClinicaVeterinaria.urls")),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/gestion/inventario/", include("apps.GestionInventarioProveedores.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
