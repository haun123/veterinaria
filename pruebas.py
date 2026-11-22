"""
Prueba de conexión INDEPENDIENTE de Flask, de los bots y del resto del proyecto.

Uso (desde la raíz del proyecto, con el entorno virtual activo):
    python probar_conexion.py

Lee el .env, prueba MongoDB A, MongoDB B (si existe MONGO_URI_B) y Neon, y mide cuánto
tarda cada paso. No imprime usuario ni contraseña.
"""
import os
import re
import sys
import time

TIMEOUT_S = 10


def seg(desde):
    return f"{time.time() - desde:.1f} s"


def limpiar(texto):
    """Quita usuario:contraseña de cualquier texto que los pudiera contener."""
    return re.sub(r"(://)[^@/\s]+@", r"\1***@", str(texto))


def host_de(uri):
    sin_esquema = re.sub(r"^[a-zA-Z0-9+.\-]+://", "", uri)
    return re.split(r"[/?]", sin_esquema.split("@")[-1])[0]


def cargar_env():
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("(python-dotenv no está instalado: solo se leen variables ya definidas en el sistema)")
        return
    raiz = os.path.dirname(os.path.abspath(__file__))
    encontrados = []
    for ruta in (os.path.join(raiz, ".env"), os.path.join(raiz, "bots_CRUD", ".env")):
        if os.path.isfile(ruta):
            load_dotenv(ruta)
            encontrados.append(os.path.relpath(ruta, raiz))
    print("Archivos .env encontrados:", ", ".join(encontrados) if encontrados else "NINGUNO")


def pistas_mongo(mensaje):
    m = mensaje.lower()
    print("   Qué suele significar:")
    if "dns" in m or "resolution lifetime" in m or "nodename" in m or "name or service" in m:
        print("   - El DNS de tu red no resuelve la URL 'mongodb+srv'. Prueba cambiar el DNS a 8.8.8.8,")
        print("     o usar en Atlas la URL estándar 'mongodb://' (Connect > Drivers > versión anterior).")
    if "authentication" in m or "auth failed" in m or "bad auth" in m:
        print("   - Usuario o contraseña incorrectos (si tiene @ # / hay que codificarlos: @ = %40).")
    if "timed out" in m or "no servers found" in m or "ssl" in m or "tls" in m or "replica set members" in m:
        print("   - Casi siempre es Atlas bloqueando tu IP: Atlas > Network Access > 'Add Current IP Address'.")
        print("     También revisa VPN/antivirus/firewall y que el cluster no esté pausado (Atlas lo pausa si no se usa).")


def probar_mongo(nombre, variable):
    print(f"\n=== MongoDB {nombre} ({variable}) ===")
    uri = os.getenv(variable)
    if not uri:
        print("No está definida en el .env -> se omite")
        return
    print("Host:", host_de(uri))
    print("Tipo de URL:", "SRV (mongodb+srv)" if uri.startswith("mongodb+srv") else "estándar (mongodb://)")

    try:
        import pymongo
        from pymongo import MongoClient
    except ImportError:
        print("pymongo no está instalado en este entorno de Python")
        return
    print("Versión de pymongo:", pymongo.version)

    t = time.time()
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=TIMEOUT_S * 1000)
    except Exception as e:
        print(f"1) FALLÓ crear el cliente tras {seg(t)}: {type(e).__name__}")
        print("  ", limpiar(e)[:900])
        pistas_mongo(str(e))
        return
    print(f"1) Cliente creado en {seg(t)}  (aquí se resuelve el DNS de la URL)")

    try:
        db = client.get_default_database()
        print("2) Nombre de la base en la URL:", db.name)
    except Exception as e:
        print("2) La URL NO incluye nombre de base:", limpiar(e))
        print("   Agrégalo entre el host y el '?', por ejemplo ...mongodb.net/veterinaria?retryWrites=true")
        return

    t = time.time()
    try:
        client.admin.command("ping")
        print(f"3) Ping OK en {seg(t)}")
    except Exception as e:
        print(f"3) FALLÓ el ping tras {seg(t)}: {type(e).__name__}")
        print("  ", limpiar(e)[:900])
        pistas_mongo(str(e))
        return

    t = time.time()
    try:
        colecciones = db.list_collection_names()
        print(f"4) Colecciones ({len(colecciones)}) en {seg(t)}: {', '.join(sorted(colecciones)) or '(ninguna)'}")
        for col in ("categorias", "citas"):
            t = time.time()
            n = db[col].count_documents({})
            print(f"5) {col}: {n} documentos (consulta en {seg(t)})")
    except Exception as e:
        print(f"4/5) FALLÓ al consultar: {type(e).__name__}: {limpiar(e)[:500]}")
        return

    print("RESULTADO: este cluster responde bien.")


def probar_neon():
    print("\n=== Neon PostgreSQL (NEON_URI) ===")
    uri = os.getenv("NEON_URI")
    if not uri:
        print("No está definida en el .env -> se omite")
        return
    print("Host:", host_de(uri))
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 no está instalado en este entorno de Python")
        return
    t = time.time()
    try:
        conn = psycopg2.connect(uri, connect_timeout=TIMEOUT_S)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        print(f"Conexión y consulta OK en {seg(t)}  (si es la primera vez en un rato, Neon puede tardar unos segundos en despertar)")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"FALLÓ tras {seg(t)}: {type(e).__name__}")
        print("  ", limpiar(e)[:600])


def main():
    print("Python", sys.version.split()[0])
    cargar_env()
    probar_mongo("A", "MONGO_URI")
    probar_mongo("B", "MONGO_URI_B")
    probar_neon()
    print("\nCopia esta salida completa y pásamela (no contiene usuario ni contraseña).")


if __name__ == "__main__":
    main()
