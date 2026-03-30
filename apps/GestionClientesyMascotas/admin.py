from django.contrib import admin
from apps.GestionClientesyMascotas.models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id_cliente', 'nombre', 'apellido', 'usuario', 'telefono', 'ciudad', 'activo', 'fecha_registro')
    list_filter = ('activo', 'ciudad', 'pais', 'fecha_registro')
    search_fields = ('nombre', 'apellido', 'usuario__correo', 'telefono', 'ciudad')
    readonly_fields = ('fecha_registro', 'fecha_actualizacion')
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('usuario', 'nombre', 'apellido')
        }),
        ('Contacto', {
            'fields': ('telefono',)
        }),
        ('Dirección', {
            'fields': ('direccion', 'ciudad', 'pais', 'codigo_postal')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_registro', 'fecha_actualizacion')
        }),
    )

