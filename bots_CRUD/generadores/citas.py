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

with open(RUTA_ESTRUCTURAS, "r", encoding = "UTF-8") as archivo:
    ESTRUCTURAS = json.load(archivo)

def generar_cita(categorias, servicios):
    """
    Genera los datos de las citas usando categorias y servicios existentes
    """
    if not categorias:
        raise ValueError("No hay categorias disponibles")
    if not servicios:
        raise ValueError("No hay servicios disponibles")

    categoria = random.choice(categorias)
    servicio = random.choice(servicios)

    estructura = ESTRUCTURAS["citas"]

    razas = categoria.get("razas") or ["Mestizo"]
    raza = random.choice(razas)

    alergias_disponibles = [
        "Pollo",
        "Lacteos",
        "Polen",
        "Picadura de insectos"
    ]

    cantidad_alergias = random.randint(0, 2)

    alergias = random.sample(
        alergias_disponibles,
        cantidad_alergias
    )

    configuracion_peso = estructura["mascota_peso"]

    peso = round(
        random.uniform(
            configuracion_peso["min"],
            configuracion_peso["max"]
        ),
        2
    )

    datos_cita = {
        "tutor_nombre": fake.first_name(),
        "tutor_apellidos": fake.last_name() + " " + fake.last_name(),
        "tutor_telefono": fake.numerify(text = "##########"),
        "tutor_email": fake.email(),

        "categoria_id": str(categoria["_id"]),

        "mascota_nombre": fake.first_name(),
        "mascota_raza": raza,
        "mascota_sexo" : random.choice(
            estructura["mascota_sexo"]["valores"]
        ),
        "mascota_color": random.choice([
            "Negro",
            "Blanco",
            "Café",
            "Dorado",
            "Gris"
        ]),
        "mascota_peso": peso,
        "mascota_alergias": ", ".join(alergias),

        "servicio_id": str(servicio["_id"]),

        "motivo": random.choice(
            estructura["motivo"]["valores"]
        )
    }

    return datos_cita