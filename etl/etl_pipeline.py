from datetime import datetime
from database import get_neon_conn
from clusters import get_mongo_db, clusters_configurados


def _str_id(val):
    return str(val) if val is not None else None


def _get_any(doc, *keys, default=None):
    for k in keys:
        if k in doc and doc[k] is not None:
            return doc[k]
    return default


def _purgar_huerfanos(cur, tabla, ids_vistos):
    """Borra de Neon los registros cuyo mongo_id ya no existe en MongoDB."""
    if not ids_vistos:
        cur.execute(f"DELETE FROM {tabla};")
    else:
        cur.execute(
            f"DELETE FROM {tabla} WHERE NOT (mongo_id = ANY(%s::text[]));",
            (list(ids_vistos),),
        )
    return cur.rowcount


def ejecutar_etl(on_fase=None):
    """
    Sincroniza TODOS los clusters de MongoDB (A y, si está configurado, B) hacia
    un único Neon PostgreSQL.

    on_fase(nombre) es opcional y avisa las fases reales para la animación:
      "mongo_a_etl"     -> leyendo documentos de los clusters
      "etl_a_postgres"  -> transformando y cargando en Neon

    Si algún cluster configurado no responde, el ETL falla completo y hace rollback:
    así NUNCA se borra de Neon lo que solo vive en el cluster caído.
    """
    def _fase(nombre):
        if on_fase:
            try:
                on_fase(nombre)
            except Exception:
                pass

    inicio = datetime.utcnow()
    conn = get_neon_conn()
    cur = conn.cursor()

    procesados = 0
    eliminados = 0
    errores = 0
    detalle_error = None
    bitacora_id = None
    nombres_clusters = []

    try:
        cur.execute(
            """
            INSERT INTO etl_bitacora (fecha_inicio, estado, registros_procesados, registros_eliminados, errores)
            VALUES (%s, %s, 0, 0, 0)
            RETURNING ejecucion_id;
            """,
            (inicio, "EN_EJECUCION"),
        )
        bitacora_id = cur.fetchone()[0]
        conn.commit()

        # ------------------------------------------------------
        # EXTRACCIÓN: se lee todo de todos los clusters
        # ------------------------------------------------------
        _fase("mongo_a_etl")
        dbs = [(nombre, get_mongo_db(nombre)) for nombre in clusters_configurados()]
        nombres_clusters = [nombre for nombre, _ in dbs]

        def _leer(coleccion):
            # Un mismo _id puede existir en A y en B (datos base copiados con sembrar_cluster_b.py):
            # se procesa una sola vez y, si hay conflicto, gana el cluster A (el principal).
            por_id = {}
            for _, mdb in dbs:
                for doc in mdb[coleccion].find():
                    por_id.setdefault(doc["_id"], doc)
            return list(por_id.values())

        docs_categorias = _leer("categorias")
        docs_servicios = _leer("servicios")
        docs_usuarios = _leer("usuarios")
        docs_tutores = _leer("tutores")
        docs_mascotas = _leer("mascotas")
        docs_citas = _leer("citas")
        docs_historial = _leer("historial")

        # ------------------------------------------------------
        # TRANSFORMACIÓN Y CARGA
        # ------------------------------------------------------
        _fase("etl_a_postgres")

        map_categorias = {}
        map_servicios = {}
        map_usuarios = {}
        map_tutores = {}
        map_mascotas = {}  # mongo_id -> (mascota_id_neon, tutor_id_neon)

        # mongo_ids que existen HOY en Mongo (en cualquiera de los clusters)
        vistos = {
            "categorias": set(),
            "servicios": set(),
            "tutores": set(),
            "mascotas": set(),
            "citas": set(),
            "historial_clinico": set(),
        }

        # 1. CATEGORIAS
        for doc in docs_categorias:
            mid = _str_id(doc.get("_id"))
            especie = _get_any(doc, "especie", "nombre", default="General")
            descripcion = _get_any(doc, "descripcion", default="")
            activa = bool(_get_any(doc, "activa", "activo", default=True))

            cur.execute(
                """
                INSERT INTO categorias (mongo_id, especie, descripcion, activa, sincronizado_en)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (mongo_id) DO UPDATE SET
                    especie = EXCLUDED.especie,
                    descripcion = EXCLUDED.descripcion,
                    activa = EXCLUDED.activa,
                    sincronizado_en = CURRENT_TIMESTAMP
                RETURNING categoria_id;
                """,
                (mid, especie, descripcion, activa),
            )
            map_categorias[mid] = cur.fetchone()[0]
            vistos["categorias"].add(mid)
            procesados += 1

        # 2. SERVICIOS
        for doc in docs_servicios:
            mid = _str_id(doc.get("_id"))
            nombre = _get_any(doc, "nombre", default="Servicio")
            tipo = _get_any(doc, "tipo", "categoria", default="general")
            duracion = int(_get_any(doc, "duracionMin", "duracion_min", "duracion", default=30) or 30)
            precio = float(_get_any(doc, "precio", "costo", default=0.0) or 0.0)
            activo = bool(_get_any(doc, "activo", "activa", default=True))

            cur.execute(
                """
                INSERT INTO servicios (mongo_id, nombre, tipo, duracion_min, precio, activo, sincronizado_en)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (mongo_id) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    tipo = EXCLUDED.tipo,
                    duracion_min = EXCLUDED.duracion_min,
                    precio = EXCLUDED.precio,
                    activo = EXCLUDED.activo,
                    sincronizado_en = CURRENT_TIMESTAMP
                RETURNING servicio_id;
                """,
                (mid, nombre, tipo, duracion, precio, activo),
            )
            map_servicios[mid] = cur.fetchone()[0]
            vistos["servicios"].add(mid)
            procesados += 1

        # 3. USUARIOS (sin DELETE previo para no chocar con FK de citas/historial)
        for doc in docs_usuarios:
            mid = _str_id(doc.get("_id"))
            nombre = _get_any(doc, "nombre", default="Usuario")
            apellidos = _get_any(doc, "apellidos", "apellido", default="")
            email = _get_any(doc, "email", "correo", default=f"{mid}@veterinaria.local")
            telefono = _get_any(doc, "telefono", default="")
            rol = _get_any(doc, "rol", default="veterinario")
            especialidad = _get_any(doc, "especialidad", default=None)
            cedula = _get_any(doc, "cedulaProfesional", "cedula_profesional", default=None)
            activo = bool(_get_any(doc, "activo", default=True))
            creado_en = _get_any(doc, "creadoEn", "creado_en", default=inicio)

            cur.execute(
                """
                INSERT INTO usuarios (
                    mongo_id, nombre, apellidos, email, telefono, rol,
                    especialidad, cedula_profesional, activo, creado_en, sincronizado_en
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (mongo_id) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    apellidos = EXCLUDED.apellidos,
                    email = EXCLUDED.email,
                    telefono = EXCLUDED.telefono,
                    rol = EXCLUDED.rol,
                    especialidad = EXCLUDED.especialidad,
                    cedula_profesional = EXCLUDED.cedula_profesional,
                    activo = EXCLUDED.activo,
                    sincronizado_en = CURRENT_TIMESTAMP
                RETURNING usuario_id;
                """,
                (mid, nombre, apellidos, email, telefono, rol, especialidad, cedula, activo, creado_en),
            )
            map_usuarios[mid] = cur.fetchone()[0]
            procesados += 1

        # 4. TUTORES Y DIRECCIONES
        mascotas_embebidas = []
        for doc in docs_tutores:
            mid = _str_id(doc.get("_id"))
            nombre = _get_any(doc, "nombre", default="Tutor")
            apellidos = _get_any(doc, "apellidos", "apellido", default="")
            telefono = _get_any(doc, "telefono", default="")
            email = _get_any(doc, "email", "correo", default=None)
            activo = bool(_get_any(doc, "activo", default=True))
            creado_en = _get_any(doc, "creadoEn", "creado_en", default=inicio)

            cur.execute(
                """
                INSERT INTO tutores (mongo_id, nombre, apellidos, telefono, email, activo, creado_en, sincronizado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (mongo_id) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    apellidos = EXCLUDED.apellidos,
                    telefono = EXCLUDED.telefono,
                    email = EXCLUDED.email,
                    activo = EXCLUDED.activo,
                    sincronizado_en = CURRENT_TIMESTAMP
                RETURNING tutor_id;
                """,
                (mid, nombre, apellidos, telefono, email, activo, creado_en),
            )
            tutor_neon_id = cur.fetchone()[0]
            map_tutores[mid] = tutor_neon_id
            vistos["tutores"].add(mid)
            procesados += 1

            dir_obj = doc.get("direccion")
            if isinstance(dir_obj, dict):
                cur.execute(
                    """
                    INSERT INTO tutor_direcciones (tutor_id, calle, colonia, ciudad, estado, cp)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tutor_id) DO UPDATE SET
                        calle = EXCLUDED.calle,
                        colonia = EXCLUDED.colonia,
                        ciudad = EXCLUDED.ciudad,
                        estado = EXCLUDED.estado,
                        cp = EXCLUDED.cp;
                    """,
                    (
                        tutor_neon_id,
                        dir_obj.get("calle"),
                        dir_obj.get("colonia"),
                        dir_obj.get("ciudad"),
                        dir_obj.get("estado"),
                        dir_obj.get("cp"),
                    ),
                )
            else:
                cur.execute("DELETE FROM tutor_direcciones WHERE tutor_id = %s;", (tutor_neon_id,))

            if isinstance(doc.get("mascotas"), list):
                for m in doc["mascotas"]:
                    m_copy = dict(m)
                    m_copy["_tutor_mongo_id"] = mid
                    mascotas_embebidas.append(m_copy)

        # 5. MASCOTAS Y ALERGIAS
        if not docs_mascotas and mascotas_embebidas:
            docs_mascotas = mascotas_embebidas

        categoria_fallback = next(iter(map_categorias.values()), None)
        tutor_fallback = next(iter(map_tutores.values()), None)

        for doc in docs_mascotas:
            mid = _str_id(_get_any(doc, "_id", "mascotaId", "mascota_id"))
            tutor_mid = _str_id(_get_any(doc, "tutorId", "tutor_id", "_tutor_mongo_id"))
            cat_mid = _str_id(_get_any(doc, "categoriaId", "categoria_id"))

            tutor_neon_id = map_tutores.get(tutor_mid, tutor_fallback)
            cat_neon_id = map_categorias.get(cat_mid, categoria_fallback)

            if not mid or not tutor_neon_id or not cat_neon_id:
                continue

            nombre = _get_any(doc, "nombre", default="Mascota")
            raza = _get_any(doc, "raza", default="No especificada")
            sexo = _get_any(doc, "sexo", default=None)
            fecha_nac = _get_any(doc, "fechaNacimiento", "fecha_nacimiento", default=None)
            color = _get_any(doc, "color", default=None)
            peso = _get_any(doc, "pesoActualKg", "peso_actual_kg", "peso", default=None)
            esterilizada = bool(_get_any(doc, "esterilizada", default=False))
            activa = bool(_get_any(doc, "activa", "activo", default=True))
            creado_en = _get_any(doc, "creadoEn", "creado_en", default=inicio)

            cur.execute(
                """
                INSERT INTO mascotas (
                    mongo_id, tutor_id, categoria_id, nombre, raza, sexo,
                    fecha_nacimiento, color, peso_actual_kg, esterilizada, activa, creado_en, sincronizado_en
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (mongo_id) DO UPDATE SET
                    tutor_id = EXCLUDED.tutor_id,
                    categoria_id = EXCLUDED.categoria_id,
                    nombre = EXCLUDED.nombre,
                    raza = EXCLUDED.raza,
                    sexo = EXCLUDED.sexo,
                    fecha_nacimiento = EXCLUDED.fecha_nacimiento,
                    color = EXCLUDED.color,
                    peso_actual_kg = EXCLUDED.peso_actual_kg,
                    esterilizada = EXCLUDED.esterilizada,
                    activa = EXCLUDED.activa,
                    sincronizado_en = CURRENT_TIMESTAMP
                RETURNING mascota_id;
                """,
                (
                    mid, tutor_neon_id, cat_neon_id, nombre, raza, sexo,
                    fecha_nac, color, peso, esterilizada, activa, creado_en,
                ),
            )
            mascota_neon_id = cur.fetchone()[0]
            map_mascotas[mid] = (mascota_neon_id, tutor_neon_id)
            vistos["mascotas"].add(mid)
            procesados += 1

            alergias = doc.get("alergias")
            if isinstance(alergias, list):
                cur.execute("DELETE FROM mascota_alergias WHERE mascota_id = %s;", (mascota_neon_id,))
                for al in alergias:
                    if al:
                        cur.execute(
                            "INSERT INTO mascota_alergias (mascota_id, descripcion) VALUES (%s, %s);",
                            (mascota_neon_id, str(al)),
                        )

        mascota_fallback = next(iter(map_mascotas.values()), None)

        # 6. CITAS (con respaldo por si alguna cita apunta a una mascota ya borrada)
        for doc in docs_citas:
            mid = _str_id(doc.get("_id"))
            mascota_mid = _str_id(_get_any(doc, "mascotaId", "mascota_id"))
            tutor_mid = _str_id(_get_any(doc, "tutorId", "tutor_id"))
            usuario_mid = _str_id(_get_any(doc, "usuarioId", "usuario_id"))
            servicio_mid = _str_id(_get_any(doc, "servicioId", "servicio_id"))

            mascota_info = map_mascotas.get(mascota_mid) or mascota_fallback
            if not mascota_info:
                continue

            mascota_neon_id, tutor_desde_mascota = mascota_info
            tutor_neon_id = map_tutores.get(tutor_mid, tutor_desde_mascota)
            usuario_neon_id = map_usuarios.get(usuario_mid)
            servicio_neon_id = map_servicios.get(servicio_mid)

            tipo = _get_any(doc, "tipo", default="presencial")
            motivo = _get_any(doc, "motivo", default="")
            estado = _get_any(doc, "estado", default="confirmada")
            fecha_inicio = _get_any(doc, "fechaInicio", "fecha_inicio", default=inicio)
            fecha_fin = _get_any(doc, "fechaFin", "fecha_fin", default=fecha_inicio)
            creado_en = _get_any(doc, "creadoEn", "creado_en", default=inicio)
            actualizado_en = _get_any(doc, "actualizadoEn", "actualizado_en", default=creado_en)

            cur.execute(
                """
                INSERT INTO citas (
                    mongo_id, mascota_id, tutor_id, usuario_id, servicio_id,
                    tipo, motivo, estado, fecha_inicio, fecha_fin, creado_en, actualizado_en, sincronizado_en
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (mongo_id) DO UPDATE SET
                    mascota_id = EXCLUDED.mascota_id,
                    tutor_id = EXCLUDED.tutor_id,
                    usuario_id = EXCLUDED.usuario_id,
                    servicio_id = EXCLUDED.servicio_id,
                    tipo = EXCLUDED.tipo,
                    motivo = EXCLUDED.motivo,
                    estado = EXCLUDED.estado,
                    fecha_inicio = EXCLUDED.fecha_inicio,
                    fecha_fin = EXCLUDED.fecha_fin,
                    actualizado_en = EXCLUDED.actualizado_en,
                    sincronizado_en = CURRENT_TIMESTAMP;
                """,
                (
                    mid, mascota_neon_id, tutor_neon_id, usuario_neon_id, servicio_neon_id,
                    tipo, motivo, estado, fecha_inicio, fecha_fin, creado_en, actualizado_en,
                ),
            )
            vistos["citas"].add(mid)
            procesados += 1

        # 7. HISTORIAL CLÍNICO + SÍNTOMAS + TRATAMIENTOS
        for doc in docs_historial:
            mid = _str_id(doc.get("_id"))
            mascota_mid = _str_id(_get_any(doc, "mascotaId", "mascota_id"))
            usuario_mid = _str_id(_get_any(doc, "usuarioId", "usuario_id"))

            mascota_info = map_mascotas.get(mascota_mid) or mascota_fallback
            if not mascota_info:
                continue

            mascota_neon_id, tutor_neon_id = mascota_info
            usuario_neon_id = map_usuarios.get(usuario_mid)

            fecha = _get_any(doc, "fecha", default=inicio)
            motivo = _get_any(doc, "motivoConsulta", "motivo_consulta", default="")
            diagnostico = _get_any(doc, "diagnostico", default="")
            observaciones = _get_any(doc, "observaciones", default="")
            creado_en = _get_any(doc, "creadoEn", "creado_en", default=inicio)

            signos = doc.get("signosVitales") or {}
            peso_kg = signos.get("pesoKg") if isinstance(signos, dict) else None
            temp_c = signos.get("temperaturaC") if isinstance(signos, dict) else None
            fc = signos.get("frecuenciaCardiaca") if isinstance(signos, dict) else None
            fr = signos.get("frecuenciaRespiratoria") if isinstance(signos, dict) else None

            cur.execute(
                """
                INSERT INTO historial_clinico (
                    mongo_id, mascota_id, tutor_id, usuario_id, fecha,
                    motivo_consulta, diagnostico, observaciones,
                    peso_kg, temperatura_c, frecuencia_cardiaca, frecuencia_respiratoria,
                    creado_en, sincronizado_en
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (mongo_id) DO UPDATE SET
                    mascota_id = EXCLUDED.mascota_id,
                    tutor_id = EXCLUDED.tutor_id,
                    usuario_id = EXCLUDED.usuario_id,
                    fecha = EXCLUDED.fecha,
                    motivo_consulta = EXCLUDED.motivo_consulta,
                    diagnostico = EXCLUDED.diagnostico,
                    observaciones = EXCLUDED.observaciones,
                    peso_kg = EXCLUDED.peso_kg,
                    temperatura_c = EXCLUDED.temperatura_c,
                    frecuencia_cardiaca = EXCLUDED.frecuencia_cardiaca,
                    frecuencia_respiratoria = EXCLUDED.frecuencia_respiratoria,
                    sincronizado_en = CURRENT_TIMESTAMP
                RETURNING historial_id;
                """,
                (
                    mid, mascota_neon_id, tutor_neon_id, usuario_neon_id, fecha,
                    motivo, diagnostico, observaciones,
                    peso_kg, temp_c, fc, fr, creado_en,
                ),
            )
            historial_neon_id = cur.fetchone()[0]
            vistos["historial_clinico"].add(mid)
            procesados += 1

            sintomas = doc.get("sintomas")
            if isinstance(sintomas, list):
                cur.execute("DELETE FROM historial_sintomas WHERE historial_id = %s;", (historial_neon_id,))
                for s in sintomas:
                    if s:
                        cur.execute(
                            "INSERT INTO historial_sintomas (historial_id, descripcion) VALUES (%s, %s);",
                            (historial_neon_id, str(s)),
                        )

            tratamientos = doc.get("tratamientos")
            if isinstance(tratamientos, list):
                cur.execute("DELETE FROM historial_tratamientos WHERE historial_id = %s;", (historial_neon_id,))
                for t in tratamientos:
                    if t:
                        cur.execute(
                            "INSERT INTO historial_tratamientos (historial_id, indicacion) VALUES (%s, %s);",
                            (historial_neon_id, str(t)),
                        )

        # 8. LIMPIEZA DE REGISTROS ELIMINADOS EN MONGODB (en cualquiera de los clusters)
        for tabla in [
            "historial_clinico",
            "citas",
            "mascotas",
            "tutores",
            "servicios",
            "categorias",
        ]:
            eliminados += _purgar_huerfanos(cur, tabla, vistos[tabla])

        fin = datetime.utcnow()
        cur.execute(
            """
            UPDATE etl_bitacora
            SET fecha_fin = %s, estado = %s, registros_procesados = %s,
                registros_eliminados = %s, errores = %s
            WHERE ejecucion_id = %s;
            """,
            (fin, "SINCRONIZADO", procesados, eliminados, errores, bitacora_id),
        )
        conn.commit()
        print(f"[ETL OK] Clusters: {'+'.join(nombres_clusters)} | Procesados: {procesados} | Eliminados: {eliminados}")

        return {
            "success": True,
            "estado": "Sincronizado",
            "clusters": nombres_clusters,
            "registros_procesados": procesados,
            "registros_eliminados": eliminados,
            "errores": errores,
            "ultima_sincronizacion": fin.isoformat(),
        }

    except Exception as e:
        conn.rollback()
        errores += 1
        detalle_error = str(e)
        print(f"[ETL ERROR] {detalle_error}")
        fin = datetime.utcnow()
        if bitacora_id:
            try:
                cur.execute(
                    """
                    UPDATE etl_bitacora
                    SET fecha_fin = %s, estado = %s, registros_procesados = %s,
                        registros_eliminados = %s, errores = %s, detalle_error = %s
                    WHERE ejecucion_id = %s;
                    """,
                    (fin, "ERROR", procesados, eliminados, errores, detalle_error, bitacora_id),
                )
                conn.commit()
            except Exception:
                pass
        return {
            "success": False,
            "estado": "Error",
            "clusters": nombres_clusters,
            "registros_procesados": procesados,
            "registros_eliminados": eliminados,
            "errores": errores,
            "error": detalle_error,
            "ultima_sincronizacion": fin.isoformat(),
        }
    finally:
        cur.close()
        conn.close()
