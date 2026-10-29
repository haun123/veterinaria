import os
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# Conexión a MongoDB Atlas usando tu variable de entorno
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["veterinaria"]  


@app.route('/')
def index():
    return render_template('admin.html')
# ==========================================
# 1. RUTAS DE SERVICIOS (Catálogo)
# ==========================================
@app.route('/api/servicios', methods=['GET'])
def obtener_servicios():
    try:
        servicios = list(db.servicios.find({"activo": True}))
        for s in servicios:
            s['_id'] = str(s['_id'])
        return jsonify({"success": True, "data": servicios}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# 2. RUTAS DE CATEGORÍAS (Especies y Razas)
# ==========================================
@app.route('/api/categorias', methods=['GET'])
def obtener_categorias():
    try:
        categorias = list(db.categorias.find({"activa": True}))
        for c in categorias:
            c['_id'] = str(c['_id'])
        return jsonify({"success": True, "data": categorias}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# 3. RUTAS DE PACIENTES / TUTORES Y MASCOTAS
# ==========================================

@app.route('/api/tutores/registrar', methods=['POST'])
def registrar_tutor():
    try:
        data = request.json
        ahora = datetime.utcnow()
        
        tutor_doc = {
            "nombre": data.get("tutor_nombre"),
            "apellidos": data.get("tutor_apellidos", ""),
            "telefono": data.get("tutor_telefono"),
            "email": data.get("tutor_email", ""),
            "direccion": {
                "calle": data.get("calle", ""),
                "colonia": data.get("colonia", ""),
                "ciudad": data.get("ciudad", ""),
                "estado": data.get("estado", ""),
                "cp": data.get("cp", "")
            },
            "activo": True,
            "creadoEn": ahora
        }
        
        tutor_id = db.tutores.insert_one(tutor_doc).inserted_id

        return jsonify({
            "success": True, 
            "message": "Tutor registrado con éxito",
            "tutor_id": str(tutor_id)
        }), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/mascotas/registrar', methods=['POST'])
def registrar_mascota():
    try:
        data = request.json
        ahora = datetime.utcnow()
        
        # Validar campos mínimos obligatorios
        if not data.get("nombre") or not data.get("tutor_id") or not data.get("categoria_id"):
            return jsonify({"success": False, "error": "Faltan campos obligatorios (nombre, tutor o categoría)"}), 400

        # Fecha de nacimiento opcional
        fecha_nac = datetime.utcnow()
        if data.get("fecha_nacimiento"):
            try:
                fecha_nac = datetime.strptime(data.get("fecha_nacimiento"), "%Y-%m-%d")
            except:
                pass

        # Alergias opcionales (si vienen, se separan por comas; si no, lista vacía)
        alergias_raw = data.get("alergias", "")
        alergias_list = [a.strip() for a in alergias_raw.split(",") if a.strip()] if alergias_raw else []

        mascota_doc = {
            "nombre": data.get("nombre"),
            "tutorId": ObjectId(data.get("tutor_id")),
            "categoriaId": ObjectId(data.get("categoria_id")),
            "raza": data.get("raza", "").strip() or "No especificada",
            "sexo": data.get("sexo", "macho"),
            "fechaNacimiento": fecha_nac,
            "color": data.get("color", "").strip() or "No especificado",
            "pesoActualKg": float(data.get("peso") or 0),
            "esterilizada": bool(data.get("esterilizada", False)),
            "alergias": alergias_list,
            "activa": True,
            "creadoEn": ahora
        }
        
        mascota_id = db.mascotas.insert_one(mascota_doc).inserted_id

        return jsonify({
            "success": True, 
            "message": "Mascota registrada con éxito",
            "mascota_id": str(mascota_id)
        }), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Registrar Tutor + Primera Mascota (Requisito C)
@app.route('/api/pacientes/registrar', methods=['POST'])
def registrar_paciente_completo():
    try:
        data = request.json
        ahora = datetime.utcnow()
        
        # 1. Insertar Tutor
        tutor_id = db.tutores.insert_one({
            "nombre": data.get("tutor_nombre"),
            "apellidos": data.get("tutor_apellidos", ""),
            "telefono": data.get("tutor_telefono"),
            "email": data.get("tutor_email", ""),
            "activo": True,
            "creadoEn": ahora
        }).inserted_id

        # 2. Insertar Mascota (Validando si trae categoría o es un registro temporal/vacío)
        cat_id_raw = data.get("categoria_id")
        categoria_id = ObjectId(cat_id_raw) if cat_id_raw and cat_id_raw.strip() != "" else None

        mascota_doc = {
            "nombre": data.get("mascota_nombre", "Temporal"),
            "tutorId": tutor_id,
            "raza": data.get("mascota_raza", ""),
            "sexo": data.get("mascota_sexo", "desconocido"),
            "pesoActualKg": float(data.get("peso_actual", 0)),
            "activa": True,
            "creadoEn": ahora
        }
        
        if categoria_id:
            mascota_doc["categoriaId"] = categoria_id

        mascota_id = db.mascotas.insert_one(mascota_doc).inserted_id

        return jsonify({
            "success": True, 
            "message": "Tutor y mascota registrados con éxito",
            "tutor_id": str(tutor_id),
            "mascota_id": str(mascota_id)
        }), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# 4. RUTAS DE CITAS Y AGENDA
# ==========================================

@app.route('/api/citas/crear', methods=['POST'])
def crear_cita_mostrador():
    try:
        data = request.json
        ahora = datetime.utcnow()

        # 1. Gestionar Tutor (Buscar si ya existe por teléfono o crearlo)
        telefono = data.get("tutor_telefono")
        tutor = db.tutores.find_one({"telefono": telefono})
        
        if tutor:
            tutor_id = tutor["_id"]
            tutor_nombre_completo = f"{tutor.get('nombre', '')} {tutor.get('apellidos', '')}".strip()
        else:
            # Crear nuevo tutor con la estructura exacta
            tutor_nuevo = {
                "nombre": data.get("tutor_nombre"),
                "apellidos": data.get("tutor_apellidos", ""),
                "telefono": telefono,
                "email": data.get("tutor_email", ""),
                "activo": True,
                "creadoEn": ahora
            }
            tutor_id = db.tutores.insert_one(tutor_nuevo).inserted_id
            tutor_nombre_completo = f"{data.get('tutor_nombre')} {data.get('tutor_apellidos', '')}".strip()

        # 2. Registrar la Mascota asociada al tutor
        categoria_id = data.get("categoria_id")
        if categoria_id and not isinstance(categoria_id, ObjectId):
            categoria_id = ObjectId(categoria_id)

        alergias_raw = data.get("mascota_alergias", "")
        alergias_list = [a.strip() for a in alergias_raw.split(",")] if alergias_raw else []

        mascota_doc = {
            "nombre": data.get("mascota_nombre"),
            "tutorId": tutor_id,
            "categoriaId": categoria_id,
            "raza": data.get("mascota_raza", ""),
            "sexo": data.get("mascota_sexo", "macho"),
            "color": data.get("mascota_color", ""),
            "pesoActualKg": float(data.get("mascota_peso", 0)),
            "alergias": alergias_list,
            "activa": True,
            "creadoEn": ahora
        }
        mascota_id = db.mascotas.insert_one(mascota_doc).inserted_id
        mascota_nombre = data.get("mascota_nombre")

        # 3. Obtener el servicio seleccionado para extraer su nombre
        servicio_id = data.get("servicio_id")
        servicio_nombre = "Consulta general"
        if servicio_id:
            if not isinstance(servicio_id, ObjectId):
                servicio_id = ObjectId(servicio_id)
            servicio = db.servicios.find_one({"_id": servicio_id})
            if servicio:
                servicio_nombre = servicio.get("nombre", "Consulta")

        # 4. Crear la Cita con la estructura exacta que especificaste
        cita_doc = {
            "mascotaId": mascota_id,
            "tutorId": tutor_id,
            "usuarioId": ObjectId('6ae22182f2102fe7ce813716'), # ID de usuario por defecto del sistema o sesión
            "servicioId": servicio_id,
            "mascotaNombre": mascota_nombre,
            "tutorNombre": tutor_nombre_completo,
            "servicioNombre": servicio_nombre,
            "fechaInicio": ahora,
            "fechaFin": ahora, # Se puede ajustar según la duración del servicio
            "motivo": data.get("motivo", "Consulta en mostrador"),
            "estado": "pendiente", # Queda lista en la agenda para ser atendida
            "creadoEn": ahora
        }
        
        db.citas.insert_one(cita_doc)

        return jsonify({"success": True, "message": "Cita registrada con éxito en mostrador"}), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    

@app.route('/api/citas', methods=['GET'])
def obtener_citas():
    try:
        citas = list(db.citas.find({}))
        resultado_final = []
        
        for c in citas:
            # 1. Obtener nombre del tutor (si ya viene plano o buscarlo)
            tutor_nombre = c.get('tutorNombre')
            tutor_telefono = 'Sin teléfono'
            
            # Siempre consultamos la colección tutores usando tutorId para asegurar el teléfono actualizado
            if c.get('tutorId'):
                tutor = db.tutores.find_one({"_id": c.get('tutorId')})
                if tutor:
                    if not tutor_nombre:
                        tutor_nombre = f"{tutor.get('nombre', '')} {tutor.get('apellidos', '')}".strip()
                    tutor_telefono = tutor.get('telefono', 'Sin teléfono')

            # 2. Mascota
            mascota_nombre = c.get('mascotaNombre')
            if not mascota_nombre and c.get('mascotaId'):
                mascota = db.mascotas.find_one({"_id": c.get('mascotaId')})
                if mascota:
                    mascota_nombre = mascota.get('nombre', '')

            # 3. Servicio
            servicio_nombre = c.get('servicioNombre')
            if not servicio_nombre and c.get('servicioId'):
                servicio = db.servicios.find_one({"_id": c.get('servicioId')})
                if servicio:
                    servicio_nombre = servicio.get('nombre', '')

            resultado_final.append({
                "_id": str(c.get('_id')),
                "tutor_nombre": tutor_nombre or "Cliente general",
                "tutor_telefono": tutor_telefono,
                "mascota_nombre": mascota_nombre or "Mascota",
                "servicio_nombre": servicio_nombre or c.get('motivo', 'Consulta'),
                "motivo": c.get('motivo', ''),
                "estado": c.get('estado', 'pendiente').lower()
            })

        return jsonify({"success": True, "data": resultado_final}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Cancelar Cita (Requisito D)
@app.route('/api/citas/cancelar/<id_cita>', methods=['PUT'])
def cancelar_cita(id_cita):
    try:
        resultado = db.citas.update_one(
            {"_id": ObjectId(id_cita)},
            {"$set": {"estado": "cancelada", "actualizadoEn": datetime.utcnow()}}
        )

        if resultado.matched_count == 0:
            return jsonify({"success": False, "error": "Cita no encontrada"}), 404

        return jsonify({"success": True, "message": "Cita cancelada correctamente"}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
# Agregar nueva consulta al historial (Requisito U)
@app.route('/api/historial/agregar/<mascota_id>', methods=['POST'])
def agregar_entrada_historial(mascota_id):
    try:
        data = request.json
        ahora = datetime.utcnow()
        
        nueva_entrada = {
            "mascotaId": ObjectId(mascota_id),
            "usuarioId": ObjectId(data.get("usuario_id")), # Veterinario responsable
            "fecha": ahora,
            "motivoConsulta": data.get("motivo_consulta"),
            "signosVitales": {
                "pesoKg": float(data.get("peso_kg", 0)),
                "temperaturaC": float(data.get("temperatura_c", 0))
            },
            "sintomas": data.get("sintomas", []),
            "diagnostico": data.get("diagnostico"),
            "tratamientos": data.get("tratamientos", []),
            "observaciones": data.get("observaciones", ""),
            "creadoEn": ahora
        }

        resultado_id = db.historial.insert_one(nueva_entrada).inserted_id

        return jsonify({
            "success": True, 
            "message": "Entrada clínica agregada con éxito al historial",
            "historial_id": str(resultado_id)
        }, 201)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# Apartado de administración del historial clínico
# ==========================================

# Búsqueda de pacientes por síntoma o diagnóstico (Requisito R)
@app.route('/api/historial/buscar', methods=['GET'])
def buscar_historial():
    try:
        termino = request.args.get('termino', '').strip()
        
        filtro = {}
        if termino:
            filtro = {
                "$or": [
                    {"sintomas": {"$regex": termino, "$options": "i"}},
                    {"diagnostico": {"$regex": termino, "$options": "i"}},
                    {"motivoConsulta": {"$regex": termino, "$options": "i"}}
                ]
            }

        historiales = list(db.historial.find(filtro))
        resultado_final = []

        for h in historiales:
            # Buscar nombre de la mascota
            mascota = db.mascotas.find_one({"_id": h.get("mascotaId")})
            mascota_nombre = mascota["nombre"] if mascota else "Mascota general"

            # Formatear fecha principal
            fecha_consulta = h.get("fecha")
            fecha_str = fecha_consulta.strftime("%Y-%m-%d") if hasattr(fecha_consulta, "strftime") else str(fecha_consulta)[:10]

            # Formatear la lista de tratamientos (si existen)
            tratamientos_formateados = []
            for t in h.get("tratamientos", []):
                tratamientos_formateados.append(
                    f"{t.get('medicamento', '')} - {t.get('dosis', '')} ({t.get('frecuencia', '')}, por {t.get('duracionDias', '')} días)"
                )

            # Formatear síntomas (puede ser lista o texto)
            sintomas_val = h.get("sintomas", [])
            sintomas_str = ", ".join(sintomas_val) if isinstance(sintomas_val, list) else str(sintomas_val)

            # Signos vitales
            signos = h.get("signosVitales", {})

            resultado_final.append({
                "_id": str(h["_id"]),
                "fecha": fecha_str,
                "motivo": h.get("motivoConsulta", "Consulta general"),
                "sintomas": sintomas_str,
                "diagnostico": h.get("diagnostico", "Sin diagnóstico"),
                "tratamientos": tratamientos_formateados,
                "signos_vitales": {
                    "peso": signos.get("pesoKg", 0),
                    "temp": signos.get("temperaturaC", 0),
                    "fc": signos.get("frecuenciaCardiaca", 0)
                },
                "observaciones": h.get("observaciones", ""),
                "proxima_revision": str(h.get("proximaRevision", ""))[:10] if h.get("proximaRevision") else None,
                "mascota_nombre": mascota_nombre,
                "costo": h.get("costo", 500) # Valor por defecto si no lo tiene en el documento
            })

        return jsonify({"success": True, "data": resultado_final}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



# ==========================================
# Apartado de administración de pacientes y tutores
# ==========================================

@app.route('/api/pacientes/listar', methods=['GET'])
def listar_pacientes():
    try:
        tutores = list(db.tutores.find({"activo": True}))
        resultado_final = []

        for tutor in tutores:
            tutor_id_str = str(tutor["_id"])
            # Buscamos las mascotas asociadas a este tutor mediante ObjectId
            mascotas = list(db.mascotas.find({"tutorId": tutor["_id"], "activa": True}))
            
            mascotas_formateadas = []
            for m in mascotas:
                # Buscamos el nombre de la especie/categoría si está vinculada
                cat = db.categorias.find_one({"_id": m.get("categoriaId")})
                especie_nombre = cat["especie"] if cat else "General"
                
                mascotas_formateadas.append({
                    "_id": str(m["_id"]),
                    "nombre": m.get("nombre"),
                    "especie": especie_nombre,
                    "raza": m.get("raza", ""),
                    "sexo": m.get("sexo", "desconocido"),
                    "peso": m.get("pesoActualKg", 0)
                })

            resultado_final.append({
                "_id": tutor_id_str,
                "nombre_completo": f"{tutor.get('nombre', '')} {tutor.get('apellidos', '')}",
                "telefono": tutor.get("telefono", ""),
                "email": tutor.get("email", "Sin correo"),
                "mascotas": mascotas_formateadas
            })

        return jsonify({"success": True, "data": resultado_final}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# Apartado de administración de servicios
# ==========================================

# Crear un nuevo servicio
@app.route('/api/servicios/crear', methods=['POST'])
def crear_servicio():
    try:
        data = request.json
        nuevo_servicio = {
            "nombre": data.get("nombre"),
            "tipo": data.get("tipo", "consulta"),
            "duracionMin": int(data.get("duracion_min", 30)),
            "precio": float(data.get("precio", 0)),
            "activo": True
        }
        db.servicios.insert_one(nuevo_servicio)
        return jsonify({"success": True, "message": "Servicio creado con éxito"}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Actualizar un servicio existente
@app.route('/api/servicios/actualizar/<id_servicio>', methods=['PUT'])
def actualizar_servicio(id_servicio):
    try:
        data = request.json
        actualizacion = {}
        if "nombre" in data: actualizacion["nombre"] = data["nombre"]
        if "tipo" in data: actualizacion["tipo"] = data["tipo"]
        if "precio" in data: actualizacion["precio"] = float(data["precio"])
        if "duracion_min" in data: actualizacion["duracionMin"] = int(data["duracion_min"])
        
        resultado = db.servicios.update_one(
            {"_id": ObjectId(id_servicio)},
            {"$set": actualizacion}
        )

        if resultado.matched_count == 0:
            return jsonify({"success": False, "error": "Servicio no encontrado"}), 404

        return jsonify({"success": True, "message": "Servicio actualizado con éxito"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)