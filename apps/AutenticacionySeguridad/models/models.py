from django.db import models

# Create your models here.
""" EQUIPO AVISO IMPORTANTE ESTO PARA CADA APP
Dentro de esta carpeta models trabajaremos descentralizando el models.py 
en archivos mas pequeños para tener un mejor control de los modelos
esto en cada app.
Aqui va:
- el modelo o los modelos
- métodos simples relacionados al propio modelo
- validaciones pequeñas del modelo
- choices/enums del dominio muy ligados al dato

Evitando poner todo en un solo archivo y evitemos colocar aqui lógica 
compleja de negocio, queries complejas(consultas complejas) y validaciones complejas.

"""
