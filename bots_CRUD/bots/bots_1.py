from servicios.api_client import consultar, registrar
from generadores.citas import generar_cita

def ejecutar_bot1(stop_event):
    print("\n========== BOT 1 INICIADO (Citas) ==========")

    try:
        categorias = consultar("categorias").get("data", [])
        servicios = consultar("servicios").get("data", [])
        print(f"[BOT 1] Consulta inicial OK -> {len(categorias)} categorías, {len(servicios)} servicios.")
    except Exception as error:
        print(f"[BOT 1] No se pudo iniciar: {error}")
        return

    if not categorias or not servicios:
        print("[BOT 1] Detenido: No hay categorías o servicios disponibles.")
        return

    contador = 0
    exitosas = 0
    fallidas = 0
    MAX_ACCIONES = 2

    while not stop_event.is_set() and contador < MAX_ACCIONES:
        contador += 1
        try:
            datos_cita = generar_cita(categorias, servicios)
            print(
                f"[BOT 1] ({contador}/{MAX_ACCIONES}) Generando cita -> "
                f"Tutor: {datos_cita.get('tutor_nombre')} {datos_cita.get('tutor_apellidos')} | "
                f"Mascota: {datos_cita.get('mascota_nombre')}"
            )
            respuesta = registrar("crear_cita", datos_cita)
            exitosas += 1
            print(f"[BOT 1] [GUARDADO] Cita #{contador} -> ID: {respuesta.get('id_generado', 'OK')}")
        except Exception as error:
            fallidas += 1
            print(f"[BOT 1] [ERROR] Cita #{contador}: {error}")

        if contador < MAX_ACCIONES:
            stop_event.wait(1)

    print(f"\n[BOT 1] Finalizado. Intentos: {contador} | Exitosas: {exitosas} | Fallidas: {fallidas}")