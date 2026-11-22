"""
Hace que cada petición HTTP que sale de un hilo de bot lleve el encabezado
X-Bot-Id (por ejemplo "bot4"). La API usa ese encabezado para decidir a qué
cluster de MongoDB escribir.

Se apoya en que rutas_bots.py nombra los hilos "Hilo-bot1", "Hilo-bot4", etc.
No requiere modificar servicios/api_client.py, siempre que éste use la
librería `requests` (lo normal).
"""
import threading

_instalado = False


def instalar():
    global _instalado
    if _instalado:
        return

    try:
        import requests
    except ImportError:
        print("[CONTEXTO_BOT] La librería 'requests' no está instalada: los bots no enviarán X-Bot-Id")
        return

    request_original = requests.sessions.Session.request

    def request_con_bot(self, method, url, *args, **kwargs):
        nombre_hilo = threading.current_thread().name
        # args[2] sería 'headers' pasado por posición; en ese caso no se toca
        if nombre_hilo.startswith("Hilo-bot") and len(args) < 3:
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("X-Bot-Id", nombre_hilo[len("Hilo-"):])
            kwargs["headers"] = headers
        return request_original(self, method, url, *args, **kwargs)

    requests.sessions.Session.request = request_con_bot
    _instalado = True
    print("[CONTEXTO_BOT] Encabezado X-Bot-Id activado para los hilos de bots")
