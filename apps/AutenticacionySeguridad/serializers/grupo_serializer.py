from rest_framework import serializers

from ..models import ComponenteSistema, GrupoPermisoComponente, GrupoUsuario


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


class GrupoPermisoComponenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoPermisoComponente
        fields = [
            "id_permiso_componente",
            "grupo",
            "componente",
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
