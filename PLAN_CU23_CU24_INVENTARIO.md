# Plan de Implementación CU-23 y CU-24 (Inventario)

## 1. Objetivo técnico
Implementar inventario por ubicación (almacén/sucursal/móvil), movimientos auditables y consultas de stock, reutilizando tablas existentes (`veterinaria`, `producto`, `unidad_movil`, `usuarios`) y agregando solo lo necesario.

## 2. Principios que no se negocian
1. No romper multi-tenant: toda consulta/escritura filtrada por `id_veterinaria`.
2. No duplicar tablas existentes: `unidad_movil` se reutiliza.
3. No romper CU ya implementados: cambios backward-compatible.
4. Auditoría completa en movimientos.
5. Cero stock negativo.

## 3. Tablas nuevas (mínimas)
1. `punto_inventario`
- Representa ubicación de stock: `ALMACEN_GENERAL | SUCURSAL | UNIDAD_MOVIL`
- FK `id_veterinaria`

2. `unidad_movil_punto`
- Puente 1:1 entre `unidad_movil` existente y `punto_inventario`
- Evita duplicación de datos de vehículo

3. `stock_punto`
- Stock por producto por punto
- FK `id_punto`, FK `id_producto`, FK `id_veterinaria`
- `UNIQUE(id_punto, id_producto)`

4. `movimiento_inventario`
- Historial de entradas/salidas/consumos/reposiciones/transferencias/devoluciones/ajustes
- FK `id_veterinaria`, `id_producto`, `id_usuario`, `id_punto_origen?`, `id_punto_destino?`
- Campos auditoría: `cantidad_anterior`, `cantidad_posterior`, `motivo`, `fecha_movimiento`

## 4. Reglas de integridad (DB + servicio)
1. `cantidad > 0`
2. Transferencia exige origen y destino distintos.
3. Salida/consumo/transferencia requieren stock suficiente.
4. Ninguna operación deja stock < 0.
5. `id_veterinaria` del movimiento debe coincidir con producto y puntos.
6. Solo una relación activa por móvil en `unidad_movil_punto`.

## 5. Fase 1: Migraciones seguras
1. Crear tablas nuevas sin tocar ni renombrar tablas actuales.
2. Índices por tenant y búsqueda:
- `stock_punto(id_veterinaria, id_producto)`
- `movimiento_inventario(id_veterinaria, fecha_movimiento desc)`
3. Constraints/uniques/checks.
4. Data migration inicial:
- Crear `punto_inventario` tipo `ALMACEN_GENERAL` por veterinaria activa.
- Crear `punto_inventario` tipo `UNIDAD_MOVIL` para cada `unidad_movil` existente y enlazar en `unidad_movil_punto`.
- Inicializar `stock_punto` con 0 donde corresponda (o migrar stock existente si hay fuente válida).

## 6. Fase 2: Dominio y servicios (backend)
1. Servicio transaccional `InventoryMovementService.register_movement(...)`
- Usa `select_for_update()` en filas de `stock_punto`
- Aplica reglas RN24-01..RN24-12
- Registra movimiento y actualiza stock atómicamente

2. Métodos por tipo:
- `register_entry`
- `register_exit`
- `register_consumption`
- `register_restock`
- `register_transfer`
- `register_return`
- `register_adjustment`

3. Permisos:
- Reusar RBAC actual
- Nuevo permiso granular: `inventario.movimientos.gestionar` y `inventario.stock.consultar`

## 7. Fase 3: API CU-24 (movimientos)
1. `POST /api/gestion/inventario/movimientos/` registrar movimiento
2. `GET /api/gestion/inventario/movimientos/` historial con filtros
3. `GET /api/gestion/inventario/movimientos/{id}/` detalle

Validaciones y errores claros:
- `400`: cantidad inválida
- `403`: sin permiso
- `404`: recurso fuera de tenant
- `409`: stock insuficiente / conflicto de negocio

## 8. Fase 4: API CU-23 (consulta/control)
1. `GET /api/gestion/inventario/stock/general/`
2. `GET /api/gestion/inventario/stock/unidades-moviles/`
3. `GET /api/gestion/inventario/stock/productos/{id}/disponibilidad/`
4. `GET /api/gestion/inventario/stock/alertas/` (bajo/agotado)
5. Filtros por categoría, estado, unidad, texto

Importante: CU-23 solo lectura, sin mutaciones.

## 9. Fase 5: Integración con front (sin romper)
1. Mantener endpoints existentes.
2. Agregar nuevos endpoints versionados/compatibles.
3. Contrato JSON estable con mensajes de negocio.
4. Estados de UI:
- éxito: "Movimiento registrado correctamente"
- error stock: "Stock insuficiente para realizar el movimiento"
- error cantidad: "La cantidad debe ser mayor a cero"

## 10. Fase 6: Pruebas obligatorias
1. Unit tests servicio de movimientos (todos los tipos)
2. Concurrency tests (dos salidas simultáneas)
3. API tests permisos y tenant isolation
4. Regression tests sobre módulos ya activos (clientes, clínica, servicios, unidades móviles)
5. Test de "no fuga de datos" entre veterinarias

## 11. Fase 7: Despliegue controlado
1. Deploy en staging con backup previo
2. Ejecutar migraciones
3. Correr suite completa
4. Smoke test CU-23/CU-24 + módulos críticos existentes
5. Habilitar en producción por feature flag (si aplica)

## 12. Riesgos y mitigación
1. Riesgo: romper permisos de admins nuevos
- Mitigación: mapear permisos por rol existente y testear onboarding

2. Riesgo: inconsistencias por concurrencia
- Mitigación: transacciones + locks de fila

3. Riesgo: fuga multi-tenant
- Mitigación: filtro obligatorio por `id_veterinaria` en queryset base + tests

4. Riesgo: conflicto con `unidad_movil`
- Mitigación: no tocar estructura de `unidad_movil`, solo tabla puente

## 13. Entregables
1. Migraciones SQL/Django
2. Modelos y servicios inventario
3. Endpoints CU-23 y CU-24
4. Tests automáticos
5. Documento de contratos API
6. PlantUML actualizado (corregido sin duplicaciones)
