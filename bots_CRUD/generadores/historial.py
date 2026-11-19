import json
import random
from pathlib import Path
from faker import Faker

fake = Faker("es_MX")

RUTA_ESTRUCTURAS = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "estructuras.json"
)

with open(RUTA_ESTRUCTURAS, "r", encoding="utf-8") as archivo:
    ESTRUCTURAS = json.load(archivo)

def generar_historial(pacientes, usuario_id):
    """
    Generar un historial ficticio para una mascota existente.
    """
    estructura = ESTRUCTURAS["historial"]

    mascotas = []

    for tutor in pacientes:
        mascotas.extend(tutor.get("mascotas", []))

    if not mascotas:
        raise ValueError(
            "No hay mascotas disponibles para generar un historial."
        )

    if not usuario_id:
        raise ValueError("Se necesita un ID de usuario válido.")

    mascota = random.choice(mascotas)
    mascota_id = str(mascota["_id"])

    sintomas_disponibles = estructura["sintomas"]["valores"]

    sintomas_posibles = [
        sintoma for sintoma in sintomas_disponibles
        if sintoma != "Ninguno"
    ]

    if random.choice([True, False]):
        sintomas = ["Ninguno"]
    else:
        sintomas = random.sample(
            sintomas_posibles,
            k=random.randint(1, min(3, len(sintomas_posibles)))
        )

    peso = mascota.get("peso")

    if peso is None:
        peso = round(random.uniform(1, 60), 2)

    temperatura = round(random.uniform(37.5, 39.5), 1)

    tratamientos = []

    if random.choice([True, False]):
        tratamientos.append({
            "medicamento": "Tratamiento de prueba",
            "dosis": "Dato simulado",
            "frecuencia": "Dato simulado",
            "duracionDias": random.randint(1, 7)
        })

    datos_historial = {
        "usuario_id": str(usuario_id),
        "motivo_consulta": random.choice(
            estructura["motivo_consulta"]["valores"]
        ),
        "peso_kg": float(peso),
        "temperatura_c": temperatura,
        "sintomas": sintomas,
        "diagnostico": random.choice(
            estructura["diagnostico"]["valores"]
        ),
        "tratamientos": tratamientos,
        "observaciones": fake.sentence()
    }

    return mascota_id, datos_historial