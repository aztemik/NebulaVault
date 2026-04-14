"""
services/bovedas.py
════════════════════════════════════════════════════════════════════════════
NébulaVault — Lógica de negocio y acceso a Firestore para Bóvedas.

Ruta Firestore:  users/{uid}/bovedas/{boveda_id}

Campos de una bóveda:
    nombre          str       — nombre legible dado por el usuario
    password_hash   str       — hash bcrypt de la contraseña de la bóveda
                                (usada como seed de la clave de cifrado)
    creado_en       Timestamp — fecha de creación (SERVER_TIMESTAMP)

NOTA: la contraseña en texto plano NUNCA se almacena. Solo el hash bcrypt,
que sirve para verificar que el usuario conoce la contraseña antes de
derivar la clave Fernet y desbloquear las entradas.
════════════════════════════════════════════════════════════════════════════
"""

from firebase_config import get_firebase_app
from firebase_admin import firestore


# ── Helper interno ─────────────────────────────────────────────────────────

def _col_bovedas(uid: str):
    """Referencia a la colección de bóvedas del usuario."""
    app = get_firebase_app()
    db  = firestore.client(app=app)
    return db.collection("users").document(uid).collection("bovedas")


# ── API pública ────────────────────────────────────────────────────────────

def cargar_bovedas(uid: str) -> list[dict]:
    """
    Devuelve todas las bóvedas del usuario.

    Cada elemento incluye:
        id              str  — document ID de Firestore
        nombre          str  — nombre de la bóveda
        password_hash   str  — hash bcrypt (para verificación local)
        creado_en            — Timestamp de Firestore

    Lanza:
        Exception propagada desde Firebase si la consulta falla.
    """
    docs = _col_bovedas(uid).get()
    return [{"id": d.id, **d.to_dict()} for d in docs]


def crear_boveda(uid: str, nombre: str, password_hash: str) -> dict:
    """
    Crea una nueva bóveda en Firestore.

    Parámetros:
        uid           — UID del usuario autenticado.
        nombre        — Nombre de la bóveda (no vacío).
        password_hash — Hash bcrypt de la contraseña de la bóveda,
                        generado con services.crypto.hashear_password_boveda.

    Retorna:
        dict con 'id', 'nombre' y 'password_hash'.

    Lanza:
        ValueError  si nombre o password_hash están vacíos.
        Exception   propagada desde Firebase si la escritura falla.
    """
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la bóveda no puede estar vacío.")
    if not password_hash:
        raise ValueError("Se requiere el hash de la contraseña.")

    datos = {
        "nombre":        nombre,
        "password_hash": password_hash,
        "creado_en":     firestore.SERVER_TIMESTAMP,
    }
    ref = _col_bovedas(uid).document()
    ref.set(datos)
    return {"id": ref.id, "nombre": nombre, "password_hash": password_hash}


def eliminar_boveda(uid: str, boveda_id: str) -> None:
    """
    Elimina la bóveda y todas sus entradas de Firestore.

    Las entradas de la subcolección se borran antes del documento padre
    para evitar huérfanos en Firestore.

    Lanza:
        Exception propagada desde Firebase si alguna operación falla.
    """
    bov_ref = _col_bovedas(uid).document(boveda_id)

    for entrada in bov_ref.collection("entradas").get():
        entrada.reference.delete()

    bov_ref.delete()
