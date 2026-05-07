from django.db import transaction
from rest_framework import serializers
from ..models.mascota import Mascota
from apps.AutenticacionySeguridad.selectors.perfil_selector import SuscripcionSelector

class MascotaService:
    @staticmethod
    @transaction.atomic
    def crear_mascota(
        *,
        veterinaria_id,
        usuario,
        especie,
        raza,
        nombre,
        sexo,
        fecha_nac=None,
        peso=None,
        color=None,
        notas_generales=None
    ):
        """
        Crea una mascota validando los límites del plan de la veterinaria.
        """
        # --- VALIDACIÓN DE LÍMITE DE MASCOTAS (SaaS) ---
        suscripcion = SuscripcionSelector.get_suscripcion_activa(veterinaria_id)
        
        if suscripcion and suscripcion.plan:
            limite = suscripcion.plan.limite_mascotas
            if limite > 0:
                conteo_actual = Mascota.objects.filter(veterinaria_id=veterinaria_id).count()
                if conteo_actual >= limite:
                    raise serializers.ValidationError({
                        "detail": f"Se ha alcanzado el límite de mascotas permitidas para su plan ({limite}).",
                        "code": "LIMITE_MASCOTAS_ALCANZADO"
                    })
        # -----------------------------------------------

        mascota = Mascota.objects.create(
            veterinaria_id=veterinaria_id,
            usuario=usuario,
            especie=especie,
            raza=raza,
            nombre=nombre,
            sexo=sexo,
            fecha_nac=fecha_nac,
            peso=peso,
            color=color,
            notas_generales=notas_generales,
        )
        return mascota

    @staticmethod
    @transaction.atomic
    def actualizar_mascota(mascota, **data):
        for field, value in data.items():
            setattr(mascota, field, value)
        mascota.save()
        return mascota

    @staticmethod
    @transaction.atomic
    def eliminar_mascota(mascota):
        # En lugar de eliminar físicamente, podríamos marcar como inactivo si el modelo lo permite
        # Pero por ahora seguimos el comportamiento estándar del proyecto
        mascota.delete()
