# PLAN VIVO INTEGRADO — PETHOME SAAS MULTI-TENANT

Estado: `ACTIVO`  
Última actualización: `2026-05-06`  
Modo de trabajo: `Plan vivo` (se actualiza a medida que avanzan implementaciones)

---

## 0. Propósito

Este documento consolida:

1. Gestión de usuarios, grupos y permisos por componentes.
2. Login SaaS con contexto completo.
3. Bitácora confidencial.
4. Flujo Web + Móvil bajo modelo multi-tenant.

Regla central:

- Frontend renderiza según contexto recibido.
- Backend protege y valida permisos en cada endpoint.

---

## 1. Decisiones Cerradas (Aprobadas)

### 1.1 SuperAdmin y tenant

- `SUPERADMIN` debe tener `id_veterinaria = NULL`.
- No se usará “veterinaria global” ficticia.
- `ADMIN`, `VETERINARIAN`, `RECEPCIONISTA`, `CLIENT` requieren `id_veterinaria`.

### 1.2 Login Web y Login Móvil

- Web: `POST /api/auth/login/` (usuarios internos + superadmin).
- Móvil: `POST /api/auth/mobile/login/` (separado).
- En móvil: `slug_veterinaria` obligatorio.

### 1.3 Registro móvil de cliente

- Endpoint: `POST /api/auth/mobile/register/`.
- Requiere `slug_veterinaria`.
- Se habilita solo si la veterinaria lo permite.

Campo requerido:

```sql
ALTER TABLE veterinaria
ADD COLUMN permite_auto_registro_clientes BOOLEAN DEFAULT TRUE;
```

### 1.4 Correo de cliente (v1)

- Correo único global.
- Cliente pertenece a una sola veterinaria.
- No implementar aún tabla puente `usuario_veterinaria`.

### 1.5 Seed de componentes

- Catálogo inicial oficial: `WEB`, `MOVIL`, `SAAS`.
- Estrategia incremental: se agregan nuevos componentes cuando aparezcan nuevos casos.
- No borrar componentes ya usados por permisos.

### 1.6 Bitácora

- `DEBUG=True`: modo tolerante (no romper flujo por error de cifrado; loggear aviso).
- `DEBUG=False`: modo estricto (sin clave válida no se permite operar bitácora sensible).

---

## 2. Principios de Arquitectura

1. Tenant aislado por `id_veterinaria`.
2. Doble control: `rol base` + `grupo/permiso por componente`.
3. Componentes globales en catálogo recursivo.
4. Permisos configurables por veterinaria.
5. Contexto SaaS en login: usuario + veterinaria + plan + componentes.
6. Bitácora confidencial de solo lectura.

---

## 3. Roles Base

- `SUPERADMIN`
- `ADMIN`
- `VETERINARIAN`
- `RECEPCIONISTA`
- `CLIENT`

Reglas:

- `SUPERADMIN`: operación global SaaS, sin veterinaria.
- `ADMIN`: solo su veterinaria.
- `VETERINARIAN`: foco clínico.
- `RECEPCIONISTA`: foco operativo.
- `CLIENT`: solo datos propios de su veterinaria.

---

## 4. Modelo de Permisos

### Nivel 1: Rol base

Clasifica al usuario (tipo general).

### Nivel 2: Grupo + permiso por componente

Define acciones reales:

- `puede_ver`
- `puede_crear`
- `puede_editar`
- `puede_eliminar`
- `puede_exportar`
- `puede_ejecutar`

Regla de combinación:

- Si el usuario está en varios grupos, permisos se combinan con `OR lógico`.

---

## 5. Componentes Recursivos

Tabla: `componente_sistema` (catálogo global).

Tipos sugeridos:

- `MODULO`
- `MENU`
- `FORMULARIO`
- `BOTON`
- `CAMPO`
- `LABEL`
- `TEXTO`
- `ACCION`

Plataformas:

- `WEB`
- `MOVIL`
- `AMBOS`

Regla de árbol:

- Si se permite un hijo, backend debe incluir sus padres en la respuesta.

---

## 6. Grupos Base por Veterinaria

Por cada veterinaria se crean:

- `ADMIN_BASE`
- `VETERINARIAN_BASE`
- `RECEPCIONISTA_BASE`
- `CLIENT_BASE`

Campos requeridos en `grupo_usuario`:

```sql
ALTER TABLE grupo_usuario
ADD COLUMN es_base BOOLEAN DEFAULT FALSE,
ADD COLUMN rol_base VARCHAR(50);
```

---

## 7. Seeds

### 7.1 Seed global (una vez)

Puebla `componente_sistema`.

### 7.2 Seed por veterinaria

Al crear veterinaria:

1. Crear grupos base.
2. Crear permisos base por grupo.
3. Asignar ADMIN inicial a `ADMIN_BASE`.

Regla:

- No sobrescribir permisos personalizados existentes.

---

## 8. Flujos clave

### 8.1 Crear veterinaria (SuperAdmin)

Transaccional:

1. Crear veterinaria.
2. Crear suscripción inicial.
3. Crear grupos base.
4. Seed permisos base.
5. Crear ADMIN inicial.
6. Asignar ADMIN a grupo base.
7. Registrar bitácora.

### 8.2 Crear usuario interno (ADMIN)

1. Validar permiso.
2. Validar tenant del creador.
3. Validar límite de plan.
4. Crear usuario con tenant heredado.
5. Crear perfil.
6. Asignar a grupo base por rol.
7. Registrar bitácora.

### 8.3 Login web interno

`POST /api/auth/login/`

1. Credenciales.
2. Usuario activo.
3. Veterinaria activa (si no es superadmin).
4. Suscripción válida.
5. Plan.
6. Grupos.
7. Permisos por componente WEB.
8. Árbol recursivo.
9. Token + contexto.
10. Bitácora.

### 8.4 Login móvil cliente

`POST /api/auth/mobile/login/`

1. Validar `slug_veterinaria`.
2. Veterinaria activa.
3. Plan permite móvil.
4. Usuario activo y rol `CLIENT`.
5. Usuario pertenece a esa veterinaria.
6. Permisos MOVIL.
7. Token + contexto.
8. Bitácora.

### 8.5 Registro móvil cliente

`POST /api/auth/mobile/register/`

1. Resolver veterinaria por slug.
2. Validar `permite_auto_registro_clientes = true`.
3. Validar suscripción/plan móvil.
4. Correo único global.
5. Crear usuario `CLIENT` con tenant.
6. Crear perfil.
7. Asignar `CLIENT_BASE`.
8. Bitácora.

---

## 9. Endpoints objetivo

### Autenticación

- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`
- `GET /api/auth/componentes/?plataforma=WEB`
- `GET /api/auth/componentes/?plataforma=MOVIL`

### Público móvil

- `GET /api/public/veterinarias/`
- `GET /api/public/veterinarias/{slug}/`
- `POST /api/auth/mobile/register/`
- `POST /api/auth/mobile/login/`

### SaaS (SuperAdmin)

- `POST /api/saas/veterinarias/`
- `GET /api/saas/veterinarias/`
- `PATCH /api/saas/veterinarias/{id}/estado/`
- `GET/POST/PATCH /api/saas/planes/`
- `GET/POST/PATCH /api/saas/suscripciones/`

### Usuarios y permisos

- `GET/POST /api/usuarios/`
- `GET/PUT/PATCH /api/usuarios/{id}/`
- `GET/POST /api/grupos/`
- `GET/PATCH /api/grupos/{id}/`
- `GET/POST /api/grupos/{id}/permisos/`
- `PATCH /api/grupos/{id}/permisos/{id_permiso}/`

### Bitácora

- `GET /api/bitacora/`
- `GET /api/bitacora/{id}/`

No exponer:

- `PUT /api/bitacora/{id}/`
- `DELETE /api/bitacora/{id}/`

---

## 10. Catálogo base de componentes (inicial)

### WEB (mínimos)

- `MENU_DASHBOARD`
- `MENU_USUARIOS`
- `MENU_CLIENTES`
- `MENU_MASCOTAS`
- `MENU_SERVICIOS`
- `MENU_CITAS`
- `MENU_RESERVAS`
- `MENU_BITACORA`
- `BTN_CREAR_USUARIO`
- `BTN_EDITAR_USUARIO`
- `BTN_DESACTIVAR_USUARIO`
- `BTN_CREAR_CLIENTE`
- `BTN_EDITAR_CLIENTE`
- `BTN_DESACTIVAR_CLIENTE`
- `BTN_CREAR_MASCOTA`
- `BTN_EDITAR_MASCOTA`
- `BTN_DESACTIVAR_MASCOTA`
- `BTN_CREAR_SERVICIO`
- `BTN_EDITAR_SERVICIO`
- `BTN_DESACTIVAR_SERVICIO`
- `BTN_CONFIRMAR_CITA`
- `BTN_REPROGRAMAR_CITA`
- `BTN_CANCELAR_CITA`
- `BTN_EXPORTAR_BITACORA`

### MOVIL (mínimos)

- `MOVIL_HOME`
- `MOVIL_MI_PERFIL`
- `MOVIL_MIS_MASCOTAS`
- `MOVIL_CREAR_MASCOTA`
- `MOVIL_EDITAR_MASCOTA`
- `MOVIL_CATALOGO_SERVICIOS`
- `MOVIL_SOLICITAR_CITA`
- `MOVIL_MIS_RESERVAS`
- `MOVIL_CANCELAR_RESERVA`
- `MOVIL_HISTORIAL_MASCOTA`
- `MOVIL_NOTIFICACIONES`

### SAAS (SuperAdmin)

- `MENU_SAAS_DASHBOARD`
- `MENU_SAAS_VETERINARIAS`
- `MENU_SAAS_PLANES`
- `MENU_SAAS_SUSCRIPCIONES`
- `MENU_SAAS_USUARIOS_GLOBALES`
- `MENU_SAAS_BITACORA_GLOBAL`
- `BTN_CREAR_VETERINARIA`
- `BTN_EDITAR_VETERINARIA`
- `BTN_ACTIVAR_VETERINARIA`
- `BTN_DESACTIVAR_VETERINARIA`
- `BTN_CREAR_PLAN`
- `BTN_EDITAR_PLAN`
- `BTN_CREAR_SUSCRIPCION`

---

## 11. Bitácora — eventos mínimos

- `LOGIN_EXITOSO`
- `LOGIN_FALLIDO`
- `LOGOUT_EXITOSO`
- `COMPONENTES_CARGADOS`
- `VETERINARIA_CREADA`
- `SUSCRIPCION_CREADA`
- `GRUPOS_BASE_CREADOS`
- `PERMISOS_BASE_CREADOS`
- `ADMIN_INICIAL_CREADO`
- `USUARIO_CREADO`
- `USUARIO_EDITADO`
- `USUARIO_ACTIVADO`
- `USUARIO_DESACTIVADO`
- `USUARIO_ASIGNADO_GRUPO`
- `USUARIO_REMOVIDO_GRUPO`
- `GRUPO_CREADO`
- `GRUPO_EDITADO`
- `GRUPO_DESACTIVADO`
- `PERMISO_CREADO`
- `PERMISO_EDITADO`
- `PERMISO_ELIMINADO`
- `BITACORA_CONSULTADA`
- `BITACORA_EXPORTADA`
- `ACCESO_DENEGADO`
- `INTENTO_ACCESO_OTRO_TENANT`

---

## 12. Checklist de implementación (vivo)

### Fase A — Base de datos y consistencia

- [x] Permitir `usuarios.id_veterinaria` nullable para `SUPERADMIN`.
- [x] Agregar `veterinaria.permite_auto_registro_clientes`.
- [x] Agregar `grupo_usuario.es_base`.
- [x] Agregar `grupo_usuario.rol_base`.

### Fase B — Seeds y plantillas

- [ ] Seed global de `componente_sistema` (WEB/MOVIL/SAAS).
- [ ] Seed de grupos base por veterinaria.
- [ ] Seed de permisos base por grupo.

### Fase C — Flujos SaaS

- [ ] Endpoint creación de veterinaria por superadmin (transaccional).
- [ ] Login web interno consolidado con contexto.
- [ ] `GET /api/auth/me/` con reconstrucción de contexto.
- [ ] `GET /api/auth/componentes/` por plataforma.

### Fase D — Móvil cliente

- [ ] `GET /api/public/veterinarias/`.
- [ ] `GET /api/public/veterinarias/{slug}/`.
- [ ] `POST /api/auth/mobile/register/`.
- [ ] `POST /api/auth/mobile/login/`.

### Fase E — Seguridad y auditoría

- [ ] Validación de permisos por componente en endpoints críticos.
- [ ] Validación de tenant en escritura y lectura.
- [ ] Bitácora tolerante en `DEBUG=True`.
- [ ] Bitácora estricta en `DEBUG=False`.

### Fase F — Verificación

- [ ] Pruebas por rol: SUPERADMIN, ADMIN, VETERINARIAN, RECEPCIONISTA, CLIENT.
- [ ] Pruebas de aislamiento entre 2 veterinarias.
- [ ] Pruebas de bitácora: lectura por tenant y global.

---

## 13. Registro de avance (bitácora del plan)

### 2026-05-06

- Se consolida plan integrado SaaS + ajustes finales aprobados.
- Documento inicial creado como base de seguimiento.
- Aún sin aplicar cambios nuevos de código en esta etapa.
- Fase A aplicada en modelos y migraciones:
  - `usuarios.id_veterinaria` ahora nullable.
  - `veterinaria.permite_auto_registro_clientes` agregado.
  - `grupo_usuario.es_base` y `grupo_usuario.rol_base` agregados.
  - Estado de migraciones limpio (`makemigrations --check` sin cambios).

---

## 14. Regla de actualización de este archivo

Cada implementación debe actualizar:

1. Checklist de fase correspondiente.
2. Registro de avance con fecha.
3. Cambios de decisión (si hubiera) en sección 1.

Este documento es la fuente principal de seguimiento funcional y técnico del SaaS.
