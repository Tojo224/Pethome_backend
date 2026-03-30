from django.shortcuts import render

# Create your views here.

""" EQUIPO AVISO IMPORTANTE ESTO PARA CADA APP
La carpeta views es el puente entre el frontend y el backend, endpoints del módulo.
Aqui entra:
- llamadas a services
- uso de selectors para lecturas
- manejo de response/status

Una vista debe ser fácil de leer de arriba abajo.
Si empieza a verse “pesada”, hay que mover lógica a services/ o selectors/, ya que 
sabe tener un poco de todo.
"""
