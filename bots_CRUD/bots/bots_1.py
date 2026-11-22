from servicios.api_client import consultar, registrar
from generadores.citas import generar_cita

# Avisador para la animación (módulo compartido, con respaldo por si se corre suelto)
try:
    from eventos_bots import registrar_evento_bot
except ImportError:
    def registrar_evento_bot(*args, **kwargs): pass

def ejecutar_bot1(stop_event):
    print("\n========== BOT 1 INICIADO (Citas) ==========")

    try:
        categorias = consultar("categorias").get("data", [])
        servicios = consultar("servicios").get("data", [])
        print(f"[BOT 1] Consulta inicial OK -> {len(categorias)} categorías, {len(servicios)} servicios.")
    except Exception as error:
        print(f"[BOT 1] No se pudo iniciar: {error}")
        registrar_evento_bot("bot1", "error", detalle=str(error), error=True)
        return

    if not categorias or not servicios:
        print("[BOT 1] Detenido: No hay categorías o servicios disponibles.")
        registrar_evento_bot("bot1", "error", detalle="Sin categorías o servicios")
        return

    contador = 0
    exitosas = 0
    fallidas = 0

    while not stop_event.is_set():
        contador += 1
        try:
            datos_cita = generar_cita(categorias, servicios)
            print(
                f"[BOT 1] ({contador}) Generando cita -> "
                f"Tutor: {datos_cita.get('tutor_nombre')} {datos_cita.get('tutor_apellidos')} | "
                f"Mascota: {datos_cita.get('mascota_nombre')}"
            )
            registrar_evento_bot("bot1", "enviando_api", operacion="cita", detalle=f"Cita #{contador}")  # Tramo Bot -> API
            respuesta = registrar("crear_cita", datos_cita)
            exitosas += 1
            registrar_evento_bot("bot1", "guardado_mongo", operacion="cita", detalle=f"Cita #{contador} guardada", exito=True)  # Tramo API -> MongoDB
            print(f"[BOT 1] [GUARDADO] Cita #{contador} -> ID: {respuesta.get('id_generado', 'OK')}")
        except Exception as error:
            fallidas += 1
            registrar_evento_bot("bot1", "error", operacion="cita", detalle=str(error), error=True)
            print(f"[BOT 1] [ERROR] Cita #{contador}: {error}")

        stop_event.wait(9)

    print(f"\n[BOT 1] Finalizado. Intentos: {contador} | Exitosas: {exitosas} | Fallidas: {fallidas}")
