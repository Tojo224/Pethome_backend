from .historial_clinico_view import HistorialClinicoListCreateView, HistorialClinicoPorMascotaView
from .consulta_clinica_view import ConsultaClinicaListCreateView, ConsultaClinicaDetailView
from .tratamiento_view import TratamientoListCreateView, TratamientoDetailView
from .receta_view import RecetaPorConsultaView, RecetaDetailView
from .detalle_receta_view import DetalleRecetaListCreateView, DetalleRecetaDetailView
from .vacuna_aplicada_view import VacunaAplicadaListCreateView, VacunaAplicadaDetailView
from .archivo_clinico_view import ArchivoClinicoCreateView, ArchivoClinicoUpdateView
from .veterinario_view import VeterinarioListView
from .veterinaria_view import (
    VeterinariaListCreateView,
    VeterinariaDetailView,
    VeterinariaPlanUpdateView,
)
from .plan_sanitario_preventivo_view import (
    PlanSanitarioClientesFilterView,
    PlanSanitarioPorMascotaView,
    PlanSanitarioDetailView,
)
