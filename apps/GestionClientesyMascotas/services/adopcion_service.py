from django.db import transaction

from apps.GestionClientesyMascotas.models.adopcion import Adopcion


class AdopcionService:
    @staticmethod
    @transaction.atomic
    def crear_adopcion(*, veterinaria_id, usuario, **data):
        data.pop("estado_adopcion", None)
        return Adopcion.objects.create(
            veterinaria_id=veterinaria_id,
            usuario=usuario,
            estado_adopcion=Adopcion.ESTADO_DISPONIBLE,
            **data,
        )

    @staticmethod
    @transaction.atomic
    def actualizar_adopcion(adopcion, **data):
        for field, value in data.items():
            setattr(adopcion, field, value)
        adopcion.save()
        return adopcion

    @staticmethod
    @transaction.atomic
    def desactivar_adopcion(adopcion):
        adopcion.estado_adopcion = Adopcion.ESTADO_INACTIVO
        adopcion.save(update_fields=["estado_adopcion", "fecha_actualizacion"])
        return adopcion
