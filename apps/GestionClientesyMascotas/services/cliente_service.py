"""Services para Cliente - Lógica de negocio."""

from typing import Dict, Any
from django.db import transaction
from apps.AutenticacionySeguridad.models import User
from apps.GestionClientesyMascotas.models import Cliente


@transaction.atomic
def crear_cliente(usuario: User, datos: Dict[str, Any]) -> Cliente:
    """
    Crea un nuevo cliente.
    
    Args:
        usuario: Instancia del usuario
        datos: Diccionario con los datos del cliente
    
    Returns:
        Instancia del Cliente creado
    
    Raises:
        ValueError: Si el usuario ya tiene un cliente asociado
    """
    # Verificar que el usuario no tenga ya un cliente
    if Cliente.objects.filter(usuario=usuario).exists():
        raise ValueError("Este usuario ya tiene un perfil de cliente.")
    
    cliente = Cliente.objects.create(
        usuario=usuario,
        nombre=datos.get('nombre', ''),
        apellido=datos.get('apellido', ''),
        telefono=datos.get('telefono', ''),
        direccion=datos.get('direccion', ''),
        ciudad=datos.get('ciudad', ''),
        pais=datos.get('pais', ''),
        codigo_postal=datos.get('codigo_postal', ''),
    )
    return cliente


@transaction.atomic
def actualizar_cliente(cliente: Cliente, datos: Dict[str, Any]) -> Cliente:
    """
    Actualiza los datos de un cliente.
    
    Args:
        cliente: Instancia del Cliente
        datos: Diccionario con los datos a actualizar
    
    Returns:
        Cliente actualizado
    """
    for campo, valor in datos.items():
        if hasattr(cliente, campo) and valor is not None:
            setattr(cliente, campo, valor)
    
    cliente.save()
    return cliente


@transaction.atomic
def desactivar_cliente(cliente: Cliente) -> Cliente:
    """
    Desactiva un cliente (soft delete).
    
    Args:
        cliente: Instancia del Cliente
    
    Returns:
        Cliente desactivado
    """
    cliente.activo = False
    cliente.save()
    return cliente


@transaction.atomic
def activar_cliente(cliente: Cliente) -> Cliente:
    """
    Activa un cliente desactivado.
    
    Args:
        cliente: Instancia del Cliente
    
    Returns:
        Cliente activado
    """
    cliente.activo = True
    cliente.save()
    return cliente


@transaction.atomic
def eliminar_cliente(cliente: Cliente) -> None:
    """
    Elimina un cliente completamente.
    
    Args:
        cliente: Instancia del Cliente a eliminar
    """
    cliente.delete()
