"""Selectores para Cliente - Lectura de datos."""

from django.db.models import QuerySet, Q
from apps.GestionClientesyMascotas.models import Cliente


def get_cliente_by_id(cliente_id: int) -> Cliente | None:
    """Obtiene un cliente por su ID."""
    try:
        return Cliente.objects.select_related('usuario').get(id_cliente=cliente_id)
    except Cliente.DoesNotExist:
        return None


def get_cliente_by_usuario(usuario_id: int) -> Cliente | None:
    """Obtiene un cliente por su ID de usuario."""
    try:
        return Cliente.objects.select_related('usuario').get(usuario_id=usuario_id)
    except Cliente.DoesNotExist:
        return None


def get_all_clientes(activos_solo: bool = False) -> QuerySet:
    """Obtiene todos los clientes."""
    queryset = Cliente.objects.select_related('usuario').all()
    
    if activos_solo:
        queryset = queryset.filter(activo=True)
    
    return queryset.order_by('-fecha_registro')


def buscar_clientes(
    search_term: str = "",
    activos_solo: bool = False
) -> QuerySet:
    """
    Busca clientes por nombre, apellido o email.
    
    Args:
        search_term: Término de búsqueda
        activos_solo: Si solo mostrar activos
    
    Returns:
        QuerySet de clientes que coincidan
    """
    queryset = Cliente.objects.select_related('usuario').all()
    
    if search_term:
        queryset = queryset.filter(
            Q(nombre__icontains=search_term) |
            Q(apellido__icontains=search_term) |
            Q(usuario__correo__icontains=search_term)
        )
    
    if activos_solo:
        queryset = queryset.filter(activo=True)
    
    return queryset.order_by('-fecha_registro')


def get_clientes_por_ciudad(ciudad: str) -> QuerySet:
    """Obtiene clientes de una ciudad específica."""
    return Cliente.objects.select_related('usuario').filter(
        ciudad__iexact=ciudad,
        activo=True
    ).order_by('apellido', 'nombre')
