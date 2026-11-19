import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL=os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:5000"
)

ENDPOINTS = {
    #CONSULTAS
    "servicios": "/api/servicios",
    "categorias": "/api/categorias",
    "pacientes": "/api/pacientes/listar",
    "citas": "/api/citas",
    "historial": "/api/historial/buscar",

    #REGISTROS
    "crear_cita": "/api/citas/crear",
    "agregar_historia": "/api/historial/agregar",

    #ACTUALIZACIONES
    "cancelar_cita": "/api/citas/cancelar"
}

REQUEST_TIMEOUT = 30
