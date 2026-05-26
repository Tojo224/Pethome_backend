from django.db.models import Q
from ..models.mascota import Mascota
from apps.GestionServiciosyReserva.models.especie import Especie
from apps.GestionServiciosyReserva.models.raza import Raza
from apps.AutenticacionySeguridad.models import Perfil, Rol

class MascotaSelector:
    @staticmethod
    def get_mascotas_by_tenant(veterinaria_id, user=None):
        """
        Retorna las mascotas de una veterinaria. 
        Si el usuario es un cliente, solo retorna sus mascotas.
        Si es Super Admin, retorna todas las mascotas.
        """
        # Si hay tenant resuelto en el request, siempre scopear por tenant.
        # Solo usar vista global cuando no exista tenant explícito.
        if user and getattr(user, "is_superuser", False) and not veterinaria_id:
            queryset = Mascota.objects.all().select_related(
                "usuario", "especie", "raza"
            )
        else:
            queryset = Mascota.objects.filter(veterinaria_id=veterinaria_id).select_related(
                "usuario", "especie", "raza"
            )
        
        if user and hasattr(user, "role") and user.role.nombre == Rol.RolName.CLIENT:
            queryset = queryset.filter(usuario=user)
            
        return queryset

    @staticmethod
    def get_mascota_detail(pk, veterinaria_id, user=None):
        if user and getattr(user, "is_superuser", False) and not veterinaria_id:
            queryset = Mascota.objects.filter(pk=pk)
        else:
            queryset = Mascota.objects.filter(pk=pk, veterinaria_id=veterinaria_id)
        
        if user and hasattr(user, "role") and user.role.nombre == Rol.RolName.CLIENT:
            queryset = queryset.filter(usuario=user)
            
        return queryset.select_related(
            "usuario", "especie", "raza"
        ).first()

    @staticmethod
    def filter_mascotas(veterinaria_id, user=None, search=None, especie_id=None):
        queryset = MascotaSelector.get_mascotas_by_tenant(veterinaria_id, user)
        
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(usuario__perfil__nombre__icontains=search) |
                Q(usuario__correo__icontains=search)
            )
            
        if especie_id:
            queryset = queryset.filter(especie_id=especie_id)
            
        return queryset

class EspecieSelector:
    @staticmethod
    def get_all_especies():
        return Especie.objects.all().order_by("nombre")

class RazaSelector:
    @staticmethod
    def get_razas_by_especie(especie_id):
        return Raza.objects.filter(especie_id=especie_id).order_by("nombre")
