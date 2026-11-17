import os
import threading
import webbrowser
from pymongo import MongoClient
import psycopg2
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
NEON_URI = os.getenv("NEON_URI")

_mongo_client = None


def get_mongo_db():
    """Toma automáticamente la base de datos especificada en la MONGO_URI."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI)
    return _mongo_client.get_default_database()


def get_neon_conn():
    """Abre y devuelve una conexión hacia Neon PostgreSQL."""
    return psycopg2.connect(NEON_URI)


# ==========================================================
# MODO PRUEBA INDEPENDIENTE (al ejecutar: python database.py)
# ==========================================================
if __name__ == "__main__":
    from flask import Flask, jsonify

    test_app = Flask(__name__)

    @test_app.route("/")
    def test_conexiones():
        resultado = {
            "mongodb": {"conectado": False, "base": None, "colecciones": [], "detalle": ""},
            "neon_postgresql": {"conectado": False, "base": None, "usuario": None, "tablas_detectadas": 0, "detalle": ""}
        }

        try:
            db = get_mongo_db()
            db.command("ping")
            resultado["mongodb"]["conectado"] = True
            resultado["mongodb"]["base"] = db.name
            resultado["mongodb"]["colecciones"] = db.list_collection_names()
            resultado["mongodb"]["detalle"] = "Conexión exitosa con user1"
        except Exception as e:
            resultado["mongodb"]["detalle"] = str(e)

        try:
            conn = get_neon_conn()
            cur = conn.cursor()
            cur.execute("SELECT current_database(), current_user;")
            db_name, db_user = cur.fetchone()

            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public';
            """)
            total_tablas = cur.fetchone()[0]
            cur.close()
            conn.close()

            resultado["neon_postgresql"]["conectado"] = True
            resultado["neon_postgresql"]["base"] = db_name
            resultado["neon_postgresql"]["usuario"] = db_user
            resultado["neon_postgresql"]["tablas_detectadas"] = total_tablas
            resultado["neon_postgresql"]["detalle"] = "Conexión exitosa con usr1"
        except Exception as e:
            resultado["neon_postgresql"]["detalle"] = str(e)

        code = 200 if (resultado["mongodb"]["conectado"] and resultado["neon_postgresql"]["conectado"]) else 500
        return jsonify(resultado), code

    url = "http://127.0.0.1:5000/"
    print("\n" + "=" * 55)
    print(f" Prueba de conexiones lista. Abre esta URL:\n -> {url}")
    print("=" * 55 + "\n")

    # Abre automáticamente el navegador tras 1 segundo
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    test_app.run(host="127.0.0.1", port=5000, debug=False)