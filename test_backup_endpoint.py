import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')
django.setup()

from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken
from apps.AutenticacionySeguridad.models import User

# Obtener un usuario admin
user = User.objects.filter(is_superuser=True).first()
if user:
    print(f"✓ Usuario encontrado: {user.correo}")
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    # Crear cliente
    client = Client()
    
    # Hacer petición
    response = client.post(
        '/api/auth/backups/create/',
        {'motivo': 'Test backup'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {access_token}'
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.content.decode()[:500]}")
else:
    print("✗ No admin user found")
