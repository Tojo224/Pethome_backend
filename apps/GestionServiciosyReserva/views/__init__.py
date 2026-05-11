from .servicios_view import ServicioListCreateView, ServicioDetailView
from .precioservicio_view import (
	PrecioServicioListCreateView,
	PrecioServicioDetailView,
	PrecioServicioDetailLegacyView,
)
from .categoriaservicio_view import (
	CategoriaServicioListCreateView,
	CategoriaServicioDetailView,
	CategoriaServicioDetailLegacyView,
)
from .citas_view import CitaListCreateView, CitaDetailView, CitaEstadoUpdateView
from .rutas_view import (
	UnidadMovilListCreateView,
	UnidadMovilDetailView,
	RutaProgramadaListCreateView,
	RutaProgramadaDetailView,
	RutaProgramadaDetalleListCreateView,
	DetalleRutaDetailView,
	MisRutasListView,
	MisRutasHoyView,
)
