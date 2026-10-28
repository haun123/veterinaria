
import os
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración de la conexión a MongoDB Atlas adwada agregado de algo
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.veterinaria  # Base de datos 'veterinaria'

@app.route("/")
def vista_tutor():
    return render_template("tutor.html")

# Ruta independiente para el panel del médico / administrador
@app.route("/admin")
def vista_admin():
    return render_template("admin.html")

# ==========================================
# ENDPOINTS - VISTA DE USUARIO
# ==========================================

# 1. Obtener catálogo de servicios activos
@app.route("/api/servicios", methods=["GET"])
def get_servicios():
    try:
        servicios_cursor = db.servicios.find({"activo": True})
        servicios = []
        for s in servicios_cursor:
            s["_id"] = str(s["_id"])
            servicios.append(s)
        return jsonify({"success": True, "data": servicios}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 2. Obtener las mascotas de un tutor específico
@app.route("/api/tutores/<tutor_id>/mascotas", methods=["GET"])
def get_mascotas_tutor(tutor_id):
    try:
        mascotas_cursor = db.mascotas.find({"tutorId": ObjectId(tutor_id), "activa": True})
        mascotas = []
        for m in mascotas_cursor:
            m["_id"] = str(m["_id"])
            m["tutorId"] = str(m["tutorId"])
            m["categoriaId"] = str(m["categoriaId"])
            mascotas.append(m)
        return jsonify({"success": True, "data": mascotas}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 3. Crear una nueva cita médica
@app.route("/api/citas", methods=["POST"])
def crear_cita():
    try:
        data = request.get_json()
        fecha_raw = data.get("fechaInicio")
        
        # Procesar la fecha de forma segura para evitar errores de datetime
        if isinstance(fecha_raw, str):
            # Limpiar la cadena ISO o formato de fecha recibido
            fecha_dt = datetime.fromisoformat(fecha_raw.replace('Z', '+00:00'))
        else:
            fecha_dt = datetime.utcnow()


        nueva_cita = {
            "mascotaId": ObjectId(data.get("mascotaId")),
            "tutorId": ObjectId(data.get("tutorId")),
            "usuarioId": ObjectId(data.get("usuarioId")),
            "servicioId": ObjectId(data.get("servicioId")),
            "mascotaNombre": data.get("mascotaNombre"),
            "tutorNombre": data.get("tutorNombre"),
            "servicioNombre": data.get("servicioNombre"),
            "fechaInicio": fecha_dt,  # Guardado como datetime válido"
            "motivo": data.get("motivo"),
            "estado": "programada",
            "creadoEn": datetime.utcnow()
        }
        
        db.citas.insert_one(nueva_cita)
        return jsonify({"success": True, "mensaje": "Cita agendada con éxito"}), 201
    except Exception as e:
        print("Error en backend al agendar cita:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

# 4. Listar citas de un usuario (para la sección de Citas Agendadas)
@app.route("/api/citas/tutor/<tutor_id>", methods=["GET"])
def get_citas_tutor(tutor_id):
    try:
        citas_cursor = db.citas.find({"tutorId": ObjectId(tutor_id)}).sort("fechaInicio", -1)
        citas = []
        for c in citas_cursor:
            c["_id"] = str(c["_id"])
            c["mascotaId"] = str(c["mascotaId"])
            c["tutorId"] = str(c["tutorId"])
            c["usuarioId"] = str(c["usuarioId"])
            c["servicioId"] = str(c["servicioId"])
            citas.append(c)
        return jsonify({"success": True, "data": citas}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 5. Cancelar una cita
@app.route("/api/citas/<cita_id>/cancelar", methods=["PATCH"])
def cancelar_cita(cita_id):
    try:
        resultado = db.citas.update_one(
            {"_id": ObjectId(cita_id)},
            {"$set": {"estado": "cancelada", "actualizadoEn": __import__('datetime').datetime.utcnow()}}
        )
        if resultado.modified_count > 0:
            return jsonify({"success": True, "message": "Cita cancelada correctamente"}), 200
        else:
            return jsonify({"success": False, "message": "Cita no encontrada o ya estaba cancelada"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 6. Obtener el historial médico de las mascotas del tutor
@app.route("/api/historial/tutor/<tutor_id>", methods=["GET"])
def get_historial_tutor(tutor_id):
    try:
        # Primero buscamos las mascotas del tutor
        mascotas_ids = [m["_id"] for m in db.mascotas.find({"tutorId": ObjectId(tutor_id)}, {"_id": 1})]
        
        # Luego buscamos todo el historial asociado a esas mascotas
        historial_cursor = db.historial.find({"mascotaId": {"$in": mascotas_ids}}).sort("fecha", -1)
        
        historial = []
        for h in historial_cursor:
            h["_id"] = str(h["_id"])
            h["mascotaId"] = str(h["mascotaId"])
            h["usuarioId"] = str(h["usuarioId"])
            if "citaId" in h and h["citaId"]:
                h["citaId"] = str(h["citaId"])
            historial.append(h)
            
        return jsonify({"success": True, "data": historial}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# ENDPOINTS - VISTA DE ADMINISTRADOR / MÉDICO   
# ==========================================


# 1. Obtener TODAS las citas de la clínica (para el administrador)
@app.route("/api/citas", methods=["GET"])
def obtener_todas_citas():
    try:
        citas = list(db.citas.find())
        for c in citas:
            c["_id"] = str(c["_id"])
            c["mascotaId"] = str(c["mascotaId"])
            c["tutorId"] = str(c["tutorId"])
            c["usuarioId"] = str(c["usuarioId"])
            c["servicioId"] = str(c["servicioId"])
        return jsonify({"success": True, "data": citas}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 2. Actualizar el estado de una cita (Confirmar, Completar, Cancelar)
@app.route("/api/citas/<id>/estado", methods=["PATCH"])
def actualizar_estado_cita(id):
    try:
        data = request.get_json()
        nuevo_estado = data.get("estado")
        db.citas.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"estado": nuevo_estado}}
        )
        return jsonify({"success": True, "mensaje": "Estado actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 3. Obtener TODAS las mascotas de la clínica (Directorio de Pacientes)
@app.route("/api/mascotas", methods=["GET"])
def obtener_todas_mascotas():
    try:
        mascotas = list(db.mascotas.find())
        for m in mascotas:
            m["_id"] = str(m["_id"])
            m["tutorId"] = str(m["tutorId"])
        return jsonify({"success": True, "data": mascotas}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 4. Registrar una nueva mascota desde el panel de Admin
@app.route("/api/mascotas", methods=["POST"])
def registrar_mascota_admin():
    try:
        data = request.get_json()
        nueva_mascota = {
            "nombre": data.get("nombre"),
            "especie": data.get("especie"),
            "raza": data.get("raza"),
            "edad": int(data.get("edad", 0)),
            "pesoKg": float(data.get("pesoKg", 0)),
            "sexo": data.get("sexo", "Desconocido"),
            "tutorNombre": data.get("tutorNombre"),
            "creadoEn": datetime.utcnow()
        }
        resultado = db.mascotas.insert_one(nueva_mascota)
        return jsonify({"success": True, "id": str(resultado.inserted_id)}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)