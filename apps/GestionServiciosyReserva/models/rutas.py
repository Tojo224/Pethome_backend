from django.conf import settings
from django.db import models


class UnidadMovil(models.Model):
    id_unidad = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    placa = models.CharField(max_length=20, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="unidades_moviles",
    )

    class Meta:
        db_table = "unidad_movil"
        verbose_name = "Unidad movil"
        verbose_name_plural = "Unidades moviles"
        ordering = ["nombre", "id_unidad"]

    def __str__(self):
        return self.nombre


class RutaProgramada(models.Model):
    class EstadoChoices(models.TextChoices):
        PROGRAMADA = "PROGRAMADA", "Programada"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        FINALIZADA = "FINALIZADA", "Finalizada"
        CANCELADA = "CANCELADA", "Cancelada"

    id_ruta = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    fecha = models.DateField()
    estado = models.CharField(
        max_length=30,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PROGRAMADA,
    )
    unidad = models.ForeignKey(
        "GestionServiciosyReserva.UnidadMovil",
        db_column="id_unidad",
        on_delete=models.PROTECT,
        related_name="rutas_programadas",
    )
    veterinario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_veterinario",
        on_delete=models.PROTECT,
        related_name="rutas_programadas",
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="rutas_programadas",
    )

    class Meta:
        db_table = "ruta_programada"
        verbose_name = "Ruta programada"
        verbose_name_plural = "Rutas programadas"
        ordering = ["fecha", "id_ruta"]

    def __str__(self):
        return f"{self.nombre} - {self.fecha}"


class DetalleRuta(models.Model):
    class EstadoChoices(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_CAMINO = "EN_CAMINO", "En camino"
        ATENDIENDO = "ATENDIENDO", "Atendiendo"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"
        INCIDENCIA = "INCIDENCIA", "Incidencia"

    id_detalle_ruta = models.AutoField(primary_key=True)
    ruta = models.ForeignKey(
        "GestionServiciosyReserva.RutaProgramada",
        db_column="id_ruta",
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    cita = models.ForeignKey(
        "GestionServiciosyReserva.Cita",
        db_column="id_cita",
        on_delete=models.CASCADE,
        related_name="detalles_ruta",
    )
    orden = models.IntegerField()
    hora_estimada = models.TimeField(blank=True, null=True)
    estado = models.CharField(
        max_length=30,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PENDIENTE,
    )

    class Meta:
        db_table = "detalle_ruta"
        verbose_name = "Detalle de ruta"
        verbose_name_plural = "Detalles de ruta"
        ordering = ["orden", "id_detalle_ruta"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruta", "cita"],
                name="uq_detalle_ruta_cita_por_ruta",
            ),
            models.UniqueConstraint(
                fields=["ruta", "orden"],
                name="uq_detalle_ruta_orden_por_ruta",
            ),
        ]

    def __str__(self):
        return f"Ruta {self.ruta_id} - Cita {self.cita_id}"


class UnidadMovilAsignacion(models.Model):
    id_asignacion = models.AutoField(primary_key=True)
    unidad = models.ForeignKey(
        "GestionServiciosyReserva.UnidadMovil",
        db_column="id_unidad",
        on_delete=models.CASCADE,
        related_name="asignaciones_logisticas",
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="asignaciones_logisticas",
    )
    zona_nombre = models.CharField(max_length=120)
    zona_descripcion = models.TextField(blank=True, null=True)
    zona_geojson = models.JSONField(blank=True, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    hora_inicio = models.TimeField(blank=True, null=True)
    hora_fin = models.TimeField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "unidad_movil_asignacion"
        verbose_name = "Asignacion de unidad movil"
        verbose_name_plural = "Asignaciones de unidad movil"
        ordering = ["-fecha_inicio", "id_asignacion"]

    def __str__(self):
        return f"{self.unidad.nombre} - {self.zona_nombre}"


class UnidadMovilAsignacionPersonal(models.Model):
    class RolOperativoChoices(models.TextChoices):
        VETERINARIO = "VETERINARIO", "Veterinario"
        CHOFER = "CHOFER", "Chofer"
        AUXILIAR = "AUXILIAR", "Auxiliar"
        APOYO = "APOYO", "Apoyo"

    id_asignacion_personal = models.AutoField(primary_key=True)
    asignacion = models.ForeignKey(
        "GestionServiciosyReserva.UnidadMovilAsignacion",
        db_column="id_asignacion",
        on_delete=models.CASCADE,
        related_name="personal_asignado",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario",
        on_delete=models.PROTECT,
        related_name="asignaciones_unidad_movil",
    )
    rol_operativo = models.CharField(
        max_length=30,
        choices=RolOperativoChoices.choices,
        default=RolOperativoChoices.VETERINARIO,
    )
    es_responsable = models.BooleanField(default=False)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "unidad_movil_asignacion_personal"
        verbose_name = "Personal asignado a unidad movil"
        verbose_name_plural = "Personal asignado a unidades moviles"
        ordering = ["id_asignacion_personal"]
        constraints = [
            models.UniqueConstraint(
                fields=["asignacion", "usuario"],
                name="uq_asignacion_personal_usuario",
            ),
        ]

    def __str__(self):
        return f"{self.usuario_id} en asignacion {self.asignacion_id}"
