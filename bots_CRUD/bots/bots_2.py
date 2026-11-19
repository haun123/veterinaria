from servicios.api_client import consultar, registrar
from generadores.historial import generar_historial

USUARIO_ID = "6ae22182f2102fe7ce813716"

def ejecutar_bot2(stop_event):
    print("\n========== BOT 2 INICIADO (Historial Clínico) ==========")

    try:
        respuesta = consultar("pacientes")
        pacientes = respuesta.get("data", [])
        print(f"[BOT 2] Consulta inicial OK -> {len(pacientes)} tutores/pacientes encontrados.")
    except Exception as error:
        print(f"[BOT 2] No se pudieron consultar los pacientes: {error}")
        return

    if not pacientes:
        print("[BOT 2] Detenido: No hay pacientes disponibles en MongoDB.")
        return

    contador = 0
    exitosos = 0
    fallidos = 0
    MAX_ACCIONES = 2

    while not stop_event.is_set() and contador < MAX_ACCIONES:
        contador += 1
        try:
            mascota_id, datos_historial = generar_historial(pacientes, USUARIO_ID)
            print(f"[BOT 2] ({contador}/{MAX_ACCIONES}) Agregando historial -> Mascota ID: {mascota_id}")
            res = registrar(f"/api/historial/agregar/{mascota_id}", datos_historial)
            exitosos += 1
            msg = res.get("message", "OK") if isinstance(res, dict) else f"Historial actualizado ({len(res)} entradas)"
            print(f"[BOT 2] [GUARDADO] Historial #{contador} -> {msg}")
        except Exception as error:
            fallidos += 1
            print(f"[BOT 2] [ERROR] Historial #{contador}: {error}")

        if contador < MAX_ACCIONES:
            stop_event.wait(1)

    print(f"\n[BOT 2] Finalizado. Intentos: {contador} | Exitosos: {exitosos} | Fallidos: {fallidos}")