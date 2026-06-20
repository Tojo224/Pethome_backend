from django.urls import path
from .views import (
    KPIsView,
    DashboardKPIsView,
    ListStaticReportsView,
    GenerarEstaticoView,
    GenerarDinamicoView,
    HistorialReportesView,
    ReporteDetailView,
    ExportReporteView,
)

urlpatterns = [
    path("kpis/", KPIsView.as_view(), name="reportes-kpis"),
    path("dashboard-kpis/", DashboardKPIsView.as_view(), name="reportes-dashboard-kpis"),
    path("estaticos/", ListStaticReportsView.as_view(), name="reportes-estaticos-list"),
    path("estaticos/generar/", GenerarEstaticoView.as_view(), name="reportes-estaticos-generar"),
    path("dinamicos/generar/", GenerarDinamicoView.as_view(), name="reportes-dinamicos-generar"),
    path("historial/", HistorialReportesView.as_view(), name="reportes-historial"),
    path("<int:pk>/", ReporteDetailView.as_view(), name="reportes-detail"),
    path("<int:pk>/exportar/", ExportReporteView.as_view(), name="reportes-exportar"),
]
