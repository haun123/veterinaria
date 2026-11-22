"""
Copia del cluster A al cluster B las colecciones base, conservando los mismos _id:

    categorias, servicios, usuarios   -> catálogo para generar citas
    tutores, mascotas                 -> pacientes, para que un bot de historial pueda
                                         trabajar si le toca el cluster B

Como el bot que se conecte de 4.º (el que va al cluster B) puede ser cualquiera de los
cuatro, el cluster B necesita estos datos de partida. Es seguro correrlo varias veces
(upsert por _id) y no borra nada del cluster B.

El ETL y el dashboard cuentan estos documentos una sola vez (por _id) aunque existan
en los dos clusters.

Uso (desde la raíz del proyecto):   python sembrar_cluster_b.py
"""
from pymongo import ReplaceOne

from clusters import clusters_configurados, get_mongo_db

COLECCIONES_BASE = ["categorias", "servicios", "usuarios", "tutores", "mascotas"]
LOTE = 500


def main():
    if "B" not in clusters_configurados():
        print("Falta MONGO_URI_B en el .env: no hay cluster B al que copiar.")
        return

    origen = get_mongo_db("A")
    destino = get_mongo_db("B")

    for coleccion in COLECCIONES_BASE:
        operaciones = []
        total = 0
        for doc in origen[coleccion].find():
            operaciones.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))
            if len(operaciones) >= LOTE:
                destino[coleccion].bulk_write(operaciones, ordered=False)
                total += len(operaciones)
                operaciones = []
        if operaciones:
            destino[coleccion].bulk_write(operaciones, ordered=False)
            total += len(operaciones)
        print(f"[SEMBRAR] {coleccion}: {total} documentos copiados al cluster B")

    print("Listo. El cluster B ya tiene los datos base.")


if __name__ == "__main__":
    main()
