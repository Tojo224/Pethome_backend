# Tablas y atributos (completo)

Fuentes: `full_db_corrected_complete.puml` + `restore_backup_20260509.sql` (tablas técnicas)

## archivo_clinico
- id_archivo_clinico: AutoField <<PK>> NOT NULL
- id_consulta_clinica: ForeignKey NOT NULL
- nombre_archivo: CharField NOT NULL
- archivo: FileField NOT NULL
- tipo_archivo: CharField NOT NULL
- extension: CharField
- tamano_bytes: BigIntegerField
- descripcion: TextField
- fecha_subida: DateTimeField NOT NULL
- estado: BooleanField NOT NULL

## auth_group
- id: integer NOT NULL
- name: character varying(150) NOT NULL

## auth_group_permissions
- id: bigint NOT NULL
- group_id: integer NOT NULL
- permission_id: integer NOT NULL

## auth_permission
- id: integer NOT NULL
- name: character varying(255) NOT NULL
- content_type_id: integer NOT NULL
- codename: character varying(100) NOT NULL

## backup_config
- id_backup_config: AutoField <<PK>> NOT NULL
- id_veterinaria: OneToOneField NOT NULL
- frecuencia: CharField NOT NULL
- dias_retenciÃ³n: IntegerField NOT NULL
- Ãºltimo_backup: DateTimeField
- prÃ³ximo_backup_programado: DateTimeField
- activo: BooleanField NOT NULL
- creado: DateTimeField NOT NULL
- actualizado: DateTimeField NOT NULL
- hora_ejecucion: IntegerField NOT NULL
- minuto_ejecucion: IntegerField NOT NULL
- dias_semana: ArrayField NOT NULL

## backup_restore
- id_backup_restore: AutoField <<PK>> NOT NULL
- tipo: CharField NOT NULL
- fecha_hora: DateTimeField NOT NULL
- ruta_archivo: CharField NOT NULL
- proveedor_almacenamiento: CharField
- estado: CharField NOT NULL
- hash_archivo: CharField
- motivo: TextField
- id_usuario: ForeignKey NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## billing_demo_event
- id_billing_demo_event: AutoField <<PK>> NOT NULL
- checkout_token: CharField NOT NULL
- event_type: CharField NOT NULL
- status: CharField NOT NULL
- id_plan: ForeignKey NOT NULL
- id_veterinaria: ForeignKey
- id_usuario: ForeignKey
- payload: JSONField NOT NULL
- payment_mode: CharField NOT NULL
- stripe_session_id: CharField
- stripe_payment_intent_id: CharField
- stripe_event_id: CharField
- amount: DecimalField
- currency: CharField
- expires_at: DateTimeField NOT NULL
- confirmed_at: DateTimeField
- created_at: DateTimeField NOT NULL
- updated_at: DateTimeField NOT NULL

## bitacora
- id_bitacora: AutoField <<PK>> NOT NULL
- id_veterinaria: ForeignKey
- fecha_hora: DateTimeField NOT NULL
- payload: BinaryField NOT NULL

## categoria_producto
- id_categoria_producto: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- descripcion: TextField
- estado: BooleanField NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## categorias_servicio
- id_categoria: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- descripcion: TextField
- estado: BooleanField NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## cita
- id_cita: AutoField <<PK>> NOT NULL
- id_usuario: ForeignKey NOT NULL
- id_mascota: ForeignKey NOT NULL
- id_servicio: ForeignKey NOT NULL
- id_precio_servicio: ForeignKey NOT NULL
- fecha_generada: DateTimeField NOT NULL
- fecha_confirmacion: DateTimeField
- fecha_programada: DateField NOT NULL
- hora_inicio: TimeField NOT NULL
- hora_fin: TimeField
- modalidad: CharField NOT NULL
- direccion_cita: TextField
- descripcion: TextField
- estado: CharField NOT NULL
- motivo_cancelacion: TextField
- id_veterinaria: ForeignKey NOT NULL

## componente_sistema
- id_componente: AutoField <<PK>> NOT NULL
- codigo: CharField NOT NULL
- nombre: CharField NOT NULL
- tipo: CharField NOT NULL
- modulo: CharField
- ruta: CharField
- plataforma: CharField NOT NULL
- id_padre: ForeignKey
- orden: IntegerField NOT NULL
- estado: BooleanField NOT NULL

## configuracion_notificacion
- id_configuracion: AutoField <<PK>> NOT NULL
- id_veterinaria: ForeignKey NOT NULL
- tipo_notificacion: CharField NOT NULL
- dias_anticipacion: IntegerField NOT NULL
- canales_habilitados: JSONField NOT NULL
- activo: BooleanField NOT NULL
- fecha_actualizacion: DateTimeField NOT NULL

## consulta_clinica
- id_consulta_clinica: AutoField <<PK>> NOT NULL
- id_historial_clinico: ForeignKey NOT NULL
- id_cita: ForeignKey
- id_usuario_veterinario: ForeignKey NOT NULL
- motivo_consulta: TextField NOT NULL
- diagnostico: TextField
- observaciones: TextField
- fecha_consulta: DateTimeField NOT NULL
- peso: DecimalField
- temperatura: DecimalField
- frecuencia_cardiaca: PositiveIntegerField
- frecuencia_respiratoria: PositiveIntegerField
- proxima_revision: DateTimeField
- fecha_creacion: DateTimeField NOT NULL
- fecha_actualizacion: DateTimeField NOT NULL
- estado: BooleanField NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## detalle_pedido
- id_detalle_pedido: BigAutoField <<PK>> NOT NULL
- pedido_id: ForeignKey NOT NULL
- producto_id: ForeignKey NOT NULL
- cantidad: PositiveIntegerField NOT NULL
- precio_unitario: DecimalField NOT NULL
- subtotal: DecimalField NOT NULL
- observacion: TextField
- estado: BooleanField NOT NULL

## detalle_receta
- id_detalle_receta: AutoField <<PK>> NOT NULL
- id_receta: ForeignKey NOT NULL
- id_producto: ForeignKey
- medicamento: CharField NOT NULL
- dosis: CharField NOT NULL
- frecuencia: CharField NOT NULL
- duracion_dias: PositiveIntegerField NOT NULL
- indicaciones_adicionales: TextField

## detalle_ruta
- id_detalle_ruta: AutoField <<PK>> NOT NULL
- id_ruta: ForeignKey NOT NULL
- id_cita: ForeignKey NOT NULL
- orden: IntegerField NOT NULL
- hora_estimada: TimeField
- estado: CharField NOT NULL

## dispositivo_usuario
- id_dispositivo: AutoField <<PK>> NOT NULL
- id_usuario: ForeignKey NOT NULL
- id_veterinaria: ForeignKey
- token_fcm: TextField NOT NULL
- plataforma: CharField NOT NULL
- activo: BooleanField NOT NULL
- fecha_registro: DateTimeField NOT NULL
- ultima_conexion: DateTimeField NOT NULL

## django_admin_log
- id: integer NOT NULL
- action_time: timestamp with time zone NOT NULL
- object_id: text
- object_repr: character varying(200) NOT NULL
- action_flag: smallint NOT NULL
- change_message: text NOT NULL
- content_type_id: integer
- user_id: integer NOT NULL

## django_content_type
- id: integer NOT NULL
- app_label: character varying(100) NOT NULL
- model: character varying(100) NOT NULL

## django_migrations
- id: bigint NOT NULL
- app: character varying(255) NOT NULL
- name: character varying(255) NOT NULL
- applied: timestamp with time zone NOT NULL

## django_session
- session_key: character varying(40) NOT NULL
- session_data: text NOT NULL
- expire_date: timestamp with time zone NOT NULL

## especie
- id_especie: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL

## grupo_permiso_componente
- id_permiso_componente: AutoField <<PK>> NOT NULL
- puede_ver: BooleanField NOT NULL
- puede_crear: BooleanField NOT NULL
- puede_editar: BooleanField NOT NULL
- puede_eliminar: BooleanField NOT NULL
- puede_exportar: BooleanField NOT NULL
- puede_ejecutar: BooleanField NOT NULL
- estado: BooleanField NOT NULL
- id_grupo: ForeignKey NOT NULL
- id_componente: ForeignKey NOT NULL

## grupo_usuario
- id_grupo: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- descripcion: TextField
- estado: BooleanField NOT NULL
- es_base: BooleanField NOT NULL
- rol_base: CharField
- fecha_creacion: DateTimeField NOT NULL
- id_veterinaria: ForeignKey

## historial_clinico
- id_historial_clinico: AutoField <<PK>> NOT NULL
- id_mascota: OneToOneField NOT NULL
- observaciones_generales: TextField
- fecha_creacion: DateTimeField NOT NULL
- fecha_actualizacion: DateTimeField NOT NULL
- estado: BooleanField NOT NULL

## mascota
- id_mascota: AutoField <<PK>> NOT NULL
- id_usuario: ForeignKey NOT NULL
- id_especie: ForeignKey NOT NULL
- id_raza: ForeignKey
- id_veterinaria: ForeignKey NOT NULL
- nombre: CharField NOT NULL
- color: CharField
- sexo: CharField
- fecha_nac: DateField
- tamano: CharField
- peso: DecimalField
- foto: CharField
- alergias: TextField
- notas_generales: TextField
- fecha_registro: DateTimeField NOT NULL
- estado: BooleanField NOT NULL

## movimiento_inventario
- id_movimiento: AutoField <<PK>>
- id_veterinaria: ForeignKey NOT NULL
- id_producto: ForeignKey NOT NULL
- id_usuario: ForeignKey NOT NULL
- id_punto_origen: ForeignKey
- id_punto_destino: ForeignKey
- tipo: CharField NOT NULL
- cantidad: DecimalField NOT NULL
- cantidad_anterior: DecimalField NOT NULL
- cantidad_posterior: DecimalField NOT NULL
- motivo: TextField
- fecha_movimiento: DateTimeField NOT NULL
- id_cita: ForeignKey

## notificacion
- id_notificacion: AutoField <<PK>> NOT NULL
- id_usuario: ForeignKey NOT NULL
- id_veterinaria: ForeignKey NOT NULL
- titulo: CharField NOT NULL
- mensaje: TextField NOT NULL
- tipo: CharField NOT NULL
- estado: CharField NOT NULL
- id_entidad_relacionada: IntegerField
- fecha_creacion: DateTimeField NOT NULL
- fecha_envio: DateTimeField
- fecha_leida: DateTimeField
- link: CharField

## password_reset_tokens
- id_password_reset_token: BigAutoField <<PK>> NOT NULL
- usuario_id: ForeignKey NOT NULL
- token: CharField NOT NULL
- expiracion: DateTimeField NOT NULL
- usado: BooleanField NOT NULL
- fecha_creacion: DateTimeField NOT NULL

## pedido
- id_pedido: BigAutoField <<PK>> NOT NULL
- usuario_id: ForeignKey NOT NULL
- veterinaria_id: ForeignKey NOT NULL
- fecha_pedido: DateTimeField NOT NULL
- direccion_entrega: TextField
- tipo_entrega: CharField NOT NULL
- estado_pedido: CharField NOT NULL
- subtotal: DecimalField NOT NULL
- costo_envio: DecimalField NOT NULL
- total: DecimalField NOT NULL
- observacion: TextField
- motivo_cancelacion: TextField
- fecha_creacion: DateTimeField NOT NULL
- fecha_actualizacion: DateTimeField NOT NULL
- estado: BooleanField NOT NULL

## perfil
- id_perfil: AutoField <<PK>> NOT NULL
- id_usuario: OneToOneField NOT NULL
- nombre: CharField NOT NULL
- telefono: CharField
- direccion: CharField
- estado: BooleanField NOT NULL
- fecha_creacion: DateTimeField NOT NULL

## plan_suscripcion
- id_plan: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- descripcion: TextField
- precio_mensual: DecimalField NOT NULL
- limite_usuarios: IntegerField NOT NULL
- limite_mascotas: IntegerField NOT NULL
- permite_app_movil: BooleanField NOT NULL
- permite_reportes: BooleanField NOT NULL
- permite_backup: BooleanField NOT NULL
- estado: BooleanField NOT NULL

## precios_servicio
- id_precio: AutoField <<PK>> NOT NULL
- servicio_id: ForeignKey NOT NULL
- variacion: CharField NOT NULL
- modalidad: CharField
- precio: DecimalField NOT NULL
- descripcion: TextField
- estado: BooleanField NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## producto
- id_producto: AutoField <<PK>> NOT NULL
- id_categoria_producto: ForeignKey NOT NULL
- id_proveedor: ForeignKey
- nombre: CharField NOT NULL
- descripcion: TextField
- precio_compra: DecimalField
- precio_venta: DecimalField
- unidad_medida: CharField
- imagen: FileField
- visible_catalogo: BooleanField NOT NULL
- estado: BooleanField NOT NULL
- tipo_mascota: CharField
- destacado: BooleanField NOT NULL
- novedad_desde: DateField
- novedad_hasta: DateField
- tiene_promocion: BooleanField NOT NULL
- tipo_descuento: CharField
- porcentaje_descuento: DecimalField
- monto_descuento: DecimalField
- precio_promocional: DecimalField
- promocion_fecha_inicio: DateField
- promocion_fecha_fin: DateField
- id_veterinaria: ForeignKey NOT NULL

## proveedor
- id_proveedor: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- contacto: CharField
- telefono: CharField
- ubicacion: TextField
- estado: BooleanField NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## punto_inventario
- id_punto: AutoField <<PK>>
- id_veterinaria: ForeignKey NOT NULL
- tipo: CharField NOT NULL
- nombre: CharField NOT NULL
- direccion: TextField
- telefono: CharField
- encargado: CharField
- descripcion: TextField
- estado: BooleanField NOT NULL
- fecha_creacion: DateTimeField NOT NULL

## raza
- id_raza: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- id_especie: ForeignKey NOT NULL

## receta
- id_receta: AutoField <<PK>> NOT NULL
- id_consulta_clinica: OneToOneField NOT NULL
- fecha: DateTimeField NOT NULL
- indicaciones: TextField
- observacion: TextField
- estado: BooleanField NOT NULL
- fecha_creacion: DateTimeField NOT NULL
- fecha_actualizacion: DateTimeField NOT NULL

## roles
- id_rol: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- descripcion: TextField

## ruta_programada
- id_ruta: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- fecha: DateField NOT NULL
- estado: CharField NOT NULL
- id_unidad: ForeignKey NOT NULL
- id_veterinario: ForeignKey NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## seguimiento
- id_seguimiento: BigAutoField <<PK>> NOT NULL
- veterinaria_id: ForeignKey NOT NULL
- usuario_id: ForeignKey
- cita_id: ForeignKey
- pedido_id: ForeignKey
- tipo_seguimiento: CharField NOT NULL
- estado_anterior: CharField
- estado_actual: CharField NOT NULL
- descripcion: TextField
- fecha_hora: DateTimeField NOT NULL
- visible_cliente: BooleanField NOT NULL
- estado: BooleanField NOT NULL

## servicios
- id_servicio: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- descripcion: TextField
- id_categoria: ForeignKey NOT NULL
- duracion_estimada: IntegerField
- disponible_domicilio: BooleanField NOT NULL
- estado: BooleanField NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## stock_punto
- id_stock: AutoField <<PK>>
- id_veterinaria: ForeignKey NOT NULL
- id_punto: ForeignKey NOT NULL
- id_producto: ForeignKey NOT NULL
- cantidad: DecimalField NOT NULL
- cantidad_minima: DecimalField NOT NULL
- UNIQUE(id_punto,id_producto)

## suscripcion
- id_suscripcion: AutoField <<PK>> NOT NULL
- fecha_inicio: DateField NOT NULL
- fecha_fin: DateField
- estado_suscripcion: CharField NOT NULL
- renovacion_automatica: BooleanField NOT NULL
- fecha_creacion: DateTimeField NOT NULL
- fecha_actualizacion: DateTimeField NOT NULL
- metodo_pago: CharField
- fecha_pago: DateTimeField
- id_veterinaria: ForeignKey NOT NULL
- id_plan: ForeignKey NOT NULL

## token_blacklist_blacklistedtoken
- id: BigAutoField <<PK>> NOT NULL
- token_id: OneToOneField NOT NULL
- blacklisted_at: DateTimeField NOT NULL

## token_blacklist_outstandingtoken
- id: BigAutoField <<PK>> NOT NULL
- user_id: ForeignKey
- jti: CharField NOT NULL
- token: TextField NOT NULL
- created_at: DateTimeField
- expires_at: DateTimeField NOT NULL

## tratamiento
- id_tratamiento: AutoField <<PK>> NOT NULL
- id_consulta_clinica: ForeignKey NOT NULL
- tipo: CharField NOT NULL
- descripcion: TextField NOT NULL
- fecha_ini: DateField NOT NULL
- fecha_fin: DateField
- observacion: TextField
- estado_tratamiento: CharField NOT NULL
- estado: BooleanField NOT NULL
- fecha_creacion: DateTimeField NOT NULL
- fecha_actualizacion: DateTimeField NOT NULL

## unidad_movil
- id_unidad: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- placa: CharField
- descripcion: TextField
- estado: BooleanField NOT NULL
- id_veterinaria: ForeignKey NOT NULL

## unidad_movil_asignacion
- id_asignacion: AutoField <<PK>> NOT NULL
- id_unidad: ForeignKey NOT NULL
- id_veterinaria: ForeignKey NOT NULL
- zona_nombre: CharField NOT NULL
- zona_descripcion: TextField
- zona_geojson: JSONField
- fecha_inicio: DateField NOT NULL
- fecha_fin: DateField
- hora_inicio: TimeField
- hora_fin: TimeField
- estado: BooleanField NOT NULL
- created_at: DateTimeField NOT NULL
- updated_at: DateTimeField NOT NULL

## unidad_movil_asignacion_personal
- id_asignacion_personal: AutoField <<PK>> NOT NULL
- id_asignacion: ForeignKey NOT NULL
- id_usuario: ForeignKey NOT NULL
- rol_operativo: CharField NOT NULL
- es_responsable: BooleanField NOT NULL
- estado: BooleanField NOT NULL
- created_at: DateTimeField NOT NULL
- updated_at: DateTimeField NOT NULL

## unidad_movil_punto
- id_unidad_movil: ForeignKey <<PK>>
- id_punto: ForeignKey UNIQUE NOT NULL

## usuario_grupo
- id_usuario_grupo: AutoField <<PK>> NOT NULL
- fecha_asignacion: DateTimeField NOT NULL
- estado: BooleanField NOT NULL
- id_usuario: ForeignKey NOT NULL
- id_grupo: ForeignKey NOT NULL

## usuarios
- password: CharField NOT NULL
- last_login: DateTimeField
- is_superuser: BooleanField NOT NULL
- id_usuario: AutoField <<PK>> NOT NULL
- correo: CharField NOT NULL
- id_rol: ForeignKey NOT NULL
- id_veterinaria: ForeignKey
- is_active: BooleanField NOT NULL
- is_staff: BooleanField NOT NULL
- date_joined: DateTimeField NOT NULL
- intentos_fallidos: PositiveSmallIntegerField NOT NULL
- bloqueado_hasta: DateTimeField
- groups: ManyToManyField NOT NULL
- user_permissions: ManyToManyField NOT NULL

## usuarios_groups
- id: bigint NOT NULL
- user_id: integer NOT NULL
- group_id: integer NOT NULL

## usuarios_user_permissions
- id: bigint NOT NULL
- user_id: integer NOT NULL
- permission_id: integer NOT NULL

## vacuna_aplicada
- id_vacuna_aplicada: AutoField <<PK>> NOT NULL
- id_consulta_clinica: ForeignKey NOT NULL
- nombre_vacuna: CharField NOT NULL
- dosis: CharField
- fecha_aplicada: DateField NOT NULL
- fecha_proxima: DateField
- observacion: TextField
- lote: CharField
- fabricante: CharField
- estado_vacuna: CharField NOT NULL
- estado: BooleanField NOT NULL
- fecha_creacion: DateTimeField NOT NULL

## veterinaria
- id_veterinaria: AutoField <<PK>> NOT NULL
- nombre: CharField NOT NULL
- slug: SlugField NOT NULL
- nit: CharField
- correo: CharField
- telefono: CharField
- direccion: TextField
- logo: CharField
- estado: BooleanField NOT NULL
- permite_auto_registro_clientes: BooleanField NOT NULL
- fecha_creacion: DateTimeField NOT NULL
- owner_user_id: ForeignKey

