import random
from servicios.api_client import consultar, registrar
from generadores.citas import generar_cita
from generadores.historial import generar_historial

# <--- AGREGADO: Importar el avisador para la animación
try:
    from rutas_bots import registrar_evento_bot
except ImportError:
    def registrar_evento_bot(*args, **kwargs): pass
# <--- FIN AGREGADO

USUARIO_ID = "6ae22182f2102fe7ce813716"

def ejecutar_bot3(stop_event):
    print("\n========== BOT 3 INICIADO (Mixto: Citas e Historial) ==========")

    try:
        categorias = consultar("categorias").get("data", [])
        servicios = consultar("servicios").get("data", [])
        pacientes = consultar("pacientes").get("data", [])
        print(
            f"[BOT 3] Consulta inicial OK -> {len(categorias)} categorías, "
            f"{len(servicios)} servicios, {len(pacientes)} pacientes."
        )
    except Exception as error:
        print(f"[BOT 3] Error al obtener información: {error}")
        registrar_evento_bot("bot3", "error", detalle=str(error), error=True)  # <--- AGREGADO
        return

    if not categorias or not servicios or not pacientes:
        print("[BOT 3] Detenido: Faltan categorías, servicios o pacientes en la base.")
        registrar_evento_bot("bot3", "error", detalle="Faltan datos iniciales")  # <--- AGREGADO
        return

    contador = 0
    exitosos = 0
    fallidos = 0

    while not stop_event.is_set():
        contador += 1
        try:
            operacion = random.choice(["citas", "historial"])
            if operacion == "citas":
                datos = generar_cita(categorias, servicios)
                print(f"[BOT 3] ({contador}) [CITA] Mascota: {datos.get('mascota_nombre')}")
                registrar_evento_bot("bot3", "enviando_api", operacion="cita", detalle=f"Cita #{contador}")  # <--- AGREGADO (Tramo Bot -> API)
                res = registrar("crear_cita", datos)
                registrar_evento_bot("bot3", "guardado_mongo", operacion="cita", detalle=f"Cita #{contador} guardada", exito=True)  # <--- AGREGADO (Tramo API -> MongoDB)
                print(f"[BOT 3] [GUARDADO] Cita #{contador} -> ID: {res.get('id_generado', 'OK')}")
            else:
                mascota_id, datos = generar_historial(pacientes, USUARIO_ID)
                print(f"[BOT 3] ({contador}) [HISTORIAL] Mascota ID: {mascota_id}")
                registrar_evento_bot("bot3", "enviando_api", operacion="historial", detalle=f"Historial #{contador}")  # <--- AGREGADO (Tramo Bot -> API)
                res = registrar(f"/api/historial/agregar/{mascota_id}", datos)
                msg = res.get("message", "OK") if isinstance(res, dict) else f"Historial actualizado ({len(res)} entradas)"
                registrar_evento_bot("bot3", "guardado_mongo", operacion="historial", detalle=msg, exito=True)  # <--- AGREGADO (Tramo API -> MongoDB)
                print(f"[BOT 3] [GUARDADO] Historial #{contador} -> {msg}")
            exitosos += 1
        except Exception as error:
            fallidos += 1
            registrar_evento_bot("bot3", "error", detalle=str(error), error=True)  # <--- AGREGADO
            print(f"[BOT 3] [ERROR] Operación #{contador}: {error}")

        stop_event.wait(9)

    print(f"\n[BOT 3] Finalizado. Intentos: {contador} | Exitosos: {exitosos} | Fallidos: {fallidos}")