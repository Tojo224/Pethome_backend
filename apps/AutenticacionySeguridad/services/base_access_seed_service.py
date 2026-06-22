from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from django.db import transaction

from ..models import (
    ComponenteSistema,
    GrupoPermisoComponente,
    GrupoUsuario,
    Rol,
    User,
    UsuarioGrupo,
    Veterinaria,
)


@dataclass(frozen=True)
class ComponentDef:
    codigo: str
    nombre: str
    tipo: str
    modulo: str
    ruta: Optional[str]
    plataforma: str
    padre_codigo: Optional[str]
    orden: int


class BaseAccessSeedService:
    """
    Servicio de seed SaaS:
    1) Catálogo global de componentes.
    2) Grupos base por veterinaria.
    3) Permisos base por rol/grupo.
    """

    ROLE_ADMIN = "ADMIN"
    ROLE_VET = "VETERINARIAN"
    ROLE_RECEPTION = "RECEPCIONISTA"
    ROLE_CLIENT = "CLIENT"
    ROLE_SUPERADMIN = "SUPERADMIN"

    GROUP_BY_ROLE = {
        ROLE_ADMIN: "ADMIN_BASE",
        ROLE_VET: "VETERINARIAN_BASE",
        ROLE_RECEPTION: "RECEPCIONISTA_BASE",
        ROLE_CLIENT: "CLIENT_BASE",
    }

    COMPONENTS: List[ComponentDef] = [
        # WEB - Menús
        ComponentDef("MENU_DASHBOARD", "Dashboard", "MENU", "WEB_APP", "/dashboard", "WEB", None, 10),
        ComponentDef("MENU_USUARIOS", "Usuarios", "MENU", "WEB_APP", "/usuarios", "WEB", None, 20),
        ComponentDef("MENU_CLIENTES", "Clientes", "MENU", "WEB_APP", "/clientes", "WEB", None, 30),
        ComponentDef("MENU_MASCOTAS", "Mascotas", "MENU", "WEB_APP", "/mascotas", "WEB", None, 40),
        ComponentDef("MENU_SERVICIOS", "Servicios", "MENU", "WEB_APP", "/servicios", "WEB", None, 50),
        ComponentDef("MENU_CITAS", "Citas", "MENU", "WEB_APP", "/citas", "WEB", None, 60),
        ComponentDef("MENU_RESERVAS", "Reservas", "MENU", "WEB_APP", "/reservas", "WEB", None, 70),
        ComponentDef("MENU_BITACORA", "Bitácora", "MENU", "WEB_APP", "/bitacora", "WEB", None, 80),
        # WEB - Botones negocio
        ComponentDef("BTN_CREAR_USUARIO", "Crear usuario", "BOTON", "WEB_APP", None, "WEB", "MENU_USUARIOS", 21),
        ComponentDef("BTN_EDITAR_USUARIO", "Editar usuario", "BOTON", "WEB_APP", None, "WEB", "MENU_USUARIOS", 22),
        ComponentDef("BTN_DESACTIVAR_USUARIO", "Desactivar usuario", "BOTON", "WEB_APP", None, "WEB", "MENU_USUARIOS", 23),
        ComponentDef("BTN_CREAR_CLIENTE", "Crear cliente", "BOTON", "WEB_APP", None, "WEB", "MENU_CLIENTES", 31),
        ComponentDef("BTN_EDITAR_CLIENTE", "Editar cliente", "BOTON", "WEB_APP", None, "WEB", "MENU_CLIENTES", 32),
        ComponentDef("BTN_DESACTIVAR_CLIENTE", "Desactivar cliente", "BOTON", "WEB_APP", None, "WEB", "MENU_CLIENTES", 33),
        ComponentDef("BTN_CREAR_MASCOTA", "Crear mascota", "BOTON", "WEB_APP", None, "WEB", "MENU_MASCOTAS", 41),
        ComponentDef("BTN_EDITAR_MASCOTA", "Editar mascota", "BOTON", "WEB_APP", None, "WEB", "MENU_MASCOTAS", 42),
        ComponentDef("BTN_DESACTIVAR_MASCOTA", "Desactivar mascota", "BOTON", "WEB_APP", None, "WEB", "MENU_MASCOTAS", 43),
        ComponentDef("BTN_CREAR_SERVICIO", "Crear servicio", "BOTON", "WEB_APP", None, "WEB", "MENU_SERVICIOS", 51),
        ComponentDef("BTN_EDITAR_SERVICIO", "Editar servicio", "BOTON", "WEB_APP", None, "WEB", "MENU_SERVICIOS", 52),
        ComponentDef("BTN_DESACTIVAR_SERVICIO", "Desactivar servicio", "BOTON", "WEB_APP", None, "WEB", "MENU_SERVICIOS", 53),
        ComponentDef("BTN_CONFIRMAR_CITA", "Confirmar cita", "BOTON", "WEB_APP", None, "WEB", "MENU_CITAS", 61),
        ComponentDef("BTN_REPROGRAMAR_CITA", "Reprogramar cita", "BOTON", "WEB_APP", None, "WEB", "MENU_CITAS", 62),
        ComponentDef("BTN_CANCELAR_CITA", "Cancelar cita", "BOTON", "WEB_APP", None, "WEB", "MENU_CITAS", 63),
        ComponentDef("BTN_EXPORTAR_BITACORA", "Exportar bitácora", "BOTON", "WEB_APP", None, "WEB", "MENU_BITACORA", 81),
        # Códigos RBAC actuales (backend)
        ComponentDef("SEG_USUARIOS", "Seguridad usuarios", "ACCION", "SEGURIDAD", None, "WEB", "MENU_USUARIOS", 200),
        ComponentDef("SEG_GRUPO_USUARIO", "Seguridad grupos", "ACCION", "SEGURIDAD", None, "WEB", "MENU_USUARIOS", 201),
        ComponentDef("SEG_PERMISO_COMPONENTE", "Seguridad permisos", "ACCION", "SEGURIDAD", None, "WEB", "MENU_USUARIOS", 202),
        ComponentDef("SEG_BITACORA", "Seguridad bitácora", "ACCION", "SEGURIDAD", None, "WEB", "MENU_BITACORA", 203),
        ComponentDef("SEG_BACKUPS", "Gestión de backups", "ACCION", "SEGURIDAD", "/_admin/gestionar-backups", "WEB", "MENU_BITACORA", 204),
        ComponentDef("CLI_CLIENTES", "Clientes API", "ACCION", "CLIENTES", None, "AMBOS", "MENU_CLIENTES", 210),
        ComponentDef("CLI_MASCOTAS", "Mascotas API", "ACCION", "MASCOTAS", None, "AMBOS", "MENU_MASCOTAS", 211),
        ComponentDef("CLI_CATALOGOS", "Catálogos mascotas", "ACCION", "MASCOTAS", None, "AMBOS", "MENU_MASCOTAS", 212),
        ComponentDef("CLI_VETERINARIOS", "Veterinarios", "ACCION", "CLINICA", None, "WEB", "MENU_CITAS", 213),
        ComponentDef("CLI_HISTORIALES", "Historiales", "ACCION", "CLINICA", None, "AMBOS", "MENU_MASCOTAS", 214),
        ComponentDef("CLI_CONSULTAS", "Consultas clínicas", "ACCION", "CLINICA", None, "AMBOS", "MENU_CITAS", 215),
        ComponentDef("CLI_ARCHIVOS", "Archivos clínicos", "ACCION", "CLINICA", None, "WEB", "MENU_CITAS", 216),
        ComponentDef("CLI_RECETAS", "Recetas", "ACCION", "CLINICA", None, "AMBOS", "MENU_CITAS", 217),
        ComponentDef("CLI_TRATAMIENTOS", "Tratamientos", "ACCION", "CLINICA", None, "AMBOS", "MENU_CITAS", 218),
        ComponentDef("CLI_VACUNAS", "Vacunas", "ACCION", "CLINICA", None, "AMBOS", "MENU_CITAS", 219),
        ComponentDef("CLI_PLAN_SANITARIO", "Plan sanitario preventivo", "ACCION", "CLINICA", None, "AMBOS", "MENU_CITAS", 2191),
        ComponentDef("SERV_CATEGORIAS", "Categorías servicios", "ACCION", "SERVICIOS", None, "WEB", "MENU_SERVICIOS", 220),
        ComponentDef("SERV_SERVICIOS", "Servicios", "ACCION", "SERVICIOS", None, "AMBOS", "MENU_SERVICIOS", 221),
        ComponentDef("SERV_PRECIOS", "Precios servicios", "ACCION", "SERVICIOS", None, "AMBOS", "MENU_SERVICIOS", 222),
        ComponentDef("SERV_CITAS", "Citas y agenda", "ACCION", "SERVICIOS", None, "AMBOS", "MENU_CITAS", 223),
        ComponentDef("INV_PRODUCTOS", "Inventario productos", "ACCION", "INVENTARIO", None, "WEB", "MENU_SERVICIOS", 224),
        # MOVIL
        ComponentDef("MOVIL_HOME", "Inicio móvil", "MENU", "MOVIL_APP", "/home", "MOVIL", None, 300),
        ComponentDef("MOVIL_MI_PERFIL", "Mi perfil", "MENU", "MOVIL_APP", "/perfil", "MOVIL", None, 301),
        ComponentDef("MOVIL_MIS_MASCOTAS", "Mis mascotas", "MENU", "MOVIL_APP", "/mascotas", "MOVIL", None, 302),
        ComponentDef("MOVIL_CREAR_MASCOTA", "Crear mascota móvil", "BOTON", "MOVIL_APP", None, "MOVIL", "MOVIL_MIS_MASCOTAS", 303),
        ComponentDef("MOVIL_EDITAR_MASCOTA", "Editar mascota móvil", "BOTON", "MOVIL_APP", None, "MOVIL", "MOVIL_MIS_MASCOTAS", 304),
        ComponentDef("MOVIL_CATALOGO_SERVICIOS", "Catálogo servicios móvil", "MENU", "MOVIL_APP", "/servicios", "MOVIL", None, 305),
        ComponentDef("MOVIL_SOLICITAR_CITA", "Solicitar cita móvil", "BOTON", "MOVIL_APP", None, "MOVIL", "MOVIL_CATALOGO_SERVICIOS", 306),
        ComponentDef("MOVIL_MIS_RESERVAS", "Mis reservas móvil", "MENU", "MOVIL_APP", "/reservas", "MOVIL", None, 307),
        ComponentDef("MOVIL_CANCELAR_RESERVA", "Cancelar reserva móvil", "BOTON", "MOVIL_APP", None, "MOVIL", "MOVIL_MIS_RESERVAS", 308),
        ComponentDef("MOVIL_HISTORIAL_MASCOTA", "Historial mascota móvil", "MENU", "MOVIL_APP", "/historial", "MOVIL", None, 309),
        ComponentDef("MOVIL_NOTIFICACIONES", "Notificaciones móvil", "MENU", "MOVIL_APP", "/notificaciones", "MOVIL", None, 310),
        # SAAS / SuperAdmin
        ComponentDef("MENU_SAAS_DASHBOARD", "SaaS dashboard", "MENU", "SAAS", "/saas", "WEB", None, 400),
        ComponentDef("MENU_SAAS_VETERINARIAS", "SaaS veterinarias", "MENU", "SAAS", "/saas/veterinarias", "WEB", None, 401),
        ComponentDef("MENU_SAAS_PLANES", "SaaS planes", "MENU", "SAAS", "/saas/planes", "WEB", None, 402),
        ComponentDef("MENU_SAAS_SUSCRIPCIONES", "SaaS suscripciones", "MENU", "SAAS", "/saas/suscripciones", "WEB", None, 403),
        ComponentDef("MENU_SAAS_USUARIOS_GLOBALES", "SaaS usuarios globales", "MENU", "SAAS", "/saas/usuarios", "WEB", None, 404),
        ComponentDef("MENU_SAAS_BITACORA_GLOBAL", "SaaS bitácora global", "MENU", "SAAS", "/saas/bitacora", "WEB", None, 405),
        ComponentDef("BTN_CREAR_VETERINARIA", "Crear veterinaria", "BOTON", "SAAS", None, "WEB", "MENU_SAAS_VETERINARIAS", 406),
        ComponentDef("BTN_EDITAR_VETERINARIA", "Editar veterinaria", "BOTON", "SAAS", None, "WEB", "MENU_SAAS_VETERINARIAS", 407),
        ComponentDef("BTN_ACTIVAR_VETERINARIA", "Activar veterinaria", "BOTON", "SAAS", None, "WEB", "MENU_SAAS_VETERINARIAS", 408),
        ComponentDef("BTN_DESACTIVAR_VETERINARIA", "Desactivar veterinaria", "BOTON", "SAAS", None, "WEB", "MENU_SAAS_VETERINARIAS", 409),
        ComponentDef("BTN_CREAR_PLAN", "Crear plan", "BOTON", "SAAS", None, "WEB", "MENU_SAAS_PLANES", 410),
        ComponentDef("BTN_EDITAR_PLAN", "Editar plan", "BOTON", "SAAS", None, "WEB", "MENU_SAAS_PLANES", 411),
        ComponentDef("BTN_CREAR_SUSCRIPCION", "Crear suscripción", "BOTON", "SAAS", None, "WEB", "MENU_SAAS_SUSCRIPCIONES", 412),
    ]

    ADMIN_ALL_CODES: Set[str] = {item.codigo for item in COMPONENTS if item.plataforma in {"WEB", "AMBOS"}}
    VET_CODES: Set[str] = {
        "MENU_DASHBOARD",
        "MENU_MASCOTAS",
        "MENU_CITAS",
        "CLI_MASCOTAS",
        "CLI_CATALOGOS",
        "CLI_HISTORIALES",
        "CLI_CONSULTAS",
        "CLI_ARCHIVOS",
        "CLI_RECETAS",
        "CLI_TRATAMIENTOS",
        "CLI_VACUNAS",
        "CLI_PLAN_SANITARIO",
        "SERV_CITAS",
    }
    RECEPCION_CODES: Set[str] = {
        "MENU_DASHBOARD",
        "MENU_CLIENTES",
        "MENU_MASCOTAS",
        "MENU_SERVICIOS",
        "MENU_CITAS",
        "MENU_RESERVAS",
        "CLI_CLIENTES",
        "CLI_MASCOTAS",
        "CLI_CATALOGOS",
        "SERV_SERVICIOS",
        "SERV_PRECIOS",
        "SERV_CITAS",
    }
    CLIENT_CODES: Set[str] = {
        "MOVIL_HOME",
        "MOVIL_MI_PERFIL",
        "MOVIL_MIS_MASCOTAS",
        "MOVIL_CREAR_MASCOTA",
        "MOVIL_EDITAR_MASCOTA",
        "MOVIL_CATALOGO_SERVICIOS",
        "MOVIL_SOLICITAR_CITA",
        "MOVIL_MIS_RESERVAS",
        "MOVIL_CANCELAR_RESERVA",
        "MOVIL_HISTORIAL_MASCOTA",
        "MOVIL_NOTIFICACIONES",
        "CLI_CLIENTES",
        "CLI_MASCOTAS",
        "CLI_CATALOGOS",
        "CLI_HISTORIALES",
        "SERV_CITAS",
        "SERV_SERVICIOS",
        "SERV_PRECIOS",
    }

    @classmethod
    def _get_permission_codes_by_role(cls, role: str) -> Set[str]:
        if role == cls.ROLE_ADMIN:
            return cls.ADMIN_ALL_CODES
        if role == cls.ROLE_VET:
            return cls.VET_CODES
        if role == cls.ROLE_RECEPTION:
            return cls.RECEPCION_CODES
        if role == cls.ROLE_CLIENT:
            return cls.CLIENT_CODES
        return set()

    @classmethod
    @transaction.atomic
    def seed_global_components(cls) -> Dict[str, int]:
        created = 0
        updated = 0

        by_code: Dict[str, ComponenteSistema] = {
            c.codigo: c for c in ComponenteSistema.objects.all()
        }

        # Primero creamos/actualizamos sin padre.
        for comp in cls.COMPONENTS:
            obj, was_created = ComponenteSistema.objects.update_or_create(
                codigo=comp.codigo,
                defaults={
                    "nombre": comp.nombre,
                    "tipo": comp.tipo,
                    "modulo": comp.modulo,
                    "ruta": comp.ruta,
                    "plataforma": comp.plataforma,
                    "orden": comp.orden,
                    "estado": True,
                },
            )
            by_code[comp.codigo] = obj
            if was_created:
                created += 1
            else:
                updated += 1

        # Luego conectamos padres.
        for comp in cls.COMPONENTS:
            if not comp.padre_codigo:
                continue
            obj = by_code[comp.codigo]
            parent = by_code.get(comp.padre_codigo)
            if parent and obj.padre_id != parent.id_componente:
                obj.padre = parent
                obj.save(update_fields=["padre"])

        return {"created": created, "updated": updated, "total": len(cls.COMPONENTS)}

    @classmethod
    @transaction.atomic
    def seed_base_groups_for_veterinaria(cls, veterinaria: Veterinaria) -> Dict[str, int]:
        created = 0
        updated = 0

        for role, group_name in cls.GROUP_BY_ROLE.items():
            _, was_created = GrupoUsuario.objects.update_or_create(
                veterinaria=veterinaria,
                rol_base=role,
                defaults={
                    "nombre": group_name,
                    "descripcion": f"Grupo base automático para rol {role}.",
                    "estado": True,
                    "es_base": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated}

    @classmethod
    @transaction.atomic
    def seed_base_permissions_for_veterinaria(cls, veterinaria: Veterinaria) -> Dict[str, int]:
        created = 0
        updated = 0

        component_map = {c.codigo: c for c in ComponenteSistema.objects.filter(estado=True)}
        groups = GrupoUsuario.objects.filter(veterinaria=veterinaria, es_base=True, estado=True)

        for group in groups:
            allowed_codes = cls._get_permission_codes_by_role((group.rol_base or "").upper())
            for code, component in component_map.items():
                allowed = code in allowed_codes
                defaults = {
                    "puede_ver": allowed,
                    "puede_crear": allowed and component.tipo in {"BOTON", "ACCION"},
                    "puede_editar": allowed and component.tipo in {"BOTON", "ACCION"},
                    "puede_eliminar": allowed and component.tipo in {"BOTON", "ACCION"},
                    "puede_exportar": allowed and code in {"BTN_EXPORTAR_BITACORA"},
                    "puede_ejecutar": allowed and component.tipo in {"ACCION", "BOTON"},
                    "estado": True,
                }
                # Cliente puede editar su propio perfil móvil (endpoint /clientes/me/),
                # sin abrir edición administrativa de otros clientes.
                if (group.rol_base or "").upper() == cls.ROLE_CLIENT and code == "MOVIL_MI_PERFIL":
                    defaults["puede_editar"] = True

                # Cliente puede gestionar sus reservas desde móvil.
                # Se habilita editar/ejecutar en el menú para compatibilidad de UI;
                # las acciones reales siguen protegidas por SERV_CITAS + tenant.
                if (group.rol_base or "").upper() == cls.ROLE_CLIENT and code == "MOVIL_MIS_RESERVAS":
                    defaults["puede_editar"] = True
                    defaults["puede_ejecutar"] = True
                _, was_created = GrupoPermisoComponente.objects.update_or_create(
                    grupo=group,
                    componente=component,
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        return {"created": created, "updated": updated}

    @classmethod
    @transaction.atomic
    def assign_existing_users_to_base_groups(cls, veterinaria: Veterinaria) -> Dict[str, int]:
        created = 0

        base_groups = {
            g.rol_base: g
            for g in GrupoUsuario.objects.filter(
                veterinaria=veterinaria, es_base=True, estado=True
            )
        }

        users = User.objects.filter(veterinaria=veterinaria, is_active=True).select_related("role")
        for user in users:
            role_name = (user.role.nombre or "").upper() if user.role_id else ""
            group = base_groups.get(role_name)
            if not group:
                continue
            _, was_created = UsuarioGrupo.objects.get_or_create(
                usuario=user,
                grupo=group,
                defaults={"estado": True},
            )
            if was_created:
                created += 1

        return {"created": created}

    @classmethod
    def seed_for_veterinarias(
        cls, veterinarias: Iterable[Veterinaria], assign_existing: bool = False
    ) -> Dict[str, int]:
        v_count = 0
        g_created = 0
        p_created = 0
        a_created = 0

        for vet in veterinarias:
            v_count += 1
            grp = cls.seed_base_groups_for_veterinaria(vet)
            perm = cls.seed_base_permissions_for_veterinaria(vet)
            g_created += grp["created"]
            p_created += perm["created"]
            if assign_existing:
                asg = cls.assign_existing_users_to_base_groups(vet)
                a_created += asg["created"]

        return {
            "veterinarias": v_count,
            "groups_created": g_created,
            "permissions_created": p_created,
            "assignments_created": a_created,
        }
