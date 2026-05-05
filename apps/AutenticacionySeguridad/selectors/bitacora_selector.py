from ..models.bitacora import Bitacora

class BitacoraSelector:
    @staticmethod
    def get_visible_bitacora(user, veterinaria_id=None):
        """
        Retorna el queryset de bitácora visible según el rol del usuario y el tenant.
        SuperAdmin ve todo. Otros ven solo su veterinaria.
        """
        if getattr(user, "is_superuser", False):
            return Bitacora.objects.all()

        if veterinaria_id:
            return Bitacora.objects.filter(veterinaria_id=veterinaria_id)

        return Bitacora.objects.none()

    @staticmethod
    def get_evento_by_id(user, pk, veterinaria_id=None):
        return BitacoraSelector.get_visible_bitacora(user, veterinaria_id).filter(pk=pk).first()
