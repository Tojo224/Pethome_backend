from django.urls import path
from apps.AutenticacionySeguridad.views.auth_view import LoginView, LogoutView, MeView
from .views.perfil_views import (
    UsuarioListCreateView,
    UsuarioDetailView,
    UsuarioClienteListView,
)


urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),

    path('usuarios/', UsuarioListCreateView.as_view(), name='usuario-list-create'),
    path('usuarios/clientes/', UsuarioClienteListView.as_view(), name='usuario-clientes-list'),
    path('usuarios/<int:pk>/', UsuarioDetailView.as_view(), name='usuario-detail'),

]