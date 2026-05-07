import os
import django
import sys
from datetime import date, timedelta

# Configuración de Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')
django.setup()

from django.db import connection
from apps.AutenticacionySeguridad.models import (
    Rol, User, Perfil, Veterinaria, PlanSuscripcion, Suscripcion,
    GrupoUsuario, ComponenteSistema, GrupoPermisoComponente, UsuarioGrupo
)
from apps.GestionServiciosyReserva.models.especie import Especie
from apps.GestionServiciosyReserva.models.raza import Raza

def reset_sequence(table_name, pk_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table_name}', '{pk_name}'), COALESCE(max({pk_name}), 1), max({pk_name}) IS NOT null) FROM {table_name};")

def seed():
    print("Iniciando carga de datos de prueba SaaS...")
    
    # 1. Resetear secuencias
    tables = [
        ('roles', 'id_rol'),
        ('usuarios', 'id_usuario'),
        ('veterinaria', 'id_veterinaria'),
        ('plan_suscripcion', 'id_plan'),
        ('suscripcion', 'id_suscripcion'),
        ('componente_sistema', 'id_componente'),
        ('grupo_usuario', 'id_grupo'),
        ('grupo_permiso_componente', 'id_permiso_componente'),
        ('especie', 'id_especie'),
        ('raza', 'id_raza')
    ]
    for table, pk in tables:
        try:
            reset_sequence(table, pk)
        except:
            pass

    # 2. Crear Roles Base
    roles_data = [
        ("SUPERADMIN", "Administrador Global del SaaS"),
        ("ADMIN", "Administrador de Veterinaria"),
        ("VETERINARIAN", "Personal Médico"),
        ("RECEPCIONISTA", "Personal de Atención"),
        ("CLIENT", "Cliente / Dueño de Mascota"),
    ]
    for nombre, desc in roles_data:
        Rol.objects.get_or_create(nombre=nombre, defaults={"descripcion": desc})
    
    rol_admin = Rol.objects.get(nombre="ADMIN")
    rol_vet = Rol.objects.get(nombre="VETERINARIAN")
    rol_super = Rol.objects.get(nombre="SUPERADMIN")

    # 3. Crear Plan de Suscripción
    plan, _ = PlanSuscripcion.objects.get_or_create(
        nombre="Premium Test",
        defaults={
            "descripcion": "Plan completo para pruebas",
            "precio_mensual": 99.99,
            "limite_usuarios": 10,
            "limite_mascotas": 100,
            "permite_app_movil": True
        }
    )

    # 4. Crear Veterinaria "PetCare"
    vet, _ = Veterinaria.objects.get_or_create(
        slug="petcare",
        defaults={
            "nombre": "PetCare Veterinaria",
            "nit": "123456789",
            "correo": "contacto@petcare.com",
            "telefono": "555-0101",
            "direccion": "Av. Principal 123",
            "permite_auto_registro_clientes": True,
            "estado": True
        }
    )

    # 5. Crear Suscripción Activa
    Suscripcion.objects.get_or_create(
        veterinaria=vet,
        plan=plan,
        defaults={
            "fecha_inicio": date.today(),
            "fecha_fin": date.today() + timedelta(days=365),
            "estado_suscripcion": "ACTIVA",
        }
    )

    # 6. Crear Grupos de la Veterinaria
    grupo_admins, _ = GrupoUsuario.objects.get_or_create(
        nombre="Administradores PetCare",
        veterinaria=vet,
        defaults={"descripcion": "Grupo con acceso total"}
    )
    grupo_vets, _ = GrupoUsuario.objects.get_or_create(
        nombre="Veterinarios PetCare",
        veterinaria=vet,
        defaults={"descripcion": "Grupo para personal médico"}
    )

    # 7. Crear Usuarios
    # Admin
    admin_user, _ = User.objects.get_or_create(
        correo="admin@petcare.com",
        defaults={
            "password": "petcarepassword",
            "role": rol_admin,
            "veterinaria": vet,
            "is_active": True
        }
    )
    if not admin_user.password.startswith('pbkdf2_'):
        admin_user.set_password("petcarepassword")
        admin_user.save()
    UsuarioGrupo.objects.get_or_create(usuario=admin_user, grupo=grupo_admins)
    Perfil.objects.get_or_create(
        usuario=admin_user,
        defaults={
            "nombre": "Administrador PetCare",
            "telefono": "70000001",
            "direccion": "Av. Principal 123",
        }
    )

    # Veterinario
    vet_user, _ = User.objects.get_or_create(
        correo="veterinario@petcare.com",
        defaults={
            "password": "vetpassword",
            "role": rol_vet,
            "veterinaria": vet,
            "is_active": True
        }
    )
    if not vet_user.password.startswith('pbkdf2_'):
        vet_user.set_password("vetpassword")
        vet_user.save()
    UsuarioGrupo.objects.get_or_create(usuario=vet_user, grupo=grupo_vets)
    Perfil.objects.get_or_create(
        usuario=vet_user,
        defaults={
            "nombre": "Dr. Veterinario PetCare",
            "telefono": "70000002",
            "direccion": "Av. Principal 124",
        }
    )

    # SuperAdmin
    super_user, _ = User.objects.get_or_create(
        correo="superadmin@pethome.com",
        defaults={
            "password": "adminpassword",
            "role": rol_super,
            "is_superuser": True,
            "is_active": True
        }
    )
    if not super_user.password.startswith('pbkdf2_'):
        super_user.set_password("adminpassword")
        super_user.save()

    # 8. Componentes del Sistema
    comps_data = [
        ("CLI_CLIENTES", "Gestión de Clientes", "Módulo para administrar los dueños de mascotas."),
        ("CLI_MASCOTAS", "Gestión de Mascotas", "Módulo para administrar las mascotas de los clientes."),
        ("CLI_CATALOGOS", "Catálogos Base", "Módulo para administrar especies, razas, etc."),
        ("SEG_USUARIOS", "Gestión de Usuarios", "Administración interna de personal de la veterinaria."),
        ("SEG_GRUPO_USUARIO", "Roles y Grupos", "Gestión de roles/grupos de acceso de la veterinaria."),
        ("SEG_PERMISO_COMPONENTE", "Permisos por Componente", "Asignación de permisos granulares por módulo."),
        ("SEG_BITACORA", "Bitácora y Seguridad", "Consulta de registros de auditoría del sistema."),
        ("SERV_SERVICIOS", "Catálogo de Servicios", "Catálogo de servicios y precios."),
        ("SERV_CITAS", "Gestión de Citas y Reservas", "Módulo para agendar citas de mascotas."),
    ]
    
    comps = {}
    for cod, nom, desc in comps_data:
        c, _ = ComponenteSistema.objects.get_or_create(
            codigo=cod,
            defaults={"nombre": nom, "tipo": "MODULO"}
        )
        comps[cod] = c

    # 9. Asignar Permisos
    # Admin: Todo True
    for c in comps.values():
        GrupoPermisoComponente.objects.update_or_create(
            grupo=grupo_admins,
            componente=c,
            defaults={
                "puede_ver": True,
                "puede_crear": True,
                "puede_editar": True,
                "puede_eliminar": True,
            }
        )

    # Veterinario: Clientes (Ver), Mascotas (Ver, Crear, Editar), Catálogos (Ver), Servicios (Ver), Citas (Ver, Crear, Editar), Usuarios (Ver)
    permissions_vet = [
        ("CLI_CLIENTES", True, False, False, False),
        ("CLI_MASCOTAS", True, True, True, False),
        ("CLI_CATALOGOS", True, False, False, False),
        ("SERV_SERVICIOS", True, False, False, False),
        ("SERV_CITAS", True, True, True, False),
        ("SEG_USUARIOS", True, False, False, False),
    ]
    for cod, v, c, ed, el in permissions_vet:
        if cod in comps:
            GrupoPermisoComponente.objects.update_or_create(
                grupo=grupo_vets,
                componente=comps[cod],
                defaults={
                    "puede_ver": v,
                    "puede_crear": c,
                    "puede_editar": ed,
                    "puede_eliminar": el,
                }
            )

    # 10. Sembrar Especies y Razas (Catálogos)
    print("Sembrando Catálogos de Especies y Razas...")
    catalogos_data = [
        ("Canino", ["Poodle", "Pastor Alemán", "Golden Retriever", "Chihuahua", "Bulldog"]),
        ("Felino", ["Siamés", "Persa", "Maine Coon", "Bengalí", "Común"]),
        ("Ave", ["Canario", "Loro", "Perico"]),
        ("Roedor", ["Hamster", "Cuy", "Conejo"]),
    ]

    for esp_nom, razas in catalogos_data:
        especie, _ = Especie.objects.get_or_create(nombre=esp_nom)
        for raza_nom in razas:
            Raza.objects.get_or_create(nombre=raza_nom, especie=especie)

    print("Carga de datos SaaS finalizada con éxito.")

if __name__ == "__main__":
    seed()
