import os
from pymongo import MongoClient
import psycopg2
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
NEON_URI = os.getenv("NEON_URI")

_mongo_client = None


def get_mongo_db():
    """Devuelve la instancia de la base de datos MongoDB configurada en MONGO_URI."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI)
    return _mongo_client.get_default_database()


def get_neon_conn():
    """Abre y devuelve una nueva conexión hacia Neon PostgreSQL."""
    return psycopg2.connect(NEON_URI)