import os
import sys
import threading
from datetime import datetime
from flask import Blueprint, jsonify

# Asegurar que Python encuentre las carpetas bots/, servicios/ y generadores/
DIRECTORIO_BOTS = os.path.dirname(os.path.abspath(__file__))
if DIRECTORIO_BOTS not in sys.path:
    sys.path.insert(0, DIRECTORIO_BOTS)

# Estado compartido (una sola copia en memoria, importada siempre como "eventos_bots")
import eventos_bots
from eventos_bots import ESTADO_BOTS, registrar_evento_bot  # noqa: F401  (se re-exportan)
import contexto_bot

from bots.bots_1 import ejecutar_bot1
from bots.bots_2 import ejecutar_bot2
from bots.bots_3 import ejecutar_bot3
from bots.bots_4 import ejecutar_bot4

from clusters import (
    MAX_BOTS_CLUSTER_A,
    asignar_cluster,
    cluster_asignado,
    cluster_previsto,
    clusters_configurados,
    diagnosticar,
    get_mongo_db,
    liberar_cluster,
)

# Los contadores de eventos se llevan por cluster (según dónde estaba el bot en ese momento)
eventos_bots.resolver_cluster = cluster_asignado

# Cada petición HTTP de un hilo de bot saldrá con X-Bot-Id
contexto_bot.instalar()

# Creamos el Blueprint con prefijo /api/bots
bots_bp = Blueprint("bots_bp", __name__, url_prefix="/api/bots")

FUNCIONES_BOTS = {
    "bot1": ejecutar_bot1,
    "bot2": ejecutar_bot2,
    "bot3": ejecutar_bot3,
    "bot4": ejecutar_bot4,
}


def _correr_hilo(bot_id, funcion, stop_event):
    try:
        funcion(stop_event)
    finally:
        liberar_cluster(bot_id)   # deja libre su lugar en el cluster
        info = ESTADO_BOTS[bot_id]
        info["activo"] = False
        if info["fase"] != "error":   # si terminó por un error, se conserva para mostrarlo
            info["fase"] = "detenido"


def _validar_cluster_b():
    """Antes de mandar un bot al cluster B, comprueba que responde y que tiene el catálogo base."""
    try:
        db_b = get_mongo_db("B")
        if db_b.categorias.count_documents({}, limit=1) == 0:
            return False, "El cluster B no tiene categorías/servicios. Ejecuta: python sembrar_cluster_b.py"
        return True, None
    except Exception as e:
        return False, f"No se pudo conectar al cluster B: {type(e).__name__}: {e}"[:400]


@bots_bp.route("/<bot_id>/iniciar", methods=["POST"])
def iniciar_bot(bot_id):
    if bot_id not in FUNCIONES_BOTS:
        return jsonify({"success": False, "error": f"Bot '{bot_id}' no válido"}), 400

    info = ESTADO_BOTS[bot_id]
    if info["hilo"] and info["hilo"].is_alive():
        return jsonify({"success": False, "message": f"{bot_id.upper()} ya está encendido"}), 409

    # Primeros MAX_BOTS_CLUSTER_A bots -> cluster A; el siguiente -> cluster B
    cluster, aviso = asignar_cluster(bot_id)
    if cluster == "B":
        ok, motivo = _validar_cluster_b()
        if not ok:
            liberar_cluster(bot_id)
            return jsonify({"success": False, "error": motivo}), 400

    stop_event = threading.Event()
    hilo = threading.Thread(
        target=_correr_hilo,
        args=(bot_id, FUNCIONES_BOTS[bot_id], stop_event),
        name=f"Hilo-{bot_id}",      # contexto_bot.py deriva X-Bot-Id de este nombre
        daemon=True,
    )

    info["stop_event"] = stop_event
    info["hilo"] = hilo
    info["activo"] = True
    info["inicio"] = datetime.utcnow().isoformat()
    registrar_evento_bot(bot_id, "iniciando", detalle=f"Cluster {cluster}")
    try:
        hilo.start()
    except Exception as e:
        liberar_cluster(bot_id)
        info["activo"] = False
        return jsonify({"success": False, "error": f"No se pudo iniciar el hilo: {e}"}), 500

    mensaje = f"{bot_id.upper()} iniciado correctamente (cluster {cluster})"
    if aviso:
        mensaje += f" · AVISO: {aviso}"
    return jsonify({
        "success": True,
        "bot": bot_id,
        "activo": True,
        "cluster": cluster,
        "aviso": aviso,
        "message": mensaje,
    }), 200


@bots_bp.route("/<bot_id>/detener", methods=["POST"])
def detener_bot(bot_id):
    if bot_id not in FUNCIONES_BOTS:
        return jsonify({"success": False, "error": f"Bot '{bot_id}' no válido"}), 400

    info = ESTADO_BOTS[bot_id]
    if not info["hilo"] or not info["hilo"].is_alive():
        info["activo"] = False
        liberar_cluster(bot_id)
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
    bots_en_a = 0
    for bot_id, info in ESTADO_BOTS.items():
        corriendo = bool(info["hilo"] and info["hilo"].is_alive())
        info["activo"] = corriendo
        if corriendo:
            activos_count += 1

        asignado = cluster_asignado(bot_id) if corriendo else None
        if asignado == "A":
            bots_en_a += 1
        resumen[bot_id] = {
            "activo": corriendo,
            "inicio": info["inicio"],
            # Encendido: el cluster que realmente usa. Apagado: el que usaría si se encendiera ahora.
            "cluster": asignado or cluster_previsto(bot_id),
            "cluster_asignado": asignado is not None,
            "fase": info["fase"],
            "operacion": info["operacion"],
            "detalle": info["detalle"],
            "exitosas": info["exitosas"],
            "fallidas": info["fallidas"],
            "por_cluster": info["por_cluster"],
            "evento_id": info["evento_id"],
        }
    return jsonify({
        "success": True,
        "bots_activos": activos_count,
        "procesos_conectados": 1 + activos_count,  # API Flask + bots encendidos
        "cluster_a": {"bots": bots_en_a, "maximo": MAX_BOTS_CLUSTER_A},
        "clusters_configurados": clusters_configurados(),
        "bots": resumen
    }), 200


@bots_bp.route("/diagnostico", methods=["GET"])
def diagnostico_clusters():
    """
    Prueba real de conexión a cada cluster. Abre en el navegador:
        http://localhost:5000/api/bots/diagnostico
    Muestra el host (sin usuario ni contraseña), la base, el tiempo de respuesta o el error exacto.
    """
    asignacion = {b: cluster_asignado(b) for b in ESTADO_BOTS if cluster_asignado(b)}
    return jsonify({
        "success": True,
        "clusters": diagnosticar(),
        "asignacion_actual": asignacion,
        "max_bots_cluster_a": MAX_BOTS_CLUSTER_A,
    }), 200
