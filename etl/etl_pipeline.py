from datetime import datetime
from database import get_mongo_db, get_neon_conn


def _str_id(val):
    return str(val) if val is not None else None


def _get_any(doc, *keys, default=None):
    for k in keys:
        if k in doc and doc[k] is not None:
            return doc[k]
    return default


def ejecutar_etl():
    """
    Extrae documentos de MongoDB (veterinaria), los transforma al modelo relacional
    y ejecuta UPSERT idempotente en Neon PostgreSQL (Veterinaria_DB).
    """
    inicio = datetime.utcnow()
    mongo_db = get_mongo_db()
    conn = get_neon_conn()
    cur = conn.cursor()

    procesados = 0
    errores = 0
    detalle_error = None
    bitacora_id = None

    try:
        # Registrar inicio en etl_bitacora
        cur.execute(
            """
            INSERT INTO etl_bitacora (fecha_inicio, estado, registros_procesados, errores)
            VALUES (%s, %s, 0, 0)
            RETURNING ejecucion_id;
            """,
            (inicio, "EN_EJECUCION"),
        )
        bitacora_id = cur.fetchone()[0]
        conn.commit()

        # Mapas mongo_id -> serial_id de Neon para resolver llaves foráneas rápido
        map_categorias = {}
        map_servicios = {}
        map_usuarios = {}
        map_tutores = {}
        map_mascotas = {}  # mongo_id -> (mascota_id_neon, tutor_id_neon)

        # ------------------------------------------------------
        # 1. CATEGORIAS
        # ------------------------------------------------------
        for doc in mongo_db.categorias.find():
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
            procesados += 1

        # ------------------------------------------------------
        # 2. SERVICIOS
        # ------------------------------------------------------
        for doc in mongo_db.servicios.find():
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
            procesados += 1

        # ------------------------------------------------------
        # 3. USUARIOS
        # ------------------------------------------------------
        for doc in mongo_db.usuarios.find():
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

        # ------------------------------------------------------
        # 4. TUTORES Y DIRECCIONES (y mascotas si vienen embebidas)
        # ------------------------------------------------------
        mascotas_embebidas = []
        for doc in mongo_db.tutores.find():
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
            procesados += 1

            # Dirección (si existe objeto direccion)
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

            # Si las mascotas vienen embebidas dentro del documento de tutor
            if isinstance(doc.get("mascotas"), list):
                for m in doc["mascotas"]:
                    m_copy = dict(m)
                    m_copy["_tutor_mongo_id"] = mid
                    mascotas_embebidas.append(m_copy)

        # ------------------------------------------------------
        # 5. MASCOTAS Y ALERGIAS (desde colección mascotas o embebidas)
        # ------------------------------------------------------
        docs_mascotas = list(mongo_db.mascotas.find()) if "mascotas" in mongo_db.list_collection_names() else []
        if not docs_mascotas and mascotas_embebidas:
            docs_mascotas = mascotas_embebidas

        categoria_fallback = next(iter(map_categorias.values()), None)

        for doc in docs_mascotas:
            mid = _str_id(_get_any(doc, "_id", "mascotaId", "mascota_id"))
            tutor_mid = _str_id(_get_any(doc, "tutorId", "tutor_id", "_tutor_mongo_id"))
            cat_mid = _str_id(_get_any(doc, "categoriaId", "categoria_id"))

            tutor_neon_id = map_tutores.get(tutor_mid)
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
            procesados += 1

            # Reemplazar alergias limpiamente
            alergias = doc.get("alergias")
            if isinstance(alergias, list):
                cur.execute("DELETE FROM mascota_alergias WHERE mascota_id = %s;", (mascota_neon_id,))
                for al in alergias:
                    if al:
                        cur.execute(
                            "INSERT INTO mascota_alergias (mascota_id, descripcion) VALUES (%s, %s);",
                            (mascota_neon_id, str(al)),
                        )

        # ------------------------------------------------------
        # 6. CITAS
        # ------------------------------------------------------
        for doc in mongo_db.citas.find():
            mid = _str_id(doc.get("_id"))
            mascota_mid = _str_id(_get_any(doc, "mascotaId", "mascota_id"))
            tutor_mid = _str_id(_get_any(doc, "tutorId", "tutor_id"))
            usuario_mid = _str_id(_get_any(doc, "usuarioId", "usuario_id"))
            servicio_mid = _str_id(_get_any(doc, "servicioId", "servicio_id"))

            mascota_info = map_mascotas.get(mascota_mid)
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
            procesados += 1

        # ------------------------------------------------------
        # 7. HISTORIAL CLÍNICO + SÍNTOMAS + TRATAMIENTOS
        # ------------------------------------------------------
        for doc in mongo_db.historial.find():
            mid = _str_id(doc.get("_id"))
            mascota_mid = _str_id(_get_any(doc, "mascotaId", "mascota_id"))
            usuario_mid = _str_id(_get_any(doc, "usuarioId", "usuario_id"))

            mascota_info = map_mascotas.get(mascota_mid)
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
            procesados += 1

            # Desanidar síntomas
            sintomas = doc.get("sintomas")
            if isinstance(sintomas, list):
                cur.execute("DELETE FROM historial_sintomas WHERE historial_id = %s;", (historial_neon_id,))
                for s in sintomas:
                    if s:
                        cur.execute(
                            "INSERT INTO historial_sintomas (historial_id, descripcion) VALUES (%s, %s);",
                            (historial_neon_id, str(s)),
                        )

            # Desanidar tratamientos
            tratamientos = doc.get("tratamientos")
            if isinstance(tratamientos, list):
                cur.execute("DELETE FROM historial_tratamientos WHERE historial_id = %s;", (historial_neon_id,))
                for t in tratamientos:
                    if t:
                        cur.execute(
                            "INSERT INTO historial_tratamientos (historial_id, indicacion) VALUES (%s, %s);",
                            (historial_neon_id, str(t)),
                        )

        # Finalizar bitácora con éxito
        fin = datetime.utcnow()
        cur.execute(
            """
            UPDATE etl_bitacora
            SET fecha_fin = %s, estado = %s, registros_procesados = %s, errores = %s
            WHERE ejecucion_id = %s;
            """,
            (fin, "SINCRONIZADO", procesados, errores, bitacora_id),
        )
        conn.commit()

        return {
            "success": True,
            "estado": "Sincronizado",
            "registros_procesados": procesados,
            "errores": errores,
            "ultima_sincronizacion": fin.isoformat(),
        }

    except Exception as e:
        conn.rollback()
        errores += 1
        detalle_error = str(e)
        fin = datetime.utcnow()
        if bitacora_id:
            try:
                cur.execute(
                    """
                    UPDATE etl_bitacora
                    SET fecha_fin = %s, estado = %s, registros_procesados = %s, errores = %s, detalle_error = %s
                    WHERE ejecucion_id = %s;
                    """,
                    (fin, "ERROR", procesados, errores, detalle_error, bitacora_id),
                )
                conn.commit()
            except Exception:
                pass
        return {
            "success": False,
            "estado": "Error",
            "registros_procesados": procesados,
            "errores": errores,
            "error": detalle_error,
            "ultima_sincronizacion": fin.isoformat(),
        }
    finally:
        cur.close()
        conn.close()