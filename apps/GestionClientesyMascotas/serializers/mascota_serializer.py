from rest_framework import serializers
from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionClientesyMascotas.models.mascota import Mascota
from apps.GestionClientesyMascotas.models.especie import Especie
from apps.GestionClientesyMascotas.models.raza import Raza
from apps.AutenticacionySeguridad.models.user import User


class UsuarioMiniSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id_usuario", "correo", "nombre"]

    def get_nombre(self, obj) -> str:
        if hasattr(obj, "perfil") and obj.perfil:
            return obj.perfil.nombre
        return obj.correo


class UsuarioChoiceField(serializers.PrimaryKeyRelatedField):
    def display_value(self, instance):
        if hasattr(instance, "perfil") and instance.perfil:
            return instance.perfil.nombre
        return f"Usuario {instance.id_usuario}"


class EspecieMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especie
        fields = ["id_especie", "nombre"]


class RazaMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Raza
        fields = ["id_raza", "nombre"]


class MascotaSerializer(serializers.ModelSerializer):
    usuario = UsuarioMiniSerializer(read_only=True)
    especie = EspecieMiniSerializer(read_only=True)
    raza = RazaMiniSerializer(read_only=True)

    usuario_id = UsuarioChoiceField(
        queryset=User.objects.filter(
            role__nombre=RoleEnum.CLIENT.value,
            is_active=True
        ).select_related("perfil"),
        source="usuario",
        write_only=True,
        required=False
    )
    especie_id = serializers.PrimaryKeyRelatedField(
        queryset=Especie.objects.all(),
        source="especie",
        write_only=True
    )
    raza_id = serializers.PrimaryKeyRelatedField(
        queryset=Raza.objects.all(),
        source="raza",
        write_only=True,
        allow_null=True,
        required=False
    )

    class Meta:
        model = Mascota
        fields = [
            "id_mascota",
            "nombre",
            "color",
            "sexo",
            "fecha_nac",
            "tamano",
            "peso",
            "foto",
            "alergias",
            "notas_generales",
            "fecha_registro",
            "estado",
            "usuario",
            "especie",
            "raza",
            "usuario_id",
            "especie_id",
            "raza_id",
        ]
        read_only_fields = ["id_mascota", "fecha_registro"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        tenant_id = getattr(tenant, "id", None)
        if tenant_id is not None:
            self.fields["usuario_id"].queryset = (
                User.objects.filter(
                    role__nombre=RoleEnum.CLIENT.value,
                    is_active=True,
                    veterinaria_id=tenant_id,
                ).select_related("perfil")
            )

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        especie = attrs.get("especie")
        raza = attrs.get("raza")

        if (
            not self.instance
            and user
            and getattr(user, "is_authenticated", False)
            and getattr(getattr(user, "role", None), "nombre", None) == RoleEnum.CLIENT.value
        ):
            attrs["usuario"] = user

        if self.instance:
            if especie is None:
                especie = self.instance.especie
            if raza is None:
                raza = self.instance.raza

        if raza and especie and raza.especie_id != especie.id_especie:
            raise serializers.ValidationError({
                "raza_id": "La raza seleccionada no pertenece a la especie indicada."
            })

        return attrs
