import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')

import django

django.setup()

from django.db.models import Count

from apps.GestionInventarioProveedores.models import CategoriaProducto, Producto, Proveedor

print('CATEGORY DUPLICATES')
print(
    list(
        CategoriaProducto.objects.values('veterinaria_id', 'nombre')
        .annotate(total=Count('id_categoria_producto'))
        .filter(total__gt=1)
    )
)

print('PRODUCT DUPLICATES')
print(
    list(
        Producto.objects.values('veterinaria_id', 'nombre', 'categoria_producto_id')
        .annotate(total=Count('id_producto'))
        .filter(total__gt=1)
    )
)

print('PROVIDER DUPLICATES')
print(
    list(
        Proveedor.objects.values('veterinaria_id', 'nombre')
        .annotate(total=Count('id_proveedor'))
        .filter(total__gt=1)
    )
)

print('ZERO PRICE')
print(
    list(
        Producto.objects.filter(precio_venta__lte=0)
        .values('id_producto', 'nombre', 'veterinaria_id', 'precio_venta')[:20]
    )
)

print('NEGATIVE OR ZERO BUY PRICE')
print(
    list(
        Producto.objects.exclude(precio_compra__isnull=True)
        .filter(precio_compra__lte=0)
        .values('id_producto', 'nombre', 'veterinaria_id', 'precio_compra')[:20]
    )
)

print('PROVIDER DUPLICATES BY TENANT+NAME')
for row in (
    Proveedor.objects.values('veterinaria_id', 'nombre')
    .annotate(total=Count('id_proveedor'))
    .filter(total__gt=1)
):
    print(row)

print('ZERO/NEGATIVE PRICE PRODUCTS')
for row in Producto.objects.filter(precio_venta__lte=0).values('id_producto', 'nombre', 'veterinaria_id', 'precio_venta')[:20]:
    print(row)
for row in Producto.objects.exclude(precio_compra__isnull=True).filter(precio_compra__lte=0).values('id_producto', 'nombre', 'veterinaria_id', 'precio_compra')[:20]:
    print(row)
