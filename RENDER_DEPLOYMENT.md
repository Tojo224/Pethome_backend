# 🚀 Guía de Despliegue en Render

Este documento describe los pasos necesarios para desplegar la aplicación HomePet en Render.

## Archivos de Configuración Generados

Se han creado los siguientes archivos para facilitar el despliegue:

- **`Procfile`** - Define cómo ejecutar la aplicación (servidor web)
- **`render.yaml`** - Configuración de servicios y base de datos en Render
- **`runtime.txt`** - Especifica la versión de Python (3.11)
- **`build.sh`** - Script de build que ejecuta migraciones y recoge archivos estáticos
- **`.env.example`** - Plantilla de variables de entorno

## Requisitos Previos

1. Una cuenta en [Render.com](https://render.com)
2. El proyecto en un repositorio Git (GitHub, GitLab o Gitea)
3. Las dependencias actualizadas (incluyendo `gunicorn` y `whitenoise`)

## Pasos para Desplegar

### 1. Preparar el Repositorio

```bash
# Asegúrate de que todos los cambios estén commiteados
git add .
git commit -m "chore: add render deployment files"
git push origin main
```

### 2. Crear Servicio en Render

1. Ve a [https://dashboard.render.com](https://dashboard.render.com)
2. Haz clic en **"New +"** → **"Web Service"**
3. Conecta tu repositorio de Git
4. Selecciona la rama principal (main/master)

### 3. Configurar el Servicio Web

En la sección de configuración, ingresa:

- **Name:** `homepet-api`
- **Environment:** `Python 3`
- **Region:** Elige la que prefieras (recomendado Ohio)
- **Build Command:** `./build.sh`
- **Start Command:** `gunicorn pethome_back.wsgi --log-file -`

### 4. Configurar Variables de Entorno

En la sección **Environment**, agrega las siguientes variables:

```
SECRET_KEY = [Genera una clave segura]
DEBUG = False
ALLOWED_HOSTS = *.onrender.com,localhost
CORS_ALLOWED_ORIGINS = https://yourfrontend.domain.com
DATABASE_URL = [Se obtiene automáticamente de la BD]
```

**Para generar un SECRET_KEY seguro:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Crear Base de Datos PostgreSQL

1. En el dashboard de Render, haz clic en **"New +"** → **"PostgreSQL"**
2. Ingresa los datos:
   - **Name:** `homepet-db`
   - **Database:** `homepet_db`
   - **User:** `homepet` (o similar)
   - **Region:** La misma que el servicio web
   - **PostgreSQL Version:** 15 (o la más reciente)

3. Copia la **Internal Database URL** que aparece en los detalles de la BD

### 6. Conectar la Base de Datos al Servicio Web

En las **Environment variables** del servicio web, agrega o actualiza:

```
DATABASE_URL = [Pega la URL interna de PostgreSQL]
```

### 7. Deployar

1. El despliegue debería iniciarse automáticamente
2. Monitorea los **Logs** para verificar:
   - ✅ Instalación de dependencias
   - ✅ Ejecución de migraciones
   - ✅ Recolección de archivos estáticos
   - ✅ Inicio del servidor Gunicorn

## Troubleshooting

### Error: "Build failed"

Verifica en los logs:
- Las dependencias en `requirements.txt` son correctas
- El `build.sh` tiene permisos de ejecución
- Las migraciones no tienen errores

### Error: "Database connection refused"

- Asegúrate de que `DATABASE_URL` esté correctamente copiado
- Verifica que la BD esté en el mismo **Private Network** o usa la URL externa

### Error: "No module named 'gunicorn'"

- Asegúrate de que `gunicorn` está en `requirements.txt`
- Ejecuta `pip install -r requirements.txt` localmente para verificar

### Archivos estáticos no se ven (404)

- Verifica que `collectstatic` se ejecutó correctamente en los logs
- Asegúrate de que `STATIC_ROOT` está configurado en `settings.py`

## Configuración Adicional (Opcional)

### Usar Custom Domain

1. En la sección de **Custom Domain** del servicio web
2. Agrega tu dominio
3. Sigue las instrucciones para configurar los DNS

### Configurar Variables de Entorno desde Secrets

Para valores sensibles como `SECRET_KEY`:

1. Ve a **Environment**
2. Usa **"Secrets"** en lugar de variables normales
3. Los secrets no aparecen en los logs

### Escalabilidad

- Para aumentar capacidad: Cambia el **Plan** en **Settings**
- Para auto-scaling: Usa Render Plus

## Monitoreo

- **Logs**: Ve a **Logs** en el dashboard para monitoreo en tiempo real
- **Métricas**: Revisa CPU, memoria y requests en **Metrics**
- **Notificaciones**: Habilita alertas en **Settings** → **Notifications**

## Rollback a Mayor Versión Anterior

Si algo sale mal:

1. Ve a **Deployments**
2. Encuentra el despliegue anterior exitoso
3. Haz clic en **"Redeploy"**

## Próximos Pasos

- [ ] Configurar SSL/TLS (automático en Render)
- [ ] Configurar backup de BD
- [ ] Habilitar métricas y monitoreo
- [ ] Configurar alias de dominio
- [ ] Probar endpoints de API

---

**Nota:** La primera vez que desplegues, puede tomar 5-10 minutos. Los despliegues posteriores son más rápidos.

¿Necesitas ayuda con algún paso? Revisa los logs en el dashboard de Render para más detalles.
