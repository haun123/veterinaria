import threading
import time
from datetime import datetime
from flask import Blueprint, jsonify
from database import get_mongo_db, get_neon_conn
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

_lock_etl = threading.Lock()
_scheduler_iniciado = False


def _correr_etl_seguro():
    """Ejecuta el ETL evitando que dos ejecuciones corran al mismo tiempo."""
    if not _lock_etl.acquire(blocking=False):
        return {"success": False, "busy": True, "message": "El ETL ya está en ejecución"}

    try:
        ESTADO_ETL["estado"] = "En ejecución"
        ESTADO_ETL["fase_animacion"] = "mongo_a_etl"
        ESTADO_ETL["ciclo_id"] += 1

        resultado = ejecutar_etl()

        if resultado.get("success"):
            # Si tu frontend espera "etl_a_postgres" para terminar la animación,
            # cambia esta línea de vuelta a "etl_a_postgres".
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
        _lock_etl.release()


def _loop_automatico_60s():
    """Hilo de fondo que sincroniza cada 60 segundos (1 minuto)."""
    while True:
        time.sleep(60)
        if ESTADO_ETL["auto_etl_activo"]:
            print("[ETL AUTO] Ejecutando sincronización programada (cada 60s)...")
            _correr_etl_seguro()


def iniciar_scheduler_etl():
    global _scheduler_iniciado
    if not _scheduler_iniciado:
        _scheduler_iniciado = True
        hilo = threading.Thread(target=_loop_automatico_60s, name="Hilo-ETL-Auto", daemon=True)
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


@etl_bp.route("/estado", methods=["GET"])
def endpoint_estado_general():
    """Devuelve todas las métricas en tiempo real de MongoDB, Neon PostgreSQL y el estado del ETL."""
    iniciar_scheduler_etl()

    # 1. Conteos en MongoDB
    mongo_db = get_mongo_db()
    colecciones = ["categorias", "servicios", "usuarios", "tutores", "mascotas", "citas", "historial"]
    existentes = set(mongo_db.list_collection_names())
    conteo_mongo = {}
    total_mongo = 0
    for col in colecciones:
        c = mongo_db[col].count_documents({}) if col in existentes else 0
        conteo_mongo[col] = c
        total_mongo += c

    # 2. Conteos en Neon PostgreSQL
    tablas = [
        "categorias", "servicios", "usuarios", "tutores", "tutor_direcciones",
        "mascotas", "mascota_alergias", "citas", "historial_clinico",
        "historial_sintomas", "historial_tratamientos"
    ]
    conteo_neon = {}
    total_neon = 0
    tablas_con_datos = 0
    ultima_bitacora = None

    conn = get_neon_conn()
    cur = conn.cursor()
    try:
        for tabla in tablas:
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
            if not ESTADO_ETL["ultima_sincronizacion"] and fila[0]:
                ESTADO_ETL["ultima_sincronizacion"] = fila[0].isoformat()
    finally:
        cur.close()
        conn.close()

    # Documentos sincronizados (entidades principales con mongo_id en Neon)
    tablas_principales = ["categorias", "servicios", "usuarios", "tutores", "mascotas", "citas", "historial_clinico"]
    docs_sincronizados = sum(conteo_neon[t] for t in tablas_principales)

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
            "usuarios_conectados": 1 + bots_activos,  # API Flask + Bots encendidos
            "detalle_colecciones": conteo_mongo,
        },
        "postgresql": {
            "registros_totales": total_neon,
            "tablas_sincronizadas": f"{tablas_con_datos} / {len(tablas)}",
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
