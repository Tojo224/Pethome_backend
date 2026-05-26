# Plan SaaS Pethome (Pago Demo en Backend) - En Fases

## Objetivo general
- Implementar flujo SaaS completo: prueba gratis, compra directa y upgrade desde trial.
- Mantener backend sin integración real de Stripe por ahora.
- Backend recibirá confirmación de pago en modo demo y activará suscripción.
- Coordinar ejecución con proyectos separados:
  - Backend API (este repo)
  - Front Web (repo separado)
  - Front Móvil (repo separado)

## Principios para no romper lo existente
- No reemplazar la arquitectura actual multi-tenant; solo extenderla.
- Mantener roles actuales (`SUPERADMIN`, `ADMIN`, etc.).
- No crear rol nuevo `OWNER`; usar atributo de ownership comercial.
- Implementar cambios incrementales con pruebas por fase.
- Usar bandera de entorno `BILLING_MODE=DEMO`.

## Modelo de cuentas y gobierno
- `SUPERADMIN`: alcance global del sistema (todas las veterinarias).
- `ADMIN`: administración operativa de su veterinaria.
- `owner comercial`: un admin especial por veterinaria, definido por atributo (ej. `veterinaria.owner_user_id`).
- Se permiten múltiples admins por veterinaria, pero un solo owner comercial activo.

## Flujos comerciales objetivo

### 1) Prueba gratis
1. Usuario entra a landing y elige `Prueba gratis`.
2. Backend crea:
   - `veterinaria` (tenant)
   - usuario admin inicial (owner comercial)
   - `suscripcion` con estado `PRUEBA` y fecha fin
3. Se devuelve acceso para iniciar sesión y operar.

### 2) Compra directa (demo)
1. Usuario entra a landing y elige `Comprar ahora`.
2. Front muestra flujo visual de pago (demo Stripe UI).
3. Backend recibe `checkout-demo/start`.
4. Backend recibe `checkout-demo/confirm` y, al confirmar demo:
   - crea `veterinaria`
   - crea admin owner
   - crea `suscripcion` `ACTIVA`

### 3) Upgrade desde trial (sin perder datos)
1. Usuario trial entra a `Facturación` dentro del panel.
2. Inicia `upgrade-demo/start`.
3. Front muestra flujo visual de pago.
4. Backend recibe `upgrade-demo/confirm` y:
   - actualiza suscripción del mismo tenant `PRUEBA -> ACTIVA`
   - conserva todos los datos ya creados.

## Suscripción y control de acceso global
- Estados permitidos para uso normal: `ACTIVA`, `PRUEBA` (opcional `GRACIA`).
- Estados bloqueados: `VENCIDA`, `SUSPENDIDA`, `CANCELADA`.
- Aplicar permiso global para bloquear API privada según estado.
- Excepciones de bloqueo:
  - login/refresh
  - recuperación de contraseña
  - endpoints de facturación demo
  - endpoints públicos de adquisición

## Habilitación por plan (incluye trial)
- Definir matriz por plan (`TRIAL`, `BASICO`, `PRO`, `ENTERPRISE`):
  - límites (usuarios, mascotas, etc.)
  - features (`permite_app_movil`, reportes, backup, etc.)
- Centralizar validación en `PlanAccessService`.
- Aplicar validaciones en endpoints críticos (inicio: creación de usuarios y acceso a features premium).

## Reglas de creación de usuarios
- El admin inicial (owner) se crea junto con el tenant en trial o compra directa.
- El admin puede crear más cuentas dentro de su veterinaria.
- Toda creación respeta:
  - `id_veterinaria` del tenant autenticado
  - límites del plan
  - RBAC vigente

## Datos comerciales vs perfil de usuario
- `veterinaria.correo` y `veterinaria.telefono`: contacto comercial de la cuenta.
- `perfil` del admin: datos personales/operativos.
- Pueden iniciar iguales y luego editarse por separado.

## Pago demo backend (sin Stripe real)
- Crear registro de eventos demo de facturación (ej. `billing_demo_event`):
  - tipo: `DIRECT_PURCHASE`, `TRIAL_UPGRADE`
  - estado: `STARTED`, `CONFIRMED`, `CANCELLED`
  - plan objetivo
  - referencia de tenant/usuario cuando aplique
  - timestamps y metadatos mínimos
- `confirm` debe:
  - validar que existe `start` abierto
  - ser idempotente (evitar dobles activaciones)
  - cerrar evento y activar/actualizar suscripción
- Marcar transacciones con `payment_mode=DEMO`.

## Seguridad mínima del modo demo
- Proteger `confirm` con token temporal de checkout demo.
- Expirar sesiones de checkout demo.
- Registrar bitácora de `start`, `confirm`, `cancel`.
- No exponer endpoints de confirmación sin validaciones.

## UX mínima requerida
- Landing con dos CTAs:
  - `Prueba gratis`
  - `Comprar ahora`
- Trial dentro del panel:
  - banner de vencimiento
  - CTA a facturación
- Pantalla de `Suscripción/Facturación`:
  - plan actual
  - estado suscripción
  - vencimiento
  - acciones de compra/upgrade

## Casos de prueba obligatorios
1. Trial crea tenant + admin + suscripción `PRUEBA`.
2. Compra directa demo crea tenant + suscripción `ACTIVA`.
3. Upgrade demo desde trial mantiene todos los datos.
4. Tenant bloqueado no accede a módulos privados.
5. Límites de plan se aplican correctamente.
6. Confirmación duplicada no duplica suscripción ni recursos.
7. Aislamiento tenant: un tenant no ve datos de otro.

## Plan por fases (backend + front web + front móvil)

### Fase 0 - Alineación y contratos
Objetivo: definir contratos API y alcance por repositorio sin tocar lógica existente.

Backend:
1. Definir payloads/respuestas de:
   - `trial-signup`
   - `checkout-demo/start`
   - `checkout-demo/confirm`
   - `upgrade-demo/start`
   - `upgrade-demo/confirm`
2. Definir estados y errores estándar para suscripción y límites.

Front Web:
1. Diseñar flujo de pantallas:
   - landing
   - pricing
   - signup trial
   - checkout demo visual
   - facturación en panel
2. Acordar manejo de errores API.

Front Móvil:
1. Confirmar impacto: solo lectura de estado/plan en contexto.
2. Definir mensajes cuando plan no permite app móvil.

Salida de fase:
- Documento de contratos API y matriz de errores.

---

### Fase 1 - Base SaaS en backend (sin flujos públicos aún)
Objetivo: robustecer gobierno SaaS sin romper endpoints existentes.

Backend:
1. Implementar ownership comercial (`owner_user_id` en veterinaria o equivalente).
2. Unificar resolución de suscripción vigente en un servicio único.
3. Implementar guard global de acceso por estado de suscripción.
4. Mantener excepciones para login/refresh/recuperación y rutas públicas necesarias.

Front Web:
1. Sin cambios funcionales todavía (solo preparar wiring de estados de suscripción).

Front Móvil:
1. Validar comportamiento actual de login contra estados de plan.

Salida de fase:
- Backend listo para controlar acceso SaaS de forma consistente.

---

### Fase 2 - Trial self-service
Objetivo: permitir alta automática de veterinaria con prueba gratis.

Backend:
1. Crear endpoint público `trial-signup`.
2. Crear tenant + admin owner + suscripción `PRUEBA`.
3. Registrar bitácora y controles de idempotencia básicos.

Front Web:
1. Implementar formulario `Prueba gratis`.
2. Conectar al endpoint y redirigir a login/panel.

Front Móvil:
1. Sin cambios obligatorios.

Salida de fase:
- Cualquier cliente puede empezar prueba sin intervención manual.

---

### Fase 3 - Compra directa demo (landing)
Objetivo: habilitar compra directa en modo demo desde web pública.

Backend:
1. Endpoint `checkout-demo/start` para intención de compra.
2. Endpoint `checkout-demo/confirm` para confirmación demo.
3. Al confirmar: crear tenant + admin owner + suscripción `ACTIVA`.
4. Idempotencia estricta en confirmación.

Front Web:
1. Botón `Comprar ahora` en landing/pricing.
2. Flujo visual tipo Stripe demo.
3. Llamada a `start` y luego `confirm`.

Front Móvil:
1. Sin cambios obligatorios.

Salida de fase:
- Cliente puede entrar directo a plan pago demo.

---

### Fase 4 - Upgrade desde trial sin pérdida de datos
Objetivo: convertir trial a pago sin recrear tenant.

Backend:
1. Endpoint autenticado `upgrade-demo/start`.
2. Endpoint autenticado `upgrade-demo/confirm`.
3. Cambio de suscripción `PRUEBA -> ACTIVA` en mismo tenant.
4. Asegurar que no se duplique tenant ni usuario owner.

Front Web:
1. Pantalla `Facturación` con CTA `Comprar plan`.
2. Banner de trial por vencer y acceso a upgrade.
3. Flujo visual demo de pago y confirmación.

Front Móvil:
1. Mostrar estado de suscripción si aplica en contexto.

Salida de fase:
- Trial convierte a pago conservando todos los datos.

---

### Fase 5 - Habilitación por plan (features y límites)
Objetivo: aplicar de forma centralizada lo que cada plan permite.

Backend:
1. Implementar `PlanAccessService`.
2. Aplicar límites y features en endpoints críticos (prioridad: usuarios, móvil, reportes, backups).
3. Estandarizar códigos de error por límite alcanzado/feature no habilitada.

Front Web:
1. Mostrar límites y bloqueos con mensajes claros.
2. Mostrar upsell cuando no alcance el plan.

Front Móvil:
1. Manejar respuesta de “plan no permite móvil” con UX clara.

Salida de fase:
- Plan trial y planes pagos se comportan según reglas comerciales.

---

### Fase 6 - Hardening y pruebas E2E
Objetivo: cerrar calidad, seguridad y operación antes de pasar a pago real.

Backend:
1. Endurecer seguridad de modo demo (tokens temporales, expiración, bitácora completa).
2. Ejecutar pruebas E2E de todos los flujos.
3. Revisar configuración productiva (CORS, HTTPS, cookies seguras).

Front Web:
1. Pruebas E2E de landing -> trial/compra -> panel.
2. Validar mensajes de error y recuperación.

Front Móvil:
1. Pruebas de login y restricciones por plan móvil.

Salida de fase:
- Flujo SaaS demo estable y listo para migrar a Stripe real.

---

### Fase 7 - Preparación para Stripe real (siguiente etapa)
Objetivo: dejar listo el camino para reemplazar `DEMO` por pasarela real.

Backend:
1. Mantener abstracción `payment_mode`.
2. Diseñar interfaz de proveedor de pagos.
3. Preparar estructura para webhook real.

Front Web:
1. Reemplazar animación demo por checkout real sin romper UX.

Front Móvil:
1. Sin impacto directo inicial.

Salida de fase:
- Migración a Stripe real con cambios acotados.

## Criterios de cierre de fase
- Un cliente puede iniciar prueba gratis sin intervención manual.
- Un cliente puede comprar directo en modo demo.
- Un tenant en trial puede pagar y continuar sin pérdida de datos.
- Owner comercial gestiona facturación de su veterinaria.
- Superadmin mantiene control global.
- Plataforma mantiene aislamiento tenant y límites por plan.
