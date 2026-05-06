from django.urls import path
from apps.AutenticacionySeguridad.views.auth_view import (
    LoginView,
    LogoutView,
    MeView,
    AuthRootView,
    PublicVeterinariaView,
)
from .views.perfil_views import (
    UsuarioListCreateView,
    UsuarioDetailView,
    UsuarioClienteListView,
    UsuarioActivarView,
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
from .views.usuario_grupo_view import (
    UsuarioGrupoListCreateView,
    UsuarioGrupoDeleteView,
)

urlpatterns = [
    path("", AuthRootView.as_view(), name="auth-root"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("public/veterinarias/<slug:slug>/", PublicVeterinariaView.as_view(), name="public-veterinaria-detail"),

    path('usuarios/', UsuarioListCreateView.as_view(), name='usuario-list-create'),
    path('usuarios/clientes/', UsuarioClienteListView.as_view(), name='usuario-clientes-list'),
    path('usuarios/<int:pk>/', UsuarioDetailView.as_view(), name='usuario-detail'),
    path('usuarios/<int:pk>/activar/', UsuarioActivarView.as_view(), name='usuario-activar'),
    
    path("usuarios-grupos/", UsuarioGrupoListCreateView.as_view(), name="usuario-grupo-list-create"),
    path("usuarios-grupos/<int:pk>/", UsuarioGrupoDeleteView.as_view(), name="usuario-grupo-delete"),

    path("bitacora/", BitacoraListView.as_view(), name="bitacora-list"),
    path("bitacora/<int:pk>/", BitacoraDetailView.as_view(), name="bitacora-detail"),

    path("grupos/", GrupoUsuarioListCreateView.as_view(), name="grupo-usuario-list-create"),
    path("grupos/<int:pk>/", GrupoUsuarioDetailView.as_view(), name="grupo-usuario-detail"),

    path("grupos-permisos/", GrupoPermisoComponenteListCreateView.as_view(), name="grupo-permiso-list-create"),
    path("grupos-permisos/<int:pk>/", GrupoPermisoComponenteDetailView.as_view(), name="grupo-permiso-detail"),

]