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

# Registrar Tutor + Primera Mascota (Requisito C)
@app.route('/api/pacientes/registrar', methods=['POST'])
def registrar_paciente_completo():
    try:
        data =reira = request.json
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

        # 2. Insertar Mascota enlazada al Tutor y a Categoría
        mascota_id = db.mascotas.insert_one({
            "nombre": data.get("mascota_nombre"),
            "tutorId": tutor_id,
            "categoriaId": ObjectId(data.get("categoria_id")),
            "raza": data.get("mascota_raza", ""),
            "sexo": data.get("mascota_sexo", "desconocido"),
            "pesoActualKg": float(data.get("peso_actual", 0)),
            "activa": True,
            "creadoEn": ahora
        }).inserted_id

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
@app.route('/api/citas', methods=['GET'])
def obtener_citas():
    try:
        citas = list(db.citas.find({}))
        for c in citas:
            c['_id'] = str(c['_id'])
            c['tutorId'] = str(c.get('tutorId', ''))
            c['mascotaId'] = str(c.get('mascotaId', ''))
            c['usuarioId'] = str(c.get('usuarioId', ''))
            c['servicioId'] = str(c.get('servicioId', ''))
        return jsonify({"success": True, "data": citas}), 200
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


# ==========================================
# 5. RUTAS DE HISTORIAL CLÍNICO (Colección independiente)
# ==========================================

# Búsqueda de pacientes por síntoma o diagnóstico (Requisito R)
@app.route('/api/historial/buscar', methods=['GET'])
def buscar_historial():
    try:
        query_busqueda = request.args.get('q', '')
        
        if not query_busqueda:
            return jsonify({"success": True, "data": []}), 200

        # Buscamos en la colección independiente 'historial' usando regex
        resultados = list(db.historial.find({
            "$or": [
                {"sintomas": {"$regex": query_busqueda, "$options": "i"}},
                {"diagnostico": {"$regex": query_busqueda, "$options": "i"}},
                {"motivoConsulta": {"$regex": query_busqueda, "$options": "i"}}
            ]
        }))

        for r in resultados:
            r['_id'] = str(r['_id'])
            r['mascotaId'] = str(r.get('mascotaId', ''))
            r['usuarioId'] = str(r.get('usuarioId', ''))

        return jsonify({"success": True, "data": resultados}), 200

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