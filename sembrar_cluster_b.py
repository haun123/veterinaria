"""
Copia del cluster A al cluster B las colecciones base, conservando los mismos _id:

    categorias, servicios, usuarios   -> catálogo para generar citas
    tutores, mascotas                 -> pacientes, para que un bot de historial pueda
                                         trabajar si le toca el cluster B
    historial                         -> historiales clínicos; los bots también los generan
                                         y modifican, así que el cluster B necesita los de partida

Como el bot que se conecte de 4.º (el que va al cluster B) puede ser cualquiera de los
cuatro, el cluster B necesita estos datos de partida. Es seguro correrlo varias veces
(upsert por _id) y no borra nada del cluster B.

Diferencia entre colecciones:
  - COLECCIONES_BASE  : se reemplaza el documento de B por el de A (el catálogo casi no cambia).
  - COLECCIONES_SOLO_NUEVAS : solo se insertan los documentos que B NO tiene; los que ya existen
    en B se dejan como están, para no pisar cambios hechos por un bot que trabaja en el cluster B.

El ETL y el dashboard cuentan estos documentos una sola vez (por _id) aunque existan
en los dos clusters.

Uso (desde la raíz del proyecto):   python sembrar_cluster_b.py
"""
from pymongo import ReplaceOne, UpdateOne

from clusters import clusters_configurados, get_mongo_db

COLECCIONES_BASE = ["categorias", "servicios", "usuarios", "tutores", "mascotas"]
COLECCIONES_SOLO_NUEVAS = ["historial"]
LOTE = 500


def _copiar(origen, destino, coleccion, construir_operacion):
    operaciones = []
    total = 0
    for doc in origen[coleccion].find():
        op = construir_operacion(doc)
        if op is None:
            continue
        operaciones.append(op)
        if len(operaciones) >= LOTE:
            destino[coleccion].bulk_write(operaciones, ordered=False)
            total += len(operaciones)
            operaciones = []
    if operaciones:
        destino[coleccion].bulk_write(operaciones, ordered=False)
        total += len(operaciones)
    return total


def _reemplazar(doc):
    return ReplaceOne({"_id": doc["_id"]}, doc, upsert=True)


def _insertar_si_falta(doc):
    campos = {k: v for k, v in doc.items() if k != "_id"}
    if not campos:
        return None
    return UpdateOne({"_id": doc["_id"]}, {"$setOnInsert": campos}, upsert=True)


def main():
    if "B" not in clusters_configurados():
        print("Falta MONGO_URI_B en el .env: no hay cluster B al que copiar.")
        return

    origen = get_mongo_db("A")
    destino = get_mongo_db("B")

    for coleccion in COLECCIONES_BASE:
        total = _copiar(origen, destino, coleccion, _reemplazar)
        print(f"[SEMBRAR] {coleccion}: {total} documentos copiados al cluster B")

    for coleccion in COLECCIONES_SOLO_NUEVAS:
        total = _copiar(origen, destino, coleccion, _insertar_si_falta)
        print(f"[SEMBRAR] {coleccion}: {total} documentos revisados (solo se insertan los que faltan en B)")

    print("Listo. El cluster B ya tiene los datos base.")


if __name__ == "__main__":
    main()
