# Testing Local Antes de Desplegar

Antes de desplegar a Render, prueba la configuración localmente para evitar sorpresas.

## 1. Configurar Variables de Entorno Locales

Crea un archivo `.env.local` basado en `.env.example`:

```env
SECRET_KEY=your-test-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=postgresql://postgres:password@localhost:5432/homepet_db
```

## 2. Actualizar Dependencias

```bash
pip install -r requirements.txt
```

## 3. Ejecutar Migraciones Locales

```bash
python manage.py migrate
```

## 4. Recolectar Archivos Estáticos

```bash
python manage.py collectstatic --no-input
```

## 5. Ejecutar con Gunicorn Localmente

```bash
gunicorn pethome_back.wsgi --bind 0.0.0.0:8000 --workers 3 --log-level debug
```

Visita: http://localhost:8000/api/schema/swagger-ui/

## 6. Probar Puntos Finales Clave

```bash
# Test de health check
curl -X GET http://localhost:8000/api/health/

# Test de login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Test con token JWT
curl -X GET http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 7. Verificar en build.sh

Asegúrate de que el script `build.sh` ejecute sin errores:

```bash
chmod +x build.sh
./build.sh
```

## Checklist Pre-Despliegue

- [ ] `requirements.txt` incluye `gunicorn` y `whitenoise`
- [ ] `DEBUG=False` en producción
- [ ] `SECRET_KEY` es una clave segura y única
- [ ] `ALLOWED_HOSTS` incluye tu dominio de Render
- [ ] `CORS_ALLOWED_ORIGINS` incluye tu frontend
- [ ] `DATABASE_URL` está configurado
- [ ] Migraciones funcionan sin errores
- [ ] `collectstatic` funciona correctamente
- [ ] Gunicorn inicia sin problemas
- [ ] Endpoints de API responden correctamente

## Notas Importantes

1. **Gunicorn vs Django runserver**: 
   - Gunicorn es más rápido y seguro para producción
   - Django's `runserver` es solo para desarrollo

2. **WhiteNoise**:
   - Sirve archivos estáticos automáticamente
   - No necesitas servidor Nginx separado
   - Comprime archivos para mayor velocidad

3. **Base de Datos**:
   - Usar PostgreSQL (no SQLite) en producción
   - SQLite no soporta múltiples giros simultáneos

4. **Logs**:
   - En Render, los logs se ven en el dashboard
   - Usa `print()` o `logging` para debugging
