from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .permissions import IsReporteRole
from .serializers import (
    ReporteGeneradoSerializer,
    GenerarEstaticoSerializer,
    GenerarDinamicoSerializer,
    DashboardKPISerializer,
)
from .models import ReporteGenerado
from .services import (
    report_scope_service,
    static_report_service,
    dynamic_report_service,
    export_service,
)


class KPIsView(APIView):
    permission_classes = [IsAuthenticated, IsReporteRole]

    def get(self, request):
        user = request.user
        id_vet = request.query_params.get("id_veterinaria")
        scope = report_scope_service.resolve_scope(user, id_vet)

        from apps.GestionServiciosyReserva.models.citas import Cita
        from apps.GestiondeVentasyPagos.models.venta import Venta
        from apps.GestionClientesyMascotas.models.mascota import Mascota
        from django.db.models import Sum

        qs_citas = Cita.objects.all()
        if scope.get("veterinaria"):
            qs_citas = qs_citas.filter(veterinaria=scope.get("veterinaria"))
        citas_pendientes = qs_citas.filter(estado=Cita.EstadoChoices.PENDIENTE).count()

        qs_ventas = Venta.objects.all()
        if scope.get("veterinaria"):
            qs_ventas = qs_ventas.filter(veterinaria=scope.get("veterinaria"))
        ingresos = qs_ventas.aggregate(total=Sum("total"))

        qs_mascotas = Mascota.objects.all()
        if scope.get("veterinaria"):
            qs_mascotas = qs_mascotas.filter(veterinaria=scope.get("veterinaria"))
        total_mascotas = qs_mascotas.count()

        return Response(
            {
                "citas_pendientes": citas_pendientes,
                "ingresos_total": float(ingresos.get("total") or 0),
                "total_mascotas": total_mascotas,
            }
        )


class DashboardKPIsView(APIView):
    permission_classes = [IsAuthenticated, IsReporteRole]

    def get(self, request):
        serializer = DashboardKPISerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        user = request.user
        id_vet = request.query_params.get("id_veterinaria")

        from .services import report_scope_service
        scope = report_scope_service.resolve_scope(user, id_vet)

        from .services.dashboard_kpi_service import build_dashboard_kpis
        data = build_dashboard_kpis(
            scope,
            periodo=params.get("periodo"),
            fecha_inicio=params.get("fecha_inicio"),
            fecha_fin=params.get("fecha_fin"),
        )
        return Response(data)


class ListStaticReportsView(APIView):
    permission_classes = [IsAuthenticated, IsReporteRole]

    def get(self, request):
        data = static_report_service.list_static_reports()
        return Response(data)


class GenerarEstaticoView(APIView):
    permission_classes = [IsAuthenticated, IsReporteRole]

    def post(self, request):
        serializer = GenerarEstaticoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        user = request.user
        filtros = payload.get("filtros") or {}
        id_vet = filtros.get("id_veterinaria")
        scope = report_scope_service.resolve_scope(user, id_vet)

        reporte = ReporteGenerado(
            usuario=user,
            veterinaria=scope.get("veterinaria"),
            tipo_reporte=payload.get("slug"),
            origen=ReporteGenerado.OrigenChoices.ESTATICO,
            titulo=payload.get("slug"),
            filtros=filtros,
            formato=payload.get("formato"),
            estado=ReporteGenerado.EstadoChoices.GENERADO,
        )
        try:
            result = static_report_service.generate_static(payload.get("slug"), filtros, scope)
            reporte.datos = result.get("datos")
            reporte.columnas = result.get("columnas")
            reporte.titulo = result.get("titulo")
            reporte.save()
            return Response(ReporteGeneradoSerializer(reporte).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            reporte.estado = ReporteGenerado.EstadoChoices.ERROR
            reporte.mensaje_error = str(e)
            reporte.save()
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GenerarDinamicoView(APIView):
    permission_classes = [IsAuthenticated, IsReporteRole]

    def post(self, request):
        serializer = GenerarDinamicoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        user = request.user
        filtros = payload.get("filtros") or {}
        id_vet = filtros.get("id_veterinaria")
        scope = report_scope_service.resolve_scope(user, id_vet)

        reporte = ReporteGenerado(
            usuario=user,
            veterinaria=scope.get("veterinaria"),
            tipo_reporte=payload.get("entidad"),
            origen=ReporteGenerado.OrigenChoices.DINAMICO,
            titulo=f"Dinamico - {payload.get('entidad')}",
            filtros=filtros,
            formato=payload.get("formato"),
            estado=ReporteGenerado.EstadoChoices.GENERADO,
        )
        try:
            result = dynamic_report_service.generate_dynamic(
                payload.get("entidad"), payload.get("metricas"), payload.get("dimensiones"), filtros, scope, user
            )
            reporte.datos = result.get("datos")
            reporte.columnas = result.get("columnas")
            reporte.titulo = result.get("titulo")
            reporte.save()
            return Response(ReporteGeneradoSerializer(reporte).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            reporte.estado = ReporteGenerado.EstadoChoices.ERROR
            reporte.mensaje_error = str(e)
            reporte.save()
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HistorialReportesView(APIView):
    permission_classes = [IsAuthenticated, IsReporteRole]

    def get(self, request):
        user = request.user
        id_vet = request.query_params.get("id_veterinaria")
        scope = report_scope_service.resolve_scope(user, id_vet)
        qs = ReporteGenerado.objects.all()
        if scope.get("veterinaria"):
            qs = qs.filter(veterinaria=scope.get("veterinaria"))

        tipo_reporte = request.query_params.get("tipo_reporte") or request.query_params.get("tipo")
        formato = request.query_params.get("formato")
        estado = request.query_params.get("estado")
        fecha_i = request.query_params.get("fecha_inicio")
        fecha_f = request.query_params.get("fecha_fin")
        if tipo_reporte:
            qs = qs.filter(tipo_reporte=tipo_reporte)
        if formato:
            qs = qs.filter(formato=formato.upper())
        if estado:
            qs = qs.filter(estado=estado.upper())
        if fecha_i:
            qs = qs.filter(fecha_generacion__date__gte=fecha_i)
        if fecha_f:
            qs = qs.filter(fecha_generacion__date__lte=fecha_f)

        paginator = PageNumberPagination()
        paginator.page_size_query_param = "page_size"
        paginator.page_size = 10
        page = paginator.paginate_queryset(qs.order_by("-fecha_generacion"), request)
        serializer = ReporteGeneradoSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ReporteDetailView(APIView):
    permission_classes = [IsAuthenticated, IsReporteRole]

    def get(self, request, pk):
        user = request.user
        id_vet = request.query_params.get("id_veterinaria")
        scope = report_scope_service.resolve_scope(user, id_vet)
        try:
            reporte = ReporteGenerado.objects.get(id_reporte=pk)
        except ReporteGenerado.DoesNotExist:
            return Response({"detail": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)

        if scope.get("veterinaria") and reporte.veterinaria and reporte.veterinaria != scope.get("veterinaria"):
            return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

        return Response(ReporteGeneradoSerializer(reporte).data)


class ExportReporteView(APIView):
    permission_classes = [IsAuthenticated, IsReporteRole]

    def get(self, request, pk):
        formato = request.query_params.get("formato", "PDF").upper()
        user = request.user
        id_vet = request.query_params.get("id_veterinaria")
        scope = report_scope_service.resolve_scope(user, id_vet)
        try:
            reporte = ReporteGenerado.objects.get(id_reporte=pk)
        except ReporteGenerado.DoesNotExist:
            return Response({"detail": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)

        if scope.get("veterinaria") and reporte.veterinaria and reporte.veterinaria != scope.get("veterinaria"):
            return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

        if reporte.estado == ReporteGenerado.EstadoChoices.ERROR:
            return Response({"detail": "No se puede exportar un reporte con estado ERROR."}, status=status.HTTP_400_BAD_REQUEST)

        if not reporte.columnas:
            return Response({"detail": "El reporte no contiene columnas para exportar."}, status=status.HTTP_400_BAD_REQUEST)

        report_payload = {"titulo": reporte.titulo, "columnas": reporte.columnas or [], "datos": reporte.datos or []}
        try:
            content, content_type, filename = export_service.export_report(report_payload, formato)
            from django.http import HttpResponse

            resp = HttpResponse(content, content_type=content_type)
            resp["Content-Disposition"] = f'attachment; filename="{filename}"'
            return resp
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
