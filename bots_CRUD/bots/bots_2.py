from servicios.api_client import consultar, registrar
from generadores.historial import generar_historial

# Avisador para la animación (módulo compartido, con respaldo por si se corre suelto)
try:
    from eventos_bots import registrar_evento_bot
except ImportError:
    def registrar_evento_bot(*args, **kwargs): pass

USUARIO_ID = "6ae22182f2102fe7ce813716"

def ejecutar_bot2(stop_event):
    print("\n========== BOT 2 INICIADO (Historial Clínico) ==========")

    try:
        respuesta = consultar("pacientes")
        pacientes = respuesta.get("data", [])
        print(f"[BOT 2] Consulta inicial OK -> {len(pacientes)} tutores/pacientes encontrados.")
    except Exception as error:
        print(f"[BOT 2] No se pudieron consultar los pacientes: {error}")
        registrar_evento_bot("bot2", "error", detalle=str(error), error=True)
        return

    if not pacientes:
        print("[BOT 2] Detenido: No hay pacientes disponibles en MongoDB.")
        registrar_evento_bot("bot2", "error", detalle="Sin pacientes disponibles")
        return

    contador = 0
    exitosos = 0
    fallidos = 0

    while not stop_event.is_set():
        contador += 1
        try:
            mascota_id, datos_historial = generar_historial(pacientes, USUARIO_ID)
            print(f"[BOT 2] ({contador}) Agregando historial -> Mascota ID: {mascota_id}")
            registrar_evento_bot("bot2", "enviando_api", operacion="historial", detalle=f"Historial #{contador}")  # Tramo Bot -> API
            res = registrar(f"/api/historial/agregar/{mascota_id}", datos_historial)
            exitosos += 1
            msg = res.get("message", "OK") if isinstance(res, dict) else f"Historial actualizado ({len(res)} entradas)"
            registrar_evento_bot("bot2", "guardado_mongo", operacion="historial", detalle=msg, exito=True)  # Tramo API -> MongoDB
            print(f"[BOT 2] [GUARDADO] Historial #{contador} -> {msg}")
        except Exception as error:
            fallidos += 1
            registrar_evento_bot("bot2", "error", operacion="historial", detalle=str(error), error=True)
            print(f"[BOT 2] [ERROR] Historial #{contador}: {error}")

        stop_event.wait(9)

    print(f"\n[BOT 2] Finalizado. Intentos: {contador} | Exitosos: {exitosos} | Fallidos: {fallidos}")
