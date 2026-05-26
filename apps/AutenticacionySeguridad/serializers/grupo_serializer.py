from rest_framework import serializers

from ..models import ComponenteSistema, GrupoPermisoComponente, GrupoUsuario, UsuarioGrupo


class GrupoUsuarioSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)

    class Meta:
        model = GrupoUsuario
        fields = [
            "id_grupo",
            "nombre",
            "descripcion",
            "estado",
            "fecha_creacion",
            "id_veterinaria",
        ]
        read_only_fields = ["id_grupo", "fecha_creacion", "id_veterinaria"]


class ComponenteNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponenteSistema
        fields = ["id_componente", "codigo", "nombre", "tipo", "plataforma"]

class GrupoPermisoComponenteSerializer(serializers.ModelSerializer):
    componente = ComponenteNestedSerializer(read_only=True)
    componente_id = serializers.PrimaryKeyRelatedField(
        queryset=ComponenteSistema.objects.filter(estado=True),
        source="componente",
        write_only=True,
    )

    class Meta:
        model = GrupoPermisoComponente
        fields = [
            "id_permiso_componente",
            "grupo",
            "componente",
            "componente_id",
            "puede_ver",
            "puede_crear",
            "puede_editar",
            "puede_eliminar",
            "puede_exportar",
            "puede_ejecutar",
            "estado",
        ]
        read_only_fields = ["id_permiso_componente"]

    def validate(self, attrs):
        grupo = attrs.get("grupo")
        componente = attrs.get("componente")
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)

        if tenant_id is None:
            raise serializers.ValidationError("No se pudo resolver el tenant activo.")

        if grupo and grupo.veterinaria_id != tenant_id:
            raise serializers.ValidationError({
                "grupo": "El grupo no pertenece a la veterinaria actual."
            })

        if componente and not ComponenteSistema.objects.filter(pk=componente.pk, estado=True).exists():
            raise serializers.ValidationError({
                "componente": "El componente no es valido o esta inactivo."
            })

        return attrs

    def to_internal_value(self, data):
        mutable = data.copy()
        # Backward compatibility with clients/tests that send "componente"
        # as an integer id instead of "componente_id".
        componente_raw = mutable.get("componente")
        if "componente_id" not in mutable and componente_raw is not None:
            if not isinstance(componente_raw, dict):
                mutable["componente_id"] = componente_raw
        return super().to_internal_value(mutable)


class UsuarioGrupoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioGrupo
        fields = ["id_usuario_grupo", "usuario", "grupo", "fecha_asignacion", "estado"]
        read_only_fields = ["id_usuario_grupo", "fecha_asignacion"]
