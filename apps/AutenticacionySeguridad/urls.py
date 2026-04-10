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


urlpatterns = [
    path("", AuthRootView.as_view(), name="auth-root"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("login", LoginView.as_view(), name="auth-login-no-slash"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("logout", LogoutView.as_view(), name="auth-logout-no-slash"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("me", MeView.as_view(), name="auth-me-no-slash"),

    path('usuarios/', UsuarioListCreateView.as_view(), name='usuario-list-create'),
    path('usuarios/clientes/', UsuarioClienteListView.as_view(), name='usuario-clientes-list'),
    path('usuarios/<int:pk>/', UsuarioDetailView.as_view(), name='usuario-detail'),
<<<<<<< HEAD
    
=======

    path("bitacora/", BitacoraListView.as_view(), name="bitacora-list"),
    path("bitacora", BitacoraListView.as_view(), name="bitacora-list-no-slash"),
    path("bitacora/<int:pk>/", BitacoraDetailView.as_view(), name="bitacora-detail"),
    path("bitacora/<int:pk>", BitacoraDetailView.as_view(), name="bitacora-detail-no-slash"),
>>>>>>> origin/main

]