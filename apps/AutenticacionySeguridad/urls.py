from django.urls import path
from apps.AutenticacionySeguridad.views.auth_view import (
    LoginView,
    LogoutView,
    MeView,
    AuthRootView,
)
from .views.perfil_views import (
    UsuarioListCreateView,
    UsuarioDetailView,
    UsuarioClienteListView,
)
from .views.bitacora_view import (
    BitacoraListView,
    BitacoraDetailView,
)
from .views.grupo_views import (
    GrupoUsuarioListCreateView,
    GrupoUsuarioDetailView,
    GrupoPermisoComponenteListCreateView,
    GrupoPermisoComponenteDetailView,
)

urlpatterns = [
    path("", AuthRootView.as_view(), name="auth-root"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),

    path('usuarios/', UsuarioListCreateView.as_view(), name='usuario-list-create'),
    path('usuarios/clientes/', UsuarioClienteListView.as_view(), name='usuario-clientes-list'),
    path('usuarios/<int:pk>/', UsuarioDetailView.as_view(), name='usuario-detail'),
    

    path("bitacora/", BitacoraListView.as_view(), name="bitacora-list"),
    path("bitacora/<int:pk>/", BitacoraDetailView.as_view(), name="bitacora-detail"),

    path("grupos/", GrupoUsuarioListCreateView.as_view(), name="grupo-usuario-list-create"),
    path("grupos/<int:pk>/", GrupoUsuarioDetailView.as_view(), name="grupo-usuario-detail"),

    path("grupos-permisos/", GrupoPermisoComponenteListCreateView.as_view(), name="grupo-permiso-list-create"),
    path("grupos-permisos/<int:pk>/", GrupoPermisoComponenteDetailView.as_view(), name="grupo-permiso-detail"),

]