import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials

load_dotenv()

# ═════════════════════════════════════════════════════════════════════════════
#  FIREBASE — Conexión y constantes
# ═════════════════════════════════════════════════════════════════════════════

# URL base de la API REST de Firebase Authentication
_FIREBASE_AUTH_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts"
    ":{endpoint}?key={api_key}"
)


def get_firebase_app() -> firebase_admin.App:
    """
    Inicializa y devuelve la app de Firebase Admin si aún no está activa.
    Lee la ruta del JSON de credenciales desde la variable de entorno
    FIREBASE_CREDENTIALS.
    """
    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS")
        if not cred_path:
            raise ValueError(
                "No se encontró FIREBASE_CREDENTIALS en el archivo .env"
            )
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firebase_admin.get_app()


def _get_api_key() -> str:
    """
    Devuelve la Web API Key de Firebase (necesaria para la REST API de Auth).
    Debe estar en la variable de entorno FIREBASE_API_KEY.
    """
    api_key = os.getenv("FIREBASE_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró FIREBASE_API_KEY en el archivo .env.\n"
            "Agrégala desde Configuración del proyecto → Aplicaciones web en Firebase Console."
        )
    return api_key