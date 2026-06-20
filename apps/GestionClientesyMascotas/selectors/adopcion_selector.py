from django.db.models import Q

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionClientesyMascotas.models.adopcion import Adopcion


class AdopcionSelector:
    @staticmethod
    def _is_admin_or_vet(user):
        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        return getattr(user, "is_superuser", False) or role_name in {
            RoleEnum.ADMIN.value,
            RoleEnum.VETERINARIAN.value,
        }

    @staticmethod
    def get_adopciones_by_tenant(veterinaria_id, user=None, public_only=False):
        if user and getattr(user, "is_superuser", False) and not veterinaria_id:
            queryset = Adopcion.objects.all()
        else:
            queryset = Adopcion.objects.filter(veterinaria_id=veterinaria_id)

        queryset = queryset.select_related("usuario", "usuario__perfil", "especie", "raza")

        if public_only or not AdopcionSelector._is_admin_or_vet(user):
            queryset = queryset.exclude(estado_adopcion=Adopcion.ESTADO_INACTIVO)
            queryset = queryset.exclude(estado_adopcion=Adopcion.ESTADO_ADOPTADO)

        return queryset

    @staticmethod
    def filter_adopciones(
        veterinaria_id,
        user=None,
        search=None,
        especie_id=None,
        estado=None,
        mine=None,
        public_only=False,
    ):
        queryset = AdopcionSelector.get_adopciones_by_tenant(
            veterinaria_id=veterinaria_id,
            user=user,
            public_only=public_only,
        )

        if mine and user and getattr(user, "is_authenticated", False):
            queryset = queryset.filter(usuario=user)

        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search)
                | Q(descripcion__icontains=search)
                | Q(ubicacion__icontains=search)
                | Q(especie__nombre__icontains=search)
                | Q(raza__nombre__icontains=search)
            )

        if especie_id:
            queryset = queryset.filter(especie_id=especie_id)

        if estado:
            queryset = queryset.filter(estado_adopcion=estado)

        return queryset
