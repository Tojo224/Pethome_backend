def obtener_snapshot_perfil(perfil):
    """Genera un snapshot del estado actual de un perfil de usuario para auditoría."""
    usuario = getattr(perfil, "usuario", None)
    rol = getattr(usuario, "role", None) if usuario else None
    return {
        "correo": getattr(usuario, "correo", None),
        "id_rol": getattr(rol, "id_rol", None),
        "rol": getattr(rol, "nombre", None),
        "estado": getattr(usuario, "is_active", None),
        "nombre": getattr(perfil, "nombre", None),
        "telefono": getattr(perfil, "telefono", None),
        "direccion": getattr(perfil, "direccion", None),
    }


def construir_metadatos_actualizacion_perfil(snapshot_antes, snapshot_despues, validated_data):
    """
    Compara dos snapshots y construye un diccionario con los cambios realizados.
    Útil para registrar exactamente qué cambió en la bitácora.
    """
    campos_enviados = sorted(list(validated_data.keys()))
    datos_anteriores = {}
    datos_actualizados = {}
    comparacion = {}

    for campo in campos_enviados:
        if campo == "password":
            datos_anteriores["password"] = "***"
            datos_actualizados["password"] = "***"
            comparacion["password"] = {
                "anterior": "***",
                "actualizado": "***",
            }
            continue

        if campo == "id_rol":
            id_rol_anterior = snapshot_antes.get("id_rol")
            id_rol_actualizado = snapshot_despues.get("id_rol")

            if id_rol_anterior != id_rol_actualizado:
                datos_anteriores["id_rol"] = id_rol_anterior
                datos_actualizados["id_rol"] = id_rol_actualizado
                comparacion["id_rol"] = {
                    "anterior": id_rol_anterior,
                    "actualizado": id_rol_actualizado,
                }

                rol_anterior = snapshot_antes.get("rol")
                rol_actualizado = snapshot_despues.get("rol")
                datos_anteriores["rol"] = rol_anterior
                datos_actualizados["rol"] = rol_actualizado
                comparacion["rol"] = {
                    "anterior": rol_anterior,
                    "actualizado": rol_actualizado,
                }
            continue

        valor_anterior = snapshot_antes.get(campo)
        valor_actualizado = snapshot_despues.get(campo)

        if valor_anterior != valor_actualizado:
            datos_anteriores[campo] = valor_anterior
            datos_actualizados[campo] = valor_actualizado
            comparacion[campo] = {
                "anterior": valor_anterior,
                "actualizado": valor_actualizado,
            }

    return {
        "campos_enviados": campos_enviados,
        "campos_actualizados": sorted(list(comparacion.keys())),
        "datos_anteriores": datos_anteriores,
        "datos_actualizados": datos_actualizados,
        "comparacion": comparacion,
    }
