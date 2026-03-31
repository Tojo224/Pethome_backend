from django.urls import path
from apps.AutenticacionySeguridad.views.auth_view import LoginView, LogoutView, MeView
from .views.perfil_views import (
    PerfilView, 
    PerfilDetailView, 
    PerfilClienteView
)
from .views.register_view import RegisterView   

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),

    path('perfiles/', PerfilView.as_view(), name='perfil-list'),
    path('perfiles/clientes/', PerfilClienteView.as_view(), name='perfil-clientes'),
    path('perfiles/<int:pk>/', PerfilDetailView.as_view(), name='perfil-detail'),
    
    path("register/", RegisterView.as_view(), name="auth-register"),
]