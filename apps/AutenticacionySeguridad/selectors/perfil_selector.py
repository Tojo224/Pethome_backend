from django.db.models import Q
from ..models import User, Perfil, Suscripcion

class UsuarioSelector:
    @staticmethod
    def get_usuario_by_id(usuario_id):
        return User.objects.filter(id_usuario=usuario_id).first()

    @staticmethod
    def get_usuario_by_email(email):
        return User.objects.filter(correo=email).first()

class PerfilSelector:
    @staticmethod
    def get_perfil_by_usuario(usuario):
        return Perfil.objects.filter(usuario=usuario).first()

    @staticmethod
    def get_perfil_with_details(perfil_id, veterinaria_id=None):
        queryset = Perfil.objects.select_related("usuario", "usuario__role")
        if veterinaria_id:
            queryset = queryset.filter(usuario__veterinaria_id=veterinaria_id)
        return queryset.filter(id_perfil=perfil_id).first()

    @staticmethod
    def filter_perfiles(veterinaria_id, search=None, rol=None, estado=None):
        """Aplica filtros complejos de búsqueda sobre los perfiles de una veterinaria."""
        queryset = Perfil.objects.select_related("usuario", "usuario__role").filter(
            usuario__veterinaria_id=veterinaria_id
        )

        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search)
                | Q(usuario__correo__icontains=search)
                | Q(telefono__icontains=search)
                | Q(direccion__icontains=search)
            )

        if rol:
            queryset = queryset.filter(usuario__role__nombre=rol)

        if estado is not None:
            if isinstance(estado, str):
                estado_norm = estado.lower()
                if estado_norm in {"true", "1", "si", "sí"}:
                    queryset = queryset.filter(usuario__is_active=True)
                elif estado_norm in {"false", "0", "no"}:
                    queryset = queryset.filter(usuario__is_active=False)
            else:
                queryset = queryset.filter(usuario__is_active=bool(estado))

        return queryset.order_by("-id_perfil")

class SuscripcionSelector:
    @staticmethod
    def get_suscripcion_activa(veterinaria_id):
        """Obtiene la suscripción más reciente y válida de una veterinaria."""
        return (
            Suscripcion.objects.filter(veterinaria_id=veterinaria_id)
            .select_related("plan")
            .order_by("-fecha_fin", "-fecha_creacion")
            .first()
        )
