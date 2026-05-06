class ComponenteTreeService:
    @staticmethod
    def build_context_tree(componentes_planos):
        """
        Toma una lista de componentes (con sus permisos calculados) 
        y devuelve un árbol recursivo incluyendo los padres necesarios.
        """
        # 1. Asegurar que los padres estén incluidos
        componentes_completos = ComponenteTreeService._incluir_padres(componentes_planos)
        
        # 2. Construir estructura de árbol
        arbol = ComponenteTreeService._convertir_a_arbol(componentes_completos)
        
        return arbol

    @staticmethod
    def _incluir_padres(componentes_permitidos):
        ids_incluidos = set()
        resultado = []

        # Mapa para búsqueda rápida de datos ya calculados
        mapa_datos = {c["id_componente"]: c for c in componentes_permitidos}

        for c_data in componentes_permitidos:
            obj = c_data.get("_obj")
            ComponenteTreeService._agregar_recursivo(obj, mapa_datos, resultado, ids_incluidos)

        # Limpiar referencias a objetos de BD antes de retornar
        for item in resultado:
            item.pop("_obj", None)
            
        return resultado

    @staticmethod
    def _agregar_recursivo(obj, mapa_datos, resultado, ids_incluidos):
        if not obj or obj.id_componente in ids_incluidos:
            return

        # Si tiene padre, procesar el padre primero (para mantener orden topológico si se desea)
        if obj.id_padre:
            ComponenteTreeService._agregar_recursivo(obj.id_padre, mapa_datos, resultado, ids_incluidos)

        if obj.id_componente in mapa_datos:
            # Si el componente ya tenía permisos específicos, usarlos
            data = mapa_datos[obj.id_componente].copy()
        else:
            # Si se incluye solo por ser padre, darle permisos de solo 'ver'
            data = {
                "id_componente": obj.id_componente,
                "codigo": obj.codigo,
                "nombre": obj.nombre,
                "tipo": obj.tipo,
                "modulo": obj.modulo,
                "ruta": obj.ruta,
                "plataforma": obj.plataforma,
                "id_padre": obj.id_padre_id,
                "orden": obj.orden,
                "permisos": {
                    "ver": True, "crear": False, "editar": False, 
                    "eliminar": False, "exportar": False, "ejecutar": False
                }
            }

        resultado.append(data)
        ids_incluidos.add(obj.id_componente)

    @staticmethod
    def _convertir_a_arbol(lista_plana):
        mapa = {}
        raices = []

        # Inicializar nodos con lista de hijos vacía
        for item in lista_plana:
            item["children"] = []
            mapa[item["id_componente"]] = item

        # Organizar jerarquía
        for item in lista_plana:
            padre_id = item.get("id_padre")
            if padre_id and padre_id in mapa:
                mapa[padre_id]["children"].append(item)
            else:
                raices.append(item)

        # Ordenar cada nivel por el campo 'orden'
        ComponenteTreeService._ordenar_arbol(raices)
        return raices

    @staticmethod
    def _ordenar_arbol(nodos):
        nodos.sort(key=lambda x: x.get("orden", 0))
        for nodo in nodos:
            if nodo["children"]:
                ComponenteTreeService._ordenar_arbol(nodo["children"])
