from rest_framework import serializers
from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionClientesyMascotas.models.mascota import Mascota
from apps.GestionServiciosyReserva.models.especie import Especie
from apps.GestionServiciosyReserva.models.raza import Raza
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

    def to_internal_value(self, data):
        """
        Acepta variantes de nombres de campos que puede enviar frontend móvil
        sin romper el contrato actual del backend.
        """
        mutable = dict(data)

        # Alias para especie/raza (móvil suele enviar snake/camel en inglés)
        if "especie_id" not in mutable:
            if "species_id" in mutable:
                mutable["especie_id"] = mutable.get("species_id")
            elif "speciesId" in mutable:
                mutable["especie_id"] = mutable.get("speciesId")
            elif "especie" in mutable and isinstance(mutable.get("especie"), int):
                mutable["especie_id"] = mutable.get("especie")

        if "raza_id" not in mutable:
            if "breed_id" in mutable:
                mutable["raza_id"] = mutable.get("breed_id")
            elif "breedId" in mutable:
                mutable["raza_id"] = mutable.get("breedId")
            elif "raza" in mutable and isinstance(mutable.get("raza"), int):
                mutable["raza_id"] = mutable.get("raza")

        # Alias de fecha de nacimiento
        if "fecha_nac" not in mutable:
            if "fechaNacimiento" in mutable:
                mutable["fecha_nac"] = mutable.get("fechaNacimiento")
            elif "birth_date" in mutable:
                mutable["fecha_nac"] = mutable.get("birth_date")

        # Normalizar sexo para evitar 400 por mayúsculas/minúsculas o etiquetas UI
        if "sexo" in mutable and mutable.get("sexo") not in (None, ""):
            sexo_val = str(mutable.get("sexo")).strip().upper()
            if sexo_val in {"M", "MACHO", "MALE"}:
                mutable["sexo"] = "MACHO"
            elif sexo_val in {"H", "HEMBRA", "F", "FEMALE"}:
                mutable["sexo"] = "HEMBRA"

        # Normalizar vacíos en opcionales para evitar 400 por tipo inválido
        optional_nullable_fields = [
            "raza_id",
            "sexo",
            "fecha_nac",
            "peso",
            "tamano",
            "foto",
            "color",
            "alergias",
            "notas_generales",
        ]
        for field in optional_nullable_fields:
            if field in mutable and mutable[field] == "":
                mutable[field] = None

        # `estado` no acepta null en modelo. Si móvil lo manda null/vacío, usar True por defecto.
        if "estado" in mutable:
            estado_val = mutable.get("estado")
            if estado_val in ("", None, "null", "None"):
                mutable["estado"] = True
            elif isinstance(estado_val, str):
                norm = estado_val.strip().lower()
                if norm in {"true", "1", "si", "sí", "yes"}:
                    mutable["estado"] = True
                elif norm in {"false", "0", "no"}:
                    mutable["estado"] = False

        return super().to_internal_value(mutable)

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
