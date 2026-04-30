from django.urls import path

from apps.GestionarClinicaVeterinaria.views.historial_clinico_view import (
    HistorialClinicoListCreateView,
    HistorialClinicoPorMascotaView,
)
from apps.GestionarClinicaVeterinaria.views.consulta_clinica_view import (
    ConsultaClinicaListCreateView,
    ConsultaClinicaDetailView,
)
from apps.GestionarClinicaVeterinaria.views.tratamiento_view import (
    TratamientoListCreateView,
    TratamientoDetailView,
)
from apps.GestionarClinicaVeterinaria.views.receta_view import (
    RecetaPorConsultaView,
    RecetaDetailView,
)
from apps.GestionarClinicaVeterinaria.views.detalle_receta_view import (
    DetalleRecetaListCreateView,
    DetalleRecetaDetailView,
)
from apps.GestionarClinicaVeterinaria.views.vacuna_aplicada_view import (
    VacunaAplicadaListCreateView,
    VacunaAplicadaDetailView,
)
from apps.GestionarClinicaVeterinaria.views.archivo_clinico_view import (
    ArchivoClinicoCreateView,
    ArchivoClinicoUpdateView,
)
from apps.GestionarClinicaVeterinaria.views.veterinario_view import (
    VeterinarioListView,
)

urlpatterns = [
    path(
        "historiales/",
        HistorialClinicoListCreateView.as_view(),
        name="historial-clinico-list-create",
    ),
    path(
        "mascotas/<int:id_mascota>/historial/",
        HistorialClinicoPorMascotaView.as_view(),
        name="historial-clinico-por-mascota",
    ),
    path(
        "historiales/<int:id_historial_clinico>/consultas/",
        ConsultaClinicaListCreateView.as_view(),
        name="consulta-clinica-list-create",
    ),
    path(
        "consultas/<int:id_consulta_clinica>/",
        ConsultaClinicaDetailView.as_view(),
        name="consulta-clinica-detail",
    ),
    path(
        "consultas/<int:id_consulta_clinica>/tratamientos/",
        TratamientoListCreateView.as_view(),
        name="tratamiento-list-create",
    ),
    path(
        "tratamientos/<int:id_tratamiento>/",
        TratamientoDetailView.as_view(),
        name="tratamiento-detail",
    ),
    path(
        "consultas/<int:id_consulta_clinica>/receta/",
        RecetaPorConsultaView.as_view(),
        name="receta-por-consulta",
    ),
    path(
        "recetas/<int:id_receta>/",
        RecetaDetailView.as_view(),
        name="receta-detail",
    ),
    path(
        "recetas/<int:id_receta>/detalles/",
        DetalleRecetaListCreateView.as_view(),
        name="detalle-receta-list-create",
    ),
    path(
        "detalles-receta/<int:id_detalle_receta>/",
        DetalleRecetaDetailView.as_view(),
        name="detalle-receta-detail",
    ),
    path(
        "consultas/<int:id_consulta_clinica>/vacunas/",
        VacunaAplicadaListCreateView.as_view(),
        name="vacuna-aplicada-list-create",
    ),
    path(
        "vacunas/<int:id_vacuna_aplicada>/",
        VacunaAplicadaDetailView.as_view(),
        name="vacuna-aplicada-detail",
    ),
    path(
        "consultas/<int:id_consulta_clinica>/archivos/",
        ArchivoClinicoCreateView.as_view(),
        name="archivo-clinico-create",
    ),
    path(
        "archivos/<int:id_archivo_clinico>/",
        ArchivoClinicoUpdateView.as_view(),
        name="archivo-clinico-update",
    ),
    path(
        "veterinarios/",
        VeterinarioListView.as_view(),
        name="veterinario-list",
    ),
]