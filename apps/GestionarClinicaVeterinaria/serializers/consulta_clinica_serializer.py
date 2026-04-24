from rest_framework import serializers
from apps.AutenticacionySeguridad.models.user import User
from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionarClinicaVeterinaria.models import ConsultaClinica
from apps.GestionarClinicaVeterinaria.serializers.tratamiento_serializer import TratamientoSerializer
from apps.GestionarClinicaVeterinaria.serializers.receta_serializer import RecetaSerializer
from apps.GestionarClinicaVeterinaria.serializers.vacuna_aplicada_serializer import VacunaAplicadaSerializer
from apps.GestionarClinicaVeterinaria.serializers.archivo_clinico_serializer import ArchivoClinicoSerializer


class VeterinarioRelatedField(serializers.PrimaryKeyRelatedField):
    def display_value(self, instance):
        if hasattr(instance, "perfil") and instance.perfil and instance.perfil.nombre:
            return instance.perfil.nombre
        return instance.correo


class ConsultaClinicaSerializer(serializers.ModelSerializer):
    usuario_veterinario = VeterinarioRelatedField(
        queryset=User.objects.filter(
            role__nombre=RoleEnum.VETERINARIAN.value,
            is_active=True,
        )
    )

    tratamientos = TratamientoSerializer(many=True, read_only=True)
    receta = RecetaSerializer(read_only=True)
    vacunas_aplicadas = VacunaAplicadaSerializer(many=True, read_only=True)
    archivos_clinicos = ArchivoClinicoSerializer(many=True, read_only=True)

    veterinario_nombre = serializers.CharField(
        source="usuario_veterinario.perfil.nombre",
        read_only=True,
    )
    mascota_nombre = serializers.CharField(
        source="historial_clinico.mascota.nombre",
        read_only=True,
    )
    propietario_id = serializers.IntegerField(
        source="historial_clinico.mascota.usuario.id_usuario",
        read_only=True,
    )
    propietario_nombre = serializers.CharField(
        source="historial_clinico.mascota.usuario.perfil.nombre",
        read_only=True,
    )

    class Meta:
        model = ConsultaClinica
        fields = [
            "id_consulta_clinica",
            "historial_clinico",
            "cita",
            "usuario_veterinario",
            "veterinario_nombre",
            "mascota_nombre",
            "propietario_id",
            "propietario_nombre",
            "motivo_consulta",
            "diagnostico",
            "observaciones",
            "fecha_consulta",
            "peso",
            "temperatura",
            "frecuencia_cardiaca",
            "frecuencia_respiratoria",
            "proxima_revision",
            "fecha_creacion",
            "fecha_actualizacion",
            "estado",
            "tratamientos",
            "receta",
            "vacunas_aplicadas",
            "archivos_clinicos",
        ]
        read_only_fields = [
            "id_consulta_clinica",
            "historial_clinico",
            "veterinario_nombre",
            "mascota_nombre",
            "propietario_id",
            "propietario_nombre",
            "fecha_creacion",
            "fecha_actualizacion",
            "tratamientos",
            "receta",
            "vacunas_aplicadas",
            "archivos_clinicos",
        ]
        extra_kwargs = {
            "cita": {"required": False, "allow_null": True},
            "diagnostico": {"required": False, "allow_null": True},
            "observaciones": {"required": False, "allow_null": True},
            "peso": {"required": False, "allow_null": True},
            "temperatura": {"required": False, "allow_null": True},
            "frecuencia_cardiaca": {"required": False, "allow_null": True},
            "frecuencia_respiratoria": {"required": False, "allow_null": True},
            "proxima_revision": {"required": False, "allow_null": True},
            "estado": {"required": False},
        }