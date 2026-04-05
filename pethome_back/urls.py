
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.AutenticacionySeguridad.urls")),
    path("api/gestion/clientes/", include("apps.GestionClientesyMascotas.urls")),
    path("api/gestion/servicios/", include("apps.GestionServiciosyReserva.urls")),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

]