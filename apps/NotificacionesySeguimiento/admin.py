from django.contrib import admin
from .models import Notificacion, DispositivoUsuario, ConfiguracionNotificacion

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "usuario", "veterinaria", "tipo", "estado", "fecha_creacion")
    list_filter = ("tipo", "estado", "veterinaria")
    search_fields = ("titulo", "mensaje", "usuario__correo")
    readonly_fields = ("fecha_creacion", "fecha_envio", "fecha_leida")

@admin.register(DispositivoUsuario)
class DispositivoUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "plataforma", "token_fcm", "activo", "fecha_registro")
    list_filter = ("plataforma", "activo", "veterinaria")
    search_fields = ("usuario__correo", "token_fcm")

@admin.register(ConfiguracionNotificacion)
class ConfiguracionNotificacionAdmin(admin.ModelAdmin):
    list_display = ("veterinaria", "tipo_notificacion", "dias_anticipacion", "activo")
    list_filter = ("tipo_notificacion", "activo")
    search_fields = ("veterinaria__nombre",)
