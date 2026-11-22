"""
Estado en tiempo real de los bots y función para reportar eventos.

Vive en su propio archivo, sin importar nada de los bots, para evitar la
importación circular con rutas_bots.py. Todos (rutas y bots) lo importan como
`eventos_bots`, así existe una sola copia de ESTADO_BOTS en memoria.
"""
import threading
from datetime import datetime

_lock_eventos = threading.Lock()

IDS_BOTS = ("bot1", "bot2", "bot3", "bot4")

# rutas_bots.py lo reemplaza por clusters.cluster_asignado para saber en qué cluster
# estaba cada bot cuando ocurrió un evento (contadores por cluster).
resolver_cluster = lambda bot_id: None  # noqa: E731


def _estado_inicial():
    return {
        "hilo": None, "stop_event": None, "activo": False, "inicio": None,
        "fase": "detenido", "operacion": None, "detalle": "",
        "exitosas": 0, "fallidas": 0, "evento_id": 0, "actualizado_en": None,
        "por_cluster": {"A": {"exitosas": 0, "fallidas": 0}, "B": {"exitosas": 0, "fallidas": 0}},
    }


ESTADO_BOTS = {bot_id: _estado_inicial() for bot_id in IDS_BOTS}


def registrar_evento_bot(bot_id, fase, operacion=None, detalle="", exito=False, error=False):
    """Actualiza el estado en tiempo real de un bot para alimentar la animación del dashboard."""
    if bot_id not in ESTADO_BOTS:
        return
    try:
        cluster = resolver_cluster(bot_id) or "A"
    except Exception:
        cluster = "A"
    with _lock_eventos:
        info = ESTADO_BOTS[bot_id]
        info["fase"] = fase  # 'iniciando' | 'enviando_api' | 'guardado_mongo' | 'error' | 'detenido'
        if operacion is not None:
            info["operacion"] = operacion
        if detalle:
            info["detalle"] = detalle
        if exito:
            info["exitosas"] += 1
            info["por_cluster"][cluster]["exitosas"] += 1
        if error:
            info["fallidas"] += 1
            info["por_cluster"][cluster]["fallidas"] += 1
        info["evento_id"] += 1
        info["actualizado_en"] = datetime.utcnow().isoformat()
