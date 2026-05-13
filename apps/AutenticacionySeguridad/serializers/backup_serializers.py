from rest_framework import serializers
from ..models.backup_restore import BackupRestore
from ..models.backup_config import BackupConfig
from ..models.user import User
from ..services.backup_service import BackupService


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id_usuario", "correo"]


class BackupRestoreSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.perfil.nombre", read_only=True)
    usuario_correo = serializers.CharField(source="usuario.correo", read_only=True)
    veterinaria_nombre = serializers.CharField(source="veterinaria.nombre", read_only=True)
    
    class Meta:
        model = BackupRestore
        fields = [
            "id_backup_restore",
            "tipo",
            "fecha_hora",
            "ruta_archivo",
            "proveedor_almacenamiento",
            "estado",
            "hash_archivo",
            "motivo",
            "usuario",
            "usuario_nombre",
            "usuario_correo",
            "veterinaria",
            "veterinaria_nombre",
        ]
        read_only_fields = [
            "id_backup_restore",
            "fecha_hora",
            "hash_archivo",
            "usuario_nombre",
            "usuario_correo",
            "veterinaria_nombre",
        ]


class BackupConfigSerializer(serializers.ModelSerializer):
    veterinaria_nombre = serializers.CharField(source="veterinaria.nombre", read_only=True)
    
    class Meta:
        model = BackupConfig
        fields = [
            "id_backup_config",
            "veterinaria",
            "veterinaria_nombre",
            "frecuencia",
            "dias_retención",
            "último_backup",
            "próximo_backup_programado",
            "activo",
            "creado",
            "actualizado",
            "hora_ejecucion",
            "minuto_ejecucion",
            "dias_semana",
        ]
        read_only_fields = [
            "id_backup_config",
            "veterinaria",
            "veterinaria_nombre",
            "último_backup",
            "creado",
            "actualizado",
            "próximo_backup_programado",
        ]

    def validate_frecuencia(self, value):
        valid_choices = [choice[0] for choice in BackupConfig.FRECUENCIAS]
        if value not in valid_choices:
            raise serializers.ValidationError(
                f"Frecuencia debe ser una de: {', '.join(valid_choices)}"
            )
        return value

    def validate_dias_retención(self, value):
        if value < 1 or value > 365:
            raise serializers.ValidationError("Días de retención debe estar entre 1 y 365")
        return value
    
    def validate_hora_ejecucion(self, value):
        if not isinstance(value, int) or value < 0 or value > 23:
            raise serializers.ValidationError("Hora de ejecución debe estar entre 0 y 23")
        return value

    def validate_minuto_ejecucion(self, value):
        if not isinstance(value, int) or value < 0 or value > 59:
            raise serializers.ValidationError("Minuto de ejecución debe estar entre 0 y 59")
        return value
    
    def validate_dias_semana(self, value):
        if value and not all(isinstance(d, int) and 0 <= d <= 6 for d in value):
            raise serializers.ValidationError("Días de semana deben ser números entre 0 y 6")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if not data.get("último_backup"):
            last_backup = (
                BackupRestore.objects.filter(
                    veterinaria=instance.veterinaria,
                    tipo="BACKUP",
                    estado="EXITOSO",
                )
                .order_by("-fecha_hora")
                .values_list("fecha_hora", flat=True)
                .first()
            )
            if last_backup:
                data["último_backup"] = last_backup.isoformat()

        if not data.get("próximo_backup_programado"):
            try:
                next_backup = BackupService._calculate_next_backup_with_config(instance)
                if next_backup:
                    data["próximo_backup_programado"] = next_backup.isoformat()
            except Exception:
                # Si el cálculo falla, conservar el valor nulo para no romper la respuesta.
                pass

        return data
