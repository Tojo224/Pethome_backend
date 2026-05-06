from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import UsuarioGrupo
from ..serializers.grupo_serializer import UsuarioGrupoSerializer
from ..permissions.tenant_rbac import HasComponentPermission
from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from ..mixins.tenant_mixins import TenantViewMixin

class UsuarioGrupoListCreateView(TenantViewMixin, generics.ListCreateAPIView):
    """
    Vista para asignar usuarios a grupos y listar asignaciones.
    """
    serializer_class = UsuarioGrupoSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_GRUPO_USUARIO"

    def get_queryset(self):
        return UsuarioGrupo.objects.filter(
            grupo__veterinaria_id=self.get_tenant_id()
        ).select_related("usuario", "grupo")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 201:
            self.registrar_bitacora(
                accion=BitacoraAccion.USUARIO_ASIGNADO_GRUPO,
                descripcion=f"Usuario #{response.data.get('usuario')} asignado al grupo #{response.data.get('grupo')}.",
                modulo=BitacoraModulo.ROLES_PERMISOS,
                entidad_tipo="UsuarioGrupo",
                entidad_id=response.data.get("id_usuario_grupo"),
                resultado=BitacoraResultado.EXITO,
                metadatos={"user_id": response.data.get("usuario"), "grupo_id": response.data.get("grupo")}
            )
        return response

class UsuarioGrupoDeleteView(TenantViewMixin, generics.DestroyAPIView):
    """
    Vista para remover usuarios de grupos.
    """
    serializer_class = UsuarioGrupoSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_GRUPO_USUARIO"
    lookup_field = "pk"

    def get_queryset(self):
        return UsuarioGrupo.objects.filter(
            grupo__veterinaria_id=self.get_tenant_id()
        )

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        user_id = instance.usuario_id
        grupo_id = instance.grupo_id
        mapping_id = instance.id_usuario_grupo
        
        response = super().delete(request, *args, **kwargs)
        
        self.registrar_bitacora(
            accion=BitacoraAccion.USUARIO_REMOVIDO_GRUPO,
            descripcion=f"Usuario #{user_id} removido del grupo #{grupo_id}.",
            modulo=BitacoraModulo.ROLES_PERMISOS,
            entidad_tipo="UsuarioGrupo",
            entidad_id=mapping_id,
            resultado=BitacoraResultado.EXITO,
            metadatos={"user_id": user_id, "grupo_id": grupo_id}
        )
        return response
