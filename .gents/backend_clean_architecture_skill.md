# Skill: Implementación de Casos de Uso (Arquitectura Limpia Pethome)

Este documento define el flujo de trabajo obligatorio para implementar nuevos Casos de Uso (CU) en el backend de Pethome SaaS, garantizando la mantenibilidad, el aislamiento multitenant y la auditoría.

## 1. Capa de Selectors (Lógica de Lectura)
**Archivo:** `apps/[Modulo]/selectors/[entidad]_selector.py`
- **Regla:** Ninguna vista debe realizar filtrados complejos directamente (`.filter(...)`).
- **Multitenant:** Todos los métodos de consulta deben recibir un `veterinaria_id`.
- **Optimización:** Usar `select_related` y `prefetch_related` para evitar el problema de consultas N+1.

## 2. Capa de Services (Lógica de Escritura y Negocio)
**Archivo:** `apps/[Modulo]/services/[entidad]_service.py`
- **Regla:** La "verdad" del negocio vive aquí. Las validaciones de límites, cálculos y procesos atómicos se hacen en esta capa.
- **Atomicidad:** Usar siempre `@transaction.atomic`.
- **Excepciones:** Lanzar `serializers.ValidationError` para que la capa de vista las capture automáticamente.

## 3. Capa de Mixins y Vistas (Interfaz)
**Archivo:** `apps/[Modulo]/views/[entidad]_view.py`
- **Base:** Heredar siempre de `TenantViewMixin` y `APIView`.
- **Seguridad:** Usar `permission_classes = [IsAuthenticated, HasComponentPermission]` y definir `rbac_component`.
- **Simplicidad:** La vista solo orquesta: llama al selector para leer o al servicio para escribir.

## 4. Sistema de Auditoría (Bitácora)
- **Estandarización:** Usar únicamente `self.registrar_bitacora(...)`.
- **Eventos:** Asegurarse de que el módulo y la acción existan en `apps/AutenticacionySeguridad/events/bitacora_events.py`.
- **Snapshot:** Para ediciones, obtener un snapshot antes de guardar para registrar los cambios exactos.

## Pasos para un nuevo CU:
1. Definir los modelos en la capa de datos.
2. Crear/Actualizar el **Selector** para las consultas necesarias.
3. Crear el **Service** para manejar la lógica de creación/edición.
4. Implementar la **View** heredando de `TenantViewMixin`.
5. Registrar el evento en la **Bitácora** al finalizar la acción con éxito o fallo.
