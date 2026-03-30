"""
EQUIPO AVISO IMPORTANTE ESTO PARA CADA APP
El filters.py se encarga de filtrar los datos que se envian a los endpoints.

Delegamos la lógica de filtrado a django-filter para permitir 
búsquedas dinámicas por URL sin ensuciar el QuerySet principal.

Funcionamiento: 
1. Lee los parámetros de la URL.
2. 'field_name' indica la columna en la BD.
3. 'lookup_expr' define la comparación (gte: >=, lte: <=, icontains: busca texto).
"""