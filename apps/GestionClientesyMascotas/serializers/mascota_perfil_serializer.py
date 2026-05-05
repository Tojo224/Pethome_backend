from rest_framework import serializers
from apps.GestionClientesyMascotas.models.mascota import Mascota
from apps.AutenticacionySeguridad.serializers.perfil_serializer import PerfilSerializer
from apps.GestionarClinicaVeterinaria.models.consulta_clinica import ConsultaClinica
from apps.GestionServiciosyReserva.models.citas import Cita

class ConsultaClinicaResumenSerializer(serializers.ModelSerializer):
    veterinario_nombre = serializers.CharField(source="usuario_veterinario.perfil.nombre", read_only=True)
    
    class Meta:
        model = ConsultaClinica
        fields = [
            "id_consulta_clinica",
            "fecha_consulta",
            "motivo_consulta",
            "diagnostico",
            "veterinario_nombre",
            "peso",
            "temperatura",
        ]

class CitaResumenSerializer(serializers.ModelSerializer):
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True)
    
    class Meta:
        model = Cita
        fields = [
            "id_cita",
            "fecha_programada",
            "hora_inicio",
            "servicio_nombre",
            "modalidad",
            "direccion_cita",
            "estado",
        ]

class MascotaPerfilSeguimientoSerializer(serializers.ModelSerializer):
    dueño = PerfilSerializer(source="usuario.perfil", read_only=True)
    especie_nombre = serializers.CharField(source="especie.nombre", read_only=True)
    raza_nombre = serializers.CharField(source="raza.nombre", read_only=True)
    
    historial_clinico_consultas = serializers.SerializerMethodField()
    historial_servicios = serializers.SerializerMethodField()

    class Meta:
        model = Mascota
        fields = [
            "id_mascota",
            "nombre",
            "foto",
            "sexo",
            "fecha_nac",
            "especie_nombre",
            "raza_nombre",
            "dueño",
            "historial_clinico_consultas",
            "historial_servicios",
        ]

    def get_historial_clinico_consultas(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        
        # --- REGLA SaaS: Privacidad de Historial Clínico ---
        # Solo veterinarios y administradores pueden ver el detalle médico.
        # Los clientes ven un historial de servicios, pero tal vez no el diagnóstico profundo.
        if user and (user.is_superuser or (hasattr(user, "role") and user.role.nombre in ["ADMIN", "VETERINARIAN"])):
            if hasattr(obj, "historial_clinico"):
                consultas = obj.historial_clinico.consultas_clinicas.filter(estado=True).order_by("-fecha_consulta")
                return ConsultaClinicaResumenSerializer(consultas, many=True).data
        return []

    def get_historial_servicios(self, obj):
        # Todas las citas asociadas a la mascota
        citas = obj.citas.all().order_by("-fecha_programada", "-hora_inicio")
        return CitaResumenSerializer(citas, many=True).data
