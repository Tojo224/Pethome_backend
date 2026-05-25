from .servicios_serializer import (
    ServicioSerializer,
)
from .precioservicio_serializer import (
    PrecioServicioSerializer,
)
from .categoriaservicio_serializer import (
    CategoriaServicioSerializer,
)
from .citas_serializer import (
    CitaSerializer,
    CitaEstadoUpdateSerializer,
)
from .rutas_serializer import (
    DetalleRutaCreateSerializer,
    DetalleRutaReadSerializer,
    DetalleRutaUpdateSerializer,
    RutaProgramadaReadSerializer,
    RutaProgramadaWriteSerializer,
    UnidadMovilSerializer,
    UnidadMovilWriteSerializer,
)
from .logistica_asignacion_serializer import (
    UnidadMovilAsignacionPersonalReadSerializer,
    UnidadMovilAsignacionPersonalWriteSerializer,
    UnidadMovilAsignacionReadSerializer,
    UnidadMovilAsignacionWriteSerializer,
)
