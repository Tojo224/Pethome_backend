# API de Alertas de Inventario

## Descripción General

Sistema de control y alertas de inventario que detecta:
- Stock por debajo del mínimo
- Stock agotado (cantidad = 0)
- Productos vencidos
- Productos próximos a vencer

## Endpoints Disponibles

### 1. Stocks Bajos

**GET** `/api/inventario/alertas/stocks-bajos/`

Obtiene todos los productos con stock por debajo de la cantidad mínima.

**Response:**
```json
{
  "cantidad": 5,
  "resultados": [
    {
      "id_stock": 1,
      "producto_nombre": "Alimento Premium Perros",
      "punto_inventario_nombre": "Almacen General",
      "cantidad": 5.0,
      "cantidad_minima": 20.0,
      "cantidad_faltante": 15.0,
      "numero_lote": "LOTE-001"
    }
  ]
}
```

---

### 2. Stocks Agotados

**GET** `/api/inventario/alertas/stocks-agotados/`

Obtiene todos los productos sin stock disponible.

**Response:**
```json
{
  "cantidad": 3,
  "resultados": [
    {
      "id_stock": 2,
      "producto_nombre": "Vitaminas para Gatos",
      "punto_inventario_nombre": "Sucursal Centro",
      "numero_lote": "LOTE-002"
    }
  ]
}
```

---

### 3. Lotes Vencidos

**GET** `/api/inventario/alertas/lotes-vencidos/`

Obtiene todos los lotes vencidos que aún tienen stock.

**Response:**
```json
{
  "cantidad": 2,
  "resultados": [
    {
      "id_stock": 3,
      "producto_nombre": "Antibiótico XYZ",
      "punto_inventario_nombre": "Almacen General",
      "fecha_vencimiento_lote": "2026-05-15",
      "numero_lote": "LOTE-003",
      "cantidad": 10.0,
      "dias_para_vencer": -12
    }
  ]
}
```

---

### 4. Lotes Próximos a Vencer

**GET** `/api/inventario/alertas/lotes-proximo-vencer/?dias=30`

Obtiene lotes que vencerán en los próximos X días.

**Query Parameters:**
- `dias` (opcional): Número de días de anticipación para la alerta (default: 30)

**Response:**
```json
{
  "dias_alerta": 30,
  "cantidad": 4,
  "resultados": [
    {
      "id_stock": 4,
      "producto_nombre": "Alimento Medicado",
      "punto_inventario_nombre": "Unidad Móvil 1",
      "fecha_vencimiento_lote": "2026-06-10",
      "numero_lote": "LOTE-004",
      "cantidad": 25.0,
      "dias_para_vencer": 14
    }
  ]
}
```

---

### 5. Resumen de Alertas

**GET** `/api/inventario/alertas/resumen/?dias=30`

Obtiene un consolidado de todas las alertas.

**Query Parameters:**
- `dias` (opcional): Días de anticipación para alertas de vencimiento (default: 30)

**Response:**
```json
{
  "cantidad_stocks_bajos": 5,
  "cantidad_stocks_agotados": 3,
  "cantidad_lotes_vencidos": 2,
  "cantidad_lotes_proximo_vencer": 4,
  "total_alertas": 14,
  "stocks_bajos": [...],
  "stocks_agotados": [...],
  "lotes_vencidos": [...],
  "lotes_proximo_vencer": [...]
}
```

---

### 6. Productos para Reposición

**GET** `/api/inventario/alertas/productos-para-reposicion/`

Obtiene lista ordenada de productos que necesitan reposición (ordenados por urgencia).

**Response:**
```json
{
  "cantidad": 3,
  "resultados": [
    {
      "stock_id": 1,
      "producto_id": 5,
      "producto_nombre": "Alimento Premium Perros",
      "punto_inventario": "Almacen General",
      "cantidad_actual": 5.0,
      "cantidad_minima": 20.0,
      "cantidad_faltante": 15.0,
      "proveedor": "Distribuidora ABC"
    }
  ]
}
```

---

### 7. Validar Disponibilidad

**GET** `/api/inventario/alertas/validar-disponibilidad/?stock_id=1&cantidad=10`

Valida si un producto está disponible en la cantidad requerida y no está vencido.

**Query Parameters:**
- `stock_id` (requerido): ID del stock a validar
- `cantidad` (requerido): Cantidad a validar

**Response - Disponible:**
```json
{
  "disponible": true,
  "mensaje": "Producto disponible",
  "stock_id": "1",
  "cantidad_requerida": 10.0
}
```

**Response - No Disponible:**
```json
{
  "disponible": false,
  "mensaje": "El producto está vencido",
  "stock_id": "1",
  "cantidad_requerida": 10.0
}
```

---

## Métodos de Modelo

### StockPunto

```python
# Verificar si stock está bajo
stock.es_stock_bajo()  # bool

# Verificar si stock está agotado
stock.es_stock_agotado()  # bool

# Verificar si lote está vencido
stock.esta_vencido()  # bool

# Verificar si lote vence en X días
stock.proximo_a_vencer(dias=30)  # bool
```

---

## Servicio de Validación

Usar `InventarioValidacionService` para lógica de negocio:

```python
from apps.GestionInventarioProveedores.services.inventario_validacion_service import (
    InventarioValidacionService
)

# Obtener todos los stocks bajos
stocks_bajos = InventarioValidacionService.get_stocks_bajos(veterinaria_id)

# Obtener todos los vencidos
vencidos = InventarioValidacionService.get_productos_vencidos(veterinaria_id)

# Obtener lista de reposición
reposicion = InventarioValidacionService.obtener_productos_para_reposicion(veterinaria_id)

# Validar disponibilidad
disponible, mensaje = InventarioValidacionService.validar_producto_disponible(
    stock_punto_id=1,
    cantidad_requerida=10
)
```

---

## Campos de Modelo

### Producto
- `requiere_control_vencimiento`: Boolean para activar control de vencimiento
- `fecha_vencimiento`: Fecha de vencimiento del producto
- `dias_alerta_vencimiento`: Días de anticipación para alerta (default: 30)

### StockPunto
- `numero_lote`: Identificador del lote
- `fecha_vencimiento_lote`: Fecha de vencimiento del lote específico
- Métodos: `es_stock_bajo()`, `es_stock_agotado()`, `esta_vencido()`, `proximo_a_vencer()`

---

## Permisos Requeridos

Todos los endpoints requieren:
- Usuario autenticado
- Pertenencia a una veterinaria

Los datos se filtran automáticamente por la veterinaria del usuario autenticado.

---

## Ejemplos de Uso

### Listar todos los problemas de inventario

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/inventario/alertas/resumen/?dias=30"
```

### Obtener solo productos vencidos

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/inventario/alertas/lotes-vencidos/"
```

### Validar si puedo usar un producto

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/inventario/alertas/validar-disponibilidad/?stock_id=5&cantidad=10"
```

---

## Códigos de Respuesta HTTP

- **200**: Consulta exitosa
- **400**: Parámetros inválidos
- **401**: No autenticado
- **403**: No tiene permisos (no pertenece a veterinaria)
- **404**: Recurso no encontrado
- **500**: Error del servidor

