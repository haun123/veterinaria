import os
import sys
import threading
from datetime import datetime
from flask import Blueprint, jsonify

# Asegurar que Python encuentre las carpetas bots/, servicios/ y generadores/
DIRECTORIO_BOTS = os.path.dirname(os.path.abspath(__file__))
if DIRECTORIO_BOTS not in sys.path:
    sys.path.insert(0, DIRECTORIO_BOTS)

from bots.bots_1 import ejecutar_bot1
from bots.bots_2 import ejecutar_bot2
from bots.bots_3 import ejecutar_bot3

# Creamos el Blueprint con prefijo /api/bots
bots_bp = Blueprint("bots_bp", __name__, url_prefix="/api/bots")

FUNCIONES_BOTS = {
    "bot1": ejecutar_bot1,
    "bot2": ejecutar_bot2,
    "bot3": ejecutar_bot3,
}

ESTADO_BOTS = {
    "bot1": {
        "hilo": None, "stop_event": None, "activo": False, "inicio": None,
        "fase": "detenido", "operacion": None, "detalle": "", "exitosas": 0, "fallidas": 0, "evento_id": 0
    },
    "bot2": {
        "hilo": None, "stop_event": None, "activo": False, "inicio": None,
        "fase": "detenido", "operacion": None, "detalle": "", "exitosas": 0, "fallidas": 0, "evento_id": 0
    },
    "bot3": {
        "hilo": None, "stop_event": None, "activo": False, "inicio": None,
        "fase": "detenido", "operacion": None, "detalle": "", "exitosas": 0, "fallidas": 0, "evento_id": 0
    },
}

def registrar_evento_bot(bot_id, fase, operacion=None, detalle="", exito=False, error=False):
    """Actualiza el estado en tiempo real de un bot para alimentar la animación del dashboard."""
    if bot_id not in ESTADO_BOTS:
        return
    with _lock_eventos:
        info = ESTADO_BOTS[bot_id]
        info["fase"] = fase  # 'iniciando' | 'enviando_api' | 'guardado_mongo' | 'esperando' | 'error' | 'detenido'
        if operacion is not None:
            info["operacion"] = operacion
        if detalle:
            info["detalle"] = detalle
        if exito:
            info["exitosas"] += 1
        if error:
            info["fallidas"] += 1
        info["evento_id"] += 1
        info["actualizado_en"] = datetime.utcnow().isoformat()

def _correr_hilo(bot_id, funcion, stop_event):
    try:
        funcion(stop_event)
    finally:
        ESTADO_BOTS[bot_id]["activo"] = False


@bots_bp.route("/<bot_id>/iniciar", methods=["POST"])
def iniciar_bot(bot_id):
    if bot_id not in FUNCIONES_BOTS:
        return jsonify({"success": False, "error": f"Bot '{bot_id}' no válido"}), 400

    info = ESTADO_BOTS[bot_id]
    if info["hilo"] and info["hilo"].is_alive():
        return jsonify({"success": False, "message": f"{bot_id.upper()} ya está encendido"}), 409

    stop_event = threading.Event()
    hilo = threading.Thread(
        target=_correr_hilo,
        args=(bot_id, FUNCIONES_BOTS[bot_id], stop_event),
        name=f"Hilo-{bot_id}",
        daemon=True,
    )

    info["stop_event"] = stop_event
    info["hilo"] = hilo
    info["activo"] = True
    info["inicio"] = datetime.utcnow().isoformat()
    hilo.start()

    return jsonify({
        "success": True,
        "bot": bot_id,
        "activo": True,
        "message": f"{bot_id.upper()} iniciado correctamente",
    }), 200


@bots_bp.route("/<bot_id>/detener", methods=["POST"])
def detener_bot(bot_id):
    if bot_id not in FUNCIONES_BOTS:
        return jsonify({"success": False, "error": f"Bot '{bot_id}' no válido"}), 400

    info = ESTADO_BOTS[bot_id]
    if not info["hilo"] or not info["hilo"].is_alive():
        info["activo"] = False
        return jsonify({"success": False, "message": f"{bot_id.upper()} ya estaba detenido"}), 400

    info["stop_event"].set()
    info["activo"] = False

    return jsonify({
        "success": True,
        "bot": bot_id,
        "activo": False,
        "message": f"{bot_id.upper()} detenido",
    }), 200


@bots_bp.route("/estado", methods=["GET"])
def estado_bots():
    resumen = {}
    activos_count = 0
    for bot_id, info in ESTADO_BOTS.items():
        corriendo = bool(info["hilo"] and info["hilo"].is_alive())
        info["activo"] = corriendo
        if corriendo:
            activos_count += 1
        resumen[bot_id] = {
            "activo": corriendo,
            "inicio": info["inicio"],
            "fase": info["fase"],
            "operacion": info["operacion"],
            "detalle": info["detalle"],
            "exitosas": info["exitosas"],
            "fallidas": info["fallidas"],
            "evento_id": info["evento_id"],
        }
    return jsonify({
        "success": True,
        "bots_activos": activos_count,
        "procesos_conectados": 1 + activos_count,  # API Flask + bots encendidos
        "bots": resumen
    }), 200