import threading
import time
from datetime import datetime
from flask import Blueprint, jsonify
from database import get_neon_conn
from clusters import get_mongo_db, clusters_configurados
from etl.etl_pipeline import ejecutar_etl

etl_bp = Blueprint("etl_bp", __name__, url_prefix="/api")

ESTADO_ETL = {
    "estado": "Sincronizado",   # "Sincronizado" | "En ejecución" | "Error"
    "fase_animacion": "idle",   # "idle" | "mongo_a_etl" | "etl_a_postgres" | "completado" | "error"
    "ultima_sincronizacion": None,
    "ultimo_resultado": None,
    "errores_carga": 0,
    "auto_etl_activo": True,
    "ciclo_id": 0,
}

INTERVALO_ETL_SEGUNDOS = 180

_lock_etl = threading.Lock()
_scheduler_iniciado = False

COLECCIONES = ["categorias", "servicios", "usuarios", "tutores", "mascotas", "citas", "historial"]
# Estas colecciones se copian a ambos clusters con los mismos _id (sembrar_cluster_b.py);
# para no contarlas doble se cuentan por _id único. citas e historial solo viven en un
# cluster (según el bot que las creó), así que simplemente se suman.
COLECCIONES_CATALOGO = ("categorias", "servicios", "usuarios", "tutores", "mascotas", "historial")

TABLAS = [
    "categorias", "servicios", "usuarios", "tutores", "tutor_direcciones",
    "mascotas", "mascota_alergias", "citas", "historial_clinico",
    "historial_sintomas", "historial_tratamientos"
]
TABLAS_PRINCIPALES = ["categorias", "servicios", "usuarios", "tutores", "mascotas", "citas", "historial_clinico"]

# Caché corto de los conteos (el dashboard los pide muy seguido)
_TTL_CONTEOS = 2.0
_snap = {"t": 0.0, "data": None}
_lock_snap = threading.Lock()

# Si un cluster no responde, no se reintenta en cada consulta (cada intento espera 5 s)
_REINTENTO_CLUSTER_CAIDO = 20.0
_cluster_caido_hasta = {}


def _set_fase(fase):
    ESTADO_ETL["fase_animacion"] = fase


def _invalidar_snapshot():
    with _lock_snap:
        _snap["t"] = 0.0


def _correr_etl_seguro():
    """Ejecuta el ETL evitando que dos ejecuciones corran al mismo tiempo."""
    if not _lock_etl.acquire(blocking=False):
        return {"success": False, "busy": True, "message": "El ETL ya está en ejecución"}

    try:
        ESTADO_ETL["estado"] = "En ejecución"
        ESTADO_ETL["fase_animacion"] = "mongo_a_etl"
        ESTADO_ETL["ciclo_id"] += 1

        resultado = ejecutar_etl(on_fase=_set_fase)

        if resultado.get("success"):
            ESTADO_ETL["fase_animacion"] = "completado"
            ESTADO_ETL["estado"] = "Sincronizado"
            ESTADO_ETL["ultima_sincronizacion"] = resultado.get("ultima_sincronizacion")
            ESTADO_ETL["errores_carga"] = 0
        else:
            ESTADO_ETL["fase_animacion"] = "error"
            ESTADO_ETL["estado"] = "Error"
            ESTADO_ETL["errores_carga"] = resultado.get("errores", 1)

        ESTADO_ETL["ultimo_resultado"] = resultado
        return resultado
    except Exception as e:
        # Salvaguarda: si algo falla fuera de ejecutar_etl, no dejar el estado en "En ejecución"
        ESTADO_ETL["fase_animacion"] = "error"
        ESTADO_ETL["estado"] = "Error"
        ESTADO_ETL["errores_carga"] = 1
        resultado = {"success": False, "estado": "Error", "errores": 1, "error": str(e)}
        ESTADO_ETL["ultimo_resultado"] = resultado
        return resultado
    finally:
        _invalidar_snapshot()   # los conteos cambiaron: que la próxima consulta sea fresca
        _lock_etl.release()


def _loop_automatico():
    """Hilo de fondo que sincroniza cada INTERVALO_ETL_SEGUNDOS."""
    while True:
        time.sleep(INTERVALO_ETL_SEGUNDOS)
        if ESTADO_ETL["auto_etl_activo"]:
            print(f"[ETL AUTO] Ejecutando sincronización programada (cada {INTERVALO_ETL_SEGUNDOS}s)...")
            _correr_etl_seguro()


def iniciar_scheduler_etl():
    global _scheduler_iniciado
    if not _scheduler_iniciado:
        _scheduler_iniciado = True
        hilo = threading.Thread(target=_loop_automatico, name="Hilo-ETL-Auto", daemon=True)
        hilo.start()


@etl_bp.route("/etl/ejecutar", methods=["POST"])
def endpoint_ejecutar_etl():
    res = _correr_etl_seguro()
    if res.get("success"):
        code = 200
    elif res.get("busy"):
        code = 409  # ya hay un ETL corriendo, no es un error del ETL
    else:
        code = 500
    return jsonify(res), code


def _resumen_clusters():
    """Cuenta documentos por cluster y devuelve también los conteos unificados por colección."""
    configurados = clusters_configurados()
    resumen = {}
    ids_catalogo = {col: set() for col in COLECCIONES_CATALOGO}
    sumas = {col: 0 for col in COLECCIONES if col not in COLECCIONES_CATALOGO}
    ahora = time.time()

    for nombre in ("A", "B"):
        info = {"configurado": nombre in configurados, "conectado": False, "documentos": 0, "detalle": {}}
        if info["configurado"]:
            if ahora < _cluster_caido_hasta.get(nombre, 0):
                info["error"] = "Sin respuesta (reintentando en unos segundos)"
            else:
                try:
                    mdb = get_mongo_db(nombre)
                    existentes = set(mdb.list_collection_names())
                    for col in COLECCIONES:
                        n = mdb[col].count_documents({}) if col in existentes else 0
                        if col in COLECCIONES_CATALOGO:
                            if n:
                                ids_catalogo[col].update(d["_id"] for d in mdb[col].find({}, {"_id": 1}))
                        else:
                            sumas[col] += n
                        info["detalle"][col] = n
                        info["documentos"] += n
                    info["conectado"] = True
                    _cluster_caido_hasta.pop(nombre, None)
                except Exception as e:
                    info["error"] = str(e)
                    _cluster_caido_hasta[nombre] = time.time() + _REINTENTO_CLUSTER_CAIDO
        resumen[nombre] = info

    conteo_unificado = {}
    for col in COLECCIONES:
        conteo_unificado[col] = len(ids_catalogo[col]) if col in COLECCIONES_CATALOGO else sumas[col]
    return resumen, conteo_unificado


def _calcular_snapshot():
    clusters, conteo_mongo = _resumen_clusters()

    conteo_neon = {}
    total_neon = 0
    tablas_con_datos = 0
    ultima_bitacora = None

    conn = get_neon_conn()
    cur = conn.cursor()
    try:
        for tabla in TABLAS:
            cur.execute(f"SELECT COUNT(*) FROM {tabla};")
            c = cur.fetchone()[0]
            conteo_neon[tabla] = c
            total_neon += c
            if c > 0:
                tablas_con_datos += 1

        cur.execute("""
            SELECT fecha_fin, estado, registros_procesados, registros_eliminados, errores
            FROM etl_bitacora
            ORDER BY ejecucion_id DESC
            LIMIT 1;
        """)
        fila = cur.fetchone()
        if fila:
            ultima_bitacora = {
                "fecha_fin": fila[0].isoformat() if fila[0] else None,
                "estado": fila[1],
                "registros_procesados": fila[2],
                "registros_eliminados": fila[3],
                "errores": fila[4],
            }
    finally:
        cur.close()
        conn.close()

    return {
        "clusters": clusters,
        "conteo_mongo": conteo_mongo,
        "conteo_neon": conteo_neon,
        "total_neon": total_neon,
        "tablas_con_datos": tablas_con_datos,
        "ultima_bitacora": ultima_bitacora,
    }


def _snapshot():
    with _lock_snap:
        if _snap["data"] is not None and (time.time() - _snap["t"]) < _TTL_CONTEOS:
            return _snap["data"]
    data = _calcular_snapshot()
    with _lock_snap:
        _snap["data"] = data
        _snap["t"] = time.time()
    return data


@etl_bp.route("/estado", methods=["GET"])
def endpoint_estado_general():
    """Devuelve todas las métricas en tiempo real de MongoDB (todos los clusters), Neon PostgreSQL y el ETL."""
    iniciar_scheduler_etl()

    snap = _snapshot()
    clusters = snap["clusters"]
    conteo_mongo = snap["conteo_mongo"]
    conteo_neon = snap["conteo_neon"]
    ultima_bitacora = snap["ultima_bitacora"]

    total_mongo = sum(conteo_mongo.values())
    docs_sincronizados = sum(conteo_neon[t] for t in TABLAS_PRINCIPALES)
    clusters_activos = sum(1 for c in clusters.values() if c["conectado"])

    if not ESTADO_ETL["ultima_sincronizacion"] and ultima_bitacora and ultima_bitacora["fecha_fin"]:
        ESTADO_ETL["ultima_sincronizacion"] = ultima_bitacora["fecha_fin"]

    # Bots activos para "Usuarios / Procesos conectados"
    try:
        from bots_CRUD.rutas_bots import ESTADO_BOTS
        bots_activos = sum(1 for b in ESTADO_BOTS.values() if b.get("activo"))
    except Exception:
        bots_activos = 0

    return jsonify({
        "success": True,
        "mongodb": {
            "documentos_totales": total_mongo,
            "documentos_sincronizados": docs_sincronizados,
            "clusters_activos": clusters_activos,
            "usuarios_conectados": 1 + bots_activos,  # API Flask + Bots encendidos
            "detalle_colecciones": conteo_mongo,
            "clusters": clusters,
        },
        "postgresql": {
            "registros_totales": snap["total_neon"],
            "tablas_sincronizadas": f"{snap['tablas_con_datos']} / {len(TABLAS)}",
            "errores_carga": ESTADO_ETL["errores_carga"],
            "ultima_sincronizacion": ESTADO_ETL["ultima_sincronizacion"],
            "detalle_tablas": conteo_neon,
        },
        "etl": {
            "estado": ESTADO_ETL["estado"],
            "fase_animacion": ESTADO_ETL["fase_animacion"],
            "ciclo_id": ESTADO_ETL["ciclo_id"],
            "ultima_bitacora": ultima_bitacora,
            "ultimo_resultado": ESTADO_ETL["ultimo_resultado"],  # incluye registros_eliminados
        }
    }), 200
