from rest_framework import serializers
import logging

from apps.GestionInventarioProveedores.models.categoria_producto import CategoriaProducto


logger = logging.getLogger(__name__)


class EstadoField(serializers.Field):
    def to_representation(self, value):
        return "Activo" if value else "Inactivo"

    def to_internal_value(self, data):
        if isinstance(data, bool):
            return data
        if isinstance(data, str):
            v = data.strip().lower()
            if v in ("activo", "true", "1", "si", "sí"):
                return True
            if v in ("inactivo", "false", "0", "no"):
                return False
        raise serializers.ValidationError("Valor de estado inválido")


class CategoriaProductoSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    estado = EstadoField()

    class Meta:
        model = CategoriaProducto
        fields = [
            "id_categoria_producto",
            "nombre",
            "descripcion",
            "estado",
            "id_veterinaria",
        ]
        read_only_fields = ["id_categoria_producto", "id_veterinaria"]

    def validate_nombre(self, value):
        nombre = (value or "").strip()
        if not nombre:
            raise serializers.ValidationError("El nombre es requerido")

        request = self.context.get("request")
        tenant_id = None
        if request is not None:
            tenant = getattr(request, "tenant", None)
            tenant_id = getattr(tenant, "id", None) or getattr(request.user, "veterinaria_id", None)

        logger.debug(
            "CategoriaProductoSerializer.validate_nombre nombre=%s tenant_id=%s user_id=%s has_request=%s",
            nombre,
            tenant_id,
            getattr(getattr(request, "user", None), "id_usuario", None),
            request is not None,
        )

        if tenant_id:
            queryset = CategoriaProducto.objects.filter(
                veterinaria_id=tenant_id,
                nombre__iexact=nombre,
            )
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                logger.debug(
                    "CategoriaProductoSerializer.validate_nombre duplicate nombre=%s tenant_id=%s",
                    nombre,
                    tenant_id,
                )
                raise serializers.ValidationError(
                    "Ya existe una categoría con ese nombre en esta veterinaria."
                )

        return nombre
