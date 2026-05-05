from django.db.models import Q
from ..models.mascota import Mascota
from ..models.especie import Especie
from ..models.raza import Raza
from apps.AutenticacionySeguridad.models import Perfil, Rol

class MascotaSelector:
    @staticmethod
    def get_mascotas_by_tenant(veterinaria_id, user=None):
        """
        Retorna las mascotas de una veterinaria. 
        Si el usuario es un cliente, solo retorna sus mascotas.
        """
        queryset = Mascota.objects.filter(veterinaria_id=veterinaria_id).select_related(
            "propietario", "especie", "raza"
        )
        
        if user and hasattr(user, "role") and user.role.nombre == Rol.RolName.CLIENT:
            queryset = queryset.filter(propietario__usuario=user)
            
        return queryset

    @staticmethod
    def get_mascota_detail(pk, veterinaria_id, user=None):
        queryset = Mascota.objects.filter(pk=pk, veterinaria_id=veterinaria_id)
        
        if user and hasattr(user, "role") and user.role.nombre == Rol.RolName.CLIENT:
            queryset = queryset.filter(propietario__usuario=user)
            
        return queryset.select_related(
            "propietario", "especie", "raza"
        ).first()

    @staticmethod
    def filter_mascotas(veterinaria_id, user=None, search=None, especie_id=None):
        queryset = MascotaSelector.get_mascotas_by_tenant(veterinaria_id, user)
        
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(propietario__nombre__icontains=search)
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
