from rest_framework import serializers

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models.user import User
from apps.GestionClientesyMascotas.models.adopcion import Adopcion
from apps.GestionClientesyMascotas.serializers.mascota_serializer import (
    EspecieMiniSerializer,
    RazaMiniSerializer,
    UsuarioChoiceField,
    UsuarioMiniSerializer,
)
from apps.GestionServiciosyReserva.models.especie import Especie
from apps.GestionServiciosyReserva.models.raza import Raza


class AdopcionSerializer(serializers.ModelSerializer):
    usuario = UsuarioMiniSerializer(read_only=True)
    especie = EspecieMiniSerializer(read_only=True)
    raza = RazaMiniSerializer(read_only=True)
    puede_editar = serializers.SerializerMethodField()
    telefono_contacto = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    referencia_ubicacion = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    latitud = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitud = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    estado_adopcion = serializers.CharField(required=False, allow_null=True)

    usuario_id = UsuarioChoiceField(
        queryset=User.objects.filter(
            role__nombre=RoleEnum.CLIENT.value,
            is_active=True,
        ).select_related("perfil"),
        source="usuario",
        write_only=True,
        required=False,
    )
    especie_id = serializers.PrimaryKeyRelatedField(
        queryset=Especie.objects.all(),
        source="especie",
        write_only=True,
    )
    raza_id = serializers.PrimaryKeyRelatedField(
        queryset=Raza.objects.all(),
        source="raza",
        write_only=True,
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Adopcion
        fields = [
            "id_adopcion",
            "nombre",
            "foto",
            "edad_aproximada",
            "sexo",
            "tamano",
            "ubicacion",
            "telefono_contacto",
            "referencia_ubicacion",
            "latitud",
            "longitud",
            "estado_adopcion",
            "descripcion",
            "estado_salud",
            "fecha_publicacion",
            "fecha_actualizacion",
            "usuario",
            "especie",
            "raza",
            "puede_editar",
            "usuario_id",
            "especie_id",
            "raza_id",
        ]
        read_only_fields = [
            "id_adopcion",
            "fecha_publicacion",
            "fecha_actualizacion",
            "puede_editar",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["foto"] = self._resolve_media_url(data.get("foto"))
        return data

    def _resolve_media_url(self, value):
        if not value:
            return value
        if str(value).startswith(("http://", "https://")):
            return value
        path = value if str(value).startswith("/") else f"/{value}"
        request = self.context.get("request")
        if request:
            try:
                return request.build_absolute_uri(path)
            except Exception:
                pass
        return path

    def get_puede_editar(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        return (
            getattr(user, "is_superuser", False)
            or role_name in {RoleEnum.ADMIN.value, RoleEnum.VETERINARIAN.value}
            or obj.usuario_id == getattr(user, "id_usuario", None)
        )

    def to_internal_value(self, data):
        mutable = dict(data)

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

        if "estado" in mutable and "estado_adopcion" not in mutable:
            mutable["estado_adopcion"] = mutable.get("estado")
        if "edad" in mutable and "edad_aproximada" not in mutable:
            mutable["edad_aproximada"] = mutable.get("edad")
        if "estadoSalud" in mutable and "estado_salud" not in mutable:
            mutable["estado_salud"] = mutable.get("estadoSalud")
        if "telefonoContacto" in mutable and "telefono_contacto" not in mutable:
            mutable["telefono_contacto"] = mutable.get("telefonoContacto")
        if "referenciaUbicacion" in mutable and "referencia_ubicacion" not in mutable:
            mutable["referencia_ubicacion"] = mutable.get("referenciaUbicacion")
        if "latitude" in mutable and "latitud" not in mutable:
            mutable["latitud"] = mutable.get("latitude")
        if "longitude" in mutable and "longitud" not in mutable:
            mutable["longitud"] = mutable.get("longitude")
        if "coordinates" in mutable and ("latitud" not in mutable or "longitud" not in mutable):
            raw_coordinates = str(mutable.get("coordinates") or "")
            parts = [part.strip() for part in raw_coordinates.split(",")]
            if len(parts) == 2:
                mutable.setdefault("latitud", parts[0])
                mutable.setdefault("longitud", parts[1])

        if "sexo" in mutable and mutable.get("sexo") not in (None, ""):
            sexo_val = str(mutable.get("sexo")).strip().upper()
            if sexo_val in {"M", "MACHO", "MALE"}:
                mutable["sexo"] = "MACHO"
            elif sexo_val in {"H", "HEMBRA", "F", "FEMALE"}:
                mutable["sexo"] = "HEMBRA"

        if "tamano" in mutable and mutable.get("tamano") not in (None, ""):
            size_val = str(mutable.get("tamano")).strip().lower()
            size_map = {
                "pequeno": "Pequeno",
                "small": "Pequeno",
                "mediano": "Mediano",
                "medium": "Mediano",
                "grande": "Grande",
                "large": "Grande",
            }
            mutable["tamano"] = size_map.get(size_val, mutable.get("tamano"))

        for field in [
            "raza_id",
            "foto",
            "edad_aproximada",
            "sexo",
            "tamano",
            "telefono_contacto",
            "referencia_ubicacion",
            "latitud",
            "longitud",
        ]:
            if field in mutable and mutable[field] == "":
                mutable[field] = None

        return super().to_internal_value(mutable)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        tenant_id = getattr(tenant, "id", None)
        if tenant_id is None and request:
            tenant_id = getattr(getattr(request, "user", None), "veterinaria_id", None)
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
        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        especie = attrs.get("especie")
        raza = attrs.get("raza")

        if self.instance:
            especie = especie or self.instance.especie
            raza = raza if "raza" in attrs else self.instance.raza

        if raza and especie and raza.especie_id != especie.id_especie:
            raise serializers.ValidationError({
                "raza_id": "La raza seleccionada no pertenece a la especie indicada."
            })

        if not self.instance:
            if user and getattr(user, "is_authenticated", False):
                if role_name == RoleEnum.CLIENT.value or not attrs.get("usuario"):
                    attrs["usuario"] = user
            attrs["estado_adopcion"] = Adopcion.ESTADO_DISPONIBLE

        latitud = attrs.get("latitud")
        longitud = attrs.get("longitud")
        if (latitud is None) != (longitud is None):
            raise serializers.ValidationError({
                "latitud": "Debes enviar latitud y longitud juntas.",
                "longitud": "Debes enviar latitud y longitud juntas.",
            })

        return attrs
