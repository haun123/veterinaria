import requests
from config.config import API_BASE_URL, ENDPOINTS, REQUEST_TIMEOUT

def construir_url(endpoint):
    """
    URL completa de un endpoint
    """
    ruta = ENDPOINTS.get(endpoint, endpoint)
    return f"{API_BASE_URL.rstrip('/')}/{ruta.lstrip('/')}"

def realizar_solicitud(metodo, endpoint, params = None, datos = None):
    """
    Ejecuta y devuelve una solicitud HTTP con una repsuesta
    """
    url = construir_url(endpoint)
    try:
        respuesta = requests.request(
            method = metodo,
            url = url,
            params = params,
            json = datos,
            timeout = REQUEST_TIMEOUT
        )
        try:
            resultado = respuesta.json()
        except ValueError:
            resultado = respuesta.text

        respuesta.raise_for_status()
        return resultado
    
    except requests.exceptions.Timeout as error:
        raise RuntimeError(
           "La solicitud excedión el tiempo de espera" 
        ) from error

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "No se pudo conectar con el servidor Flask"
        ) from error

    except requests.exceptions.HTTPError as error:
        raise RuntimeError(
            f"Error HTTP {respuesta.status_code}: {resultado}"
        ) from error

    except request.exceptions.RequestException as error:
        raise RuntimeError(
            f"Error en la solicitud: {error}"
        ) from error

def consultar(endpoint, params = None):
    """
    Solicitud GET
    """
    return realizar_solicitud(
        "GET",
        endpoint,
        params = params
    )

def registrar(endpoint, datos):
    """
    Solicitud POST
    """
    return realizar_solicitud(
        "POST",
        endpoint,
        datos = datos
    )

def actualizar(endpoint, datos = None):
    """
    Solicitud PUT
    """
    return solicitar_solicitud(
        "PUT",
        endpoint,
        datos = datos
    )
