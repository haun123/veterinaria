"""
Manejo de varios clusters de MongoDB y asignación de bots a cluster.

VARIABLES DEL .env (la URL ya incluye el nombre de la base, igual que en database.py)
  MONGO_URI    cluster A  (la de siempre, la lee tu database.py)
  NEON_URI     Neon       (la de siempre, la lee tu database.py; este archivo no la usa)
  MONGO_URI_B  cluster B  (NUEVA, opcional; misma forma que MONGO_URI)

REGLA DE ASIGNACIÓN
  - Los bots se conectan al cluster A.
  - El cluster A admite hasta MAX_BOTS_CLUSTER_A bots conectados a la vez.
  - Cuando se conecta uno más (el 4.º en total), ese bot se conecta al cluster B.
  - La asignación se decide al encender el bot y dura mientras siga encendido.
    Al apagarse libera su lugar.

La API sabe de qué bot viene cada petición por el encabezado X-Bot-Id.
Las peticiones sin encabezado (dashboard, Postman...) van al cluster A.
"""
import os
import re
import threading
import time

from dotenv import load_dotenv
from flask import has_request_context, request
from pymongo import MongoClient
from pymongo.errors import ConfigurationError

# Constantes (no son variables del .env)
MAX_BOTS_CLUSTER_A = 3     # bots que caben en el cluster A; el siguiente va al B
TIMEOUT_MS = 8000          # espera máxima al cluster B y a las pruebas de diagnóstico


def _cargar_env():
    """
    Carga el .env de la raíz del proyecto y, si existe, el de bots_CRUD/ (además del
    comportamiento normal de load_dotenv). Nunca pisa variables que ya estén definidas.
    """
    raiz = os.path.dirname(os.path.abspath(__file__))
    for ruta in (os.path.join(raiz, ".env"), os.path.join(raiz, "bots_CRUD", ".env")):
        if os.path.isfile(ruta):
            load_dotenv(ruta)
    load_dotenv()


_cargar_env()

_VARIABLE_URI = {"A": "MONGO_URI", "B": "MONGO_URI_B"}


class ClusterNoConfigurado(RuntimeError):
    pass


_lock = threading.RLock()
_cache = {}          # cluster -> Database
_asignacion = {}     # bot_id -> cluster ("A" | "B") mientras el bot está encendido


# ----------------------------------------------------------------------
# Conexión
# ----------------------------------------------------------------------
def clusters_configurados():
    """Lista de clusters disponibles según el .env: ['A'] o ['A', 'B']."""
    return [c for c, variable in _VARIABLE_URI.items() if os.getenv(variable)]


def _host_seguro(uri):
    """Solo el host de la URI (sin usuario ni contraseña), para mostrar en diagnósticos."""
    sin_esquema = re.sub(r"^[a-zA-Z0-9+.\-]+://", "", uri)
    sin_credenciales = sin_esquema.split("@")[-1]
    return re.split(r"[/?]", sin_credenciales)[0]


def get_mongo_db(cluster="A"):
    """Devuelve el objeto Database del cluster pedido (se crea una sola vez y se reutiliza)."""
    cluster = (cluster or "A").upper()
    if cluster not in _VARIABLE_URI:
        raise ValueError(f"Cluster desconocido: {cluster}")

    with _lock:
        if cluster in _cache:
            return _cache[cluster]

        variable = _VARIABLE_URI[cluster]
        uri = os.getenv(variable)
        if not uri:
            raise ClusterNoConfigurado(
                f"Falta {variable} en el archivo .env (se buscó en la raíz del proyecto y en bots_CRUD/)"
            )

        if cluster == "A":
            # Exactamente tu database.py de siempre: MONGO_URI + get_default_database()
            from database import get_mongo_db as _db_cluster_a
            db = _db_cluster_a()
        else:
            # Cluster B: igual que database.py, el nombre de la base sale de la propia URL
            client = MongoClient(uri, serverSelectionTimeoutMS=TIMEOUT_MS)
            try:
                db = client.get_default_database()
            except ConfigurationError:
                raise ClusterNoConfigurado(
                    f"{variable} no incluye el nombre de la base de datos. "
                    f"Agrégalo entre el host y el '?', por ejemplo ...mongodb.net/veterinaria?retryWrites=true"
                )

        print(f"[CLUSTERS] Cluster {cluster} -> host={_host_seguro(uri)} base={db.name}")
        _cache[cluster] = db
        return db


def diagnosticar():
    """
    Prueba de conexión (ping) a cada cluster configurado, con un cliente nuevo y de espera corta.
    Nunca devuelve usuario ni contraseña.
    """
    resultado = {}
    for cluster, variable in _VARIABLE_URI.items():
        uri = os.getenv(variable)
        info = {"variable": variable, "configurado": bool(uri), "host": _host_seguro(uri) if uri else None}
        if uri:
            inicio = time.time()
            client = None
            try:
                client = MongoClient(uri, serverSelectionTimeoutMS=TIMEOUT_MS)
                try:
                    nombre_db = client.get_default_database().name
                except ConfigurationError:
                    info.update(conectado=False,
                                error="La URL no incluye el nombre de la base de datos "
                                      "(agrégalo entre el host y el '?')")
                else:
                    client.admin.command("ping")
                    info.update(conectado=True, base_de_datos=nombre_db)
            except Exception as e:
                info.update(conectado=False, error=f"{type(e).__name__}: {e}"[:500])
            finally:
                if client is not None:
                    client.close()
            info["ms"] = round((time.time() - inicio) * 1000)
        resultado[cluster] = info
    return resultado


# ----------------------------------------------------------------------
# Asignación de bots a cluster
# ----------------------------------------------------------------------
def _bots_en_a(excepto=None):
    return sum(1 for bot, c in _asignacion.items() if c == "A" and bot != excepto)


def cluster_previsto(bot_id=None):
    """Cluster que se le asignaría a un bot si se encendiera ahora (para mostrarlo en el dashboard)."""
    with _lock:
        if _bots_en_a(excepto=bot_id) < MAX_BOTS_CLUSTER_A or "B" not in clusters_configurados():
            return "A"
        return "B"


def asignar_cluster(bot_id):
    """
    Asigna cluster a un bot que se está encendiendo. Devuelve (cluster, aviso).
    Si el A ya está lleno pero el B no está configurado, se usa el A y se devuelve un aviso.
    """
    with _lock:
        aviso = None
        if _bots_en_a(excepto=bot_id) < MAX_BOTS_CLUSTER_A:
            destino = "A"
        elif "B" in clusters_configurados():
            destino = "B"
        else:
            destino = "A"
            aviso = (f"El cluster A ya tiene {MAX_BOTS_CLUSTER_A} bots y MONGO_URI_B no está "
                     f"configurado: este bot también usará el cluster A")
        _asignacion[bot_id] = destino
        return destino, aviso


def liberar_cluster(bot_id):
    with _lock:
        _asignacion.pop(bot_id, None)


def cluster_asignado(bot_id):
    """Cluster actual de un bot encendido, o None si está apagado."""
    with _lock:
        return _asignacion.get(bot_id)


def cluster_de_la_peticion():
    """Cluster al que debe ir la petición HTTP actual (según X-Bot-Id)."""
    if has_request_context():
        bot_id = (request.headers.get("X-Bot-Id") or "").strip().lower()
        return cluster_asignado(bot_id) or "A"
    return "A"