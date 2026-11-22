import random
from servicios.api_client import consultar, registrar
from generadores.citas import generar_cita
from generadores.historial import generar_historial

# Avisador para la animación (módulo compartido, con respaldo por si se corre suelto)
try:
    from eventos_bots import registrar_evento_bot
except ImportError:
    def registrar_evento_bot(*args, **kwargs): pass

USUARIO_ID = "6ae22182f2102fe7ce813716"

# Cada cuántas operaciones se vuelve a consultar la lista de pacientes del cluster donde escribe
# (las citas nuevas crean tutores/mascotas nuevos que luego pueden recibir historial)
REFRESCAR_PACIENTES_CADA = 5


def _cargar_pacientes():
    """Devuelve los pacientes de su cluster; si falla o no hay, lista vacía (no detiene el bot)."""
    try:
        return consultar("pacientes").get("data", [])
    except Exception as error:
        print(f"[BOT 4] No se pudieron refrescar los pacientes: {error}")
        return []


def ejecutar_bot4(stop_event):
    """
    Bot 4 (Mixto: Citas e Historial).
    Es igual que el bot 3. El cluster donde escribe NO lo decide el bot: la API lo
    identifica por el encabezado X-Bot-Id (lo agrega contexto_bot.py) y rutas_bots.py
    le asignó A o B al encenderlo (los primeros 3 bots conectados van al A; el 4.º, al B).
    """
    print("\n========== BOT 4 INICIADO (Mixto) ==========")

    try:
        categorias = consultar("categorias").get("data", [])
        servicios = consultar("servicios").get("data", [])
        pacientes = _cargar_pacientes()
        print(
            f"[BOT 4] Consulta inicial OK -> {len(categorias)} categorías, "
            f"{len(servicios)} servicios, {len(pacientes)} pacientes."
        )
    except Exception as error:
        print(f"[BOT 4] Error al obtener información: {error}")
        registrar_evento_bot("bot4", "error", detalle=str(error), error=True)
        return

    if not categorias or not servicios:
        print("[BOT 4] Detenido: su cluster no tiene categorías o servicios (si es el B, ejecuta sembrar_cluster_b.py)")
        registrar_evento_bot("bot4", "error", detalle="Su cluster no tiene categorías/servicios (si es el B, ejecuta sembrar_cluster_b.py)")
        return

    contador = 0
    exitosos = 0
    fallidos = 0

    while not stop_event.is_set():
        contador += 1
        try:
            # Si todavía no hay pacientes en su cluster, solo se pueden crear citas
            if not pacientes or contador % REFRESCAR_PACIENTES_CADA == 0:
                pacientes = _cargar_pacientes() or pacientes

            operacion = random.choice(["citas", "historial"]) if pacientes else "citas"

            if operacion == "citas":
                datos = generar_cita(categorias, servicios)
                print(f"[BOT 4] ({contador}) [CITA] Mascota: {datos.get('mascota_nombre')}")
                registrar_evento_bot("bot4", "enviando_api", operacion="cita", detalle=f"Cita #{contador}")  # Tramo Bot -> API
                res = registrar("crear_cita", datos)
                registrar_evento_bot("bot4", "guardado_mongo", operacion="cita", detalle=f"Cita #{contador} guardada", exito=True)  # Tramo API -> MongoDB
                print(f"[BOT 4] [GUARDADO] Cita #{contador} -> ID: {res.get('id_generado', 'OK')}")
            else:
                mascota_id, datos = generar_historial(pacientes, USUARIO_ID)
                print(f"[BOT 4] ({contador}) [HISTORIAL] Mascota ID: {mascota_id}")
                registrar_evento_bot("bot4", "enviando_api", operacion="historial", detalle=f"Historial #{contador}")  # Tramo Bot -> API
                res = registrar(f"/api/historial/agregar/{mascota_id}", datos)
                msg = res.get("message", "OK") if isinstance(res, dict) else f"Historial actualizado ({len(res)} entradas)"
                registrar_evento_bot("bot4", "guardado_mongo", operacion="historial", detalle=msg, exito=True)  # Tramo API -> MongoDB
                print(f"[BOT 4] [GUARDADO] Historial #{contador} -> {msg}")
            exitosos += 1
        except Exception as error:
            fallidos += 1
            registrar_evento_bot("bot4", "error", detalle=str(error), error=True)
            print(f"[BOT 4] [ERROR] Operación #{contador}: {error}")

        stop_event.wait(9)

    print(f"\n[BOT 4] Finalizado. Intentos: {contador} | Exitosos: {exitosos} | Fallidos: {fallidos}")
