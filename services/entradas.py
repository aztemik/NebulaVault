"""
services/entradas.py
════════════════════════════════════════════════════════════════════════════
NébulaVault — Lógica de negocio y acceso a Firestore para Entradas.

Ruta Firestore:  users/{uid}/bovedas/{boveda_id}/entradas/{entrada_id}

Campos de una entrada:
    correo      str       — correo electrónico o nombre de usuario
    password    str       — contraseña cifrada con Fernet (nunca texto plano)
    nota        str       — nota libre, puede estar vacía
    creado_en   Timestamp — fecha de creación (SERVER_TIMESTAMP)

IMPORTANTE: este módulo recibe y devuelve la contraseña ya cifrada.
La responsabilidad de cifrar/descifrar pertenece a la capa que llama
(services/crypto.py + la pantalla de UI).
════════════════════════════════════════════════════════════════════════════
"""

from firebase_config import get_firebase_app
from firebase_admin import firestore


# ── Helper interno ─────────────────────────────────────────────────────────

def _col_entradas(uid: str, boveda_id: str):
    """Referencia a la subcolección de entradas de una bóveda."""
    app = get_firebase_app()
    db  = firestore.client(app=app)
    return (
        db.collection("users")
          .document(uid)
          .collection("bovedas")
          .document(boveda_id)
          .collection("entradas")
    )


# ── API pública ────────────────────────────────────────────────────────────

def cargar_entradas(uid: str, boveda_id: str) -> list[dict]:
    """
    Devuelve todas las entradas de una bóveda.

    Cada elemento es un dict con al menos:
        id        str  — document ID de Firestore
        correo    str  — correo o usuario
        password  str  — contraseña cifrada (Fernet token)
        nota      str  — nota libre

    Lanza:
        Exception propagada desde Firebase si la consulta falla.
    """
    docs = _col_entradas(uid, boveda_id).get()
    return [{"id": d.id, **d.to_dict()} for d in docs]


def crear_entrada(uid: str, boveda_id: str,
                  correo: str, password_cifrada: str, nota: str) -> dict:
    """
    Crea una nueva entrada en la bóveda indicada.

    Parámetros:
        uid              — UID del usuario.
        boveda_id        — Document ID de la bóveda de destino.
        correo           — Correo o usuario (no vacío).
        password_cifrada — Contraseña ya cifrada con Fernet.
                           Pasar "" si el usuario no ingresó contraseña.
        nota             — Texto libre, puede estar vacío.

    Retorna:
        dict con todos los campos de la entrada recién creada, incluyendo 'id'.

    Lanza:
        ValueError si correo está vacío.
        Exception  propagada desde Firebase si la escritura falla.
    """
    correo = correo.strip()
    if not correo:
        raise ValueError("El campo correo/usuario es obligatorio.")

    datos = {
        "correo":    correo,
        "password":  password_cifrada,
        "nota":      nota.strip(),
        "creado_en": firestore.SERVER_TIMESTAMP,
    }
    ref = _col_entradas(uid, boveda_id).document()
    ref.set(datos)
    return {"id": ref.id, **datos}


def actualizar_entrada(uid: str, boveda_id: str, entrada_id: str,
                       correo: str, password_cifrada: str, nota: str) -> dict:
    """
    Actualiza los campos de una entrada existente.

    Solo modifica correo, password y nota; no toca 'creado_en'.

    Parámetros: igual que crear_entrada, más entrada_id.

    Retorna:
        dict con los campos actualizados (sin 'creado_en').

    Lanza:
        ValueError si correo está vacío.
        Exception  propagada desde Firebase si la escritura falla.
    """
    correo = correo.strip()
    if not correo:
        raise ValueError("El campo correo/usuario es obligatorio.")

    cambios = {
        "correo":   correo,
        "password": password_cifrada,
        "nota":     nota.strip(),
    }
    _col_entradas(uid, boveda_id).document(entrada_id).update(cambios)
    return {"id": entrada_id, **cambios}


def eliminar_entrada(uid: str, boveda_id: str, entrada_id: str) -> None:
    """
    Elimina permanentemente una entrada de Firestore.

    Lanza:
        Exception propagada desde Firebase si la operación falla.
    """
    _col_entradas(uid, boveda_id).document(entrada_id).delete()


def contar_entradas(uid: str, boveda_id: str) -> int:
    """
    Devuelve el número de entradas que tiene una bóveda.

    Usa COUNT aggregation si está disponible (firebase-admin ≥ 6.0);
    si no, hace un conteo por stream como fallback.

    Lanza:
        Exception propagada desde Firebase si la consulta falla.
    """
    col = _col_entradas(uid, boveda_id)
    try:
        resultado = col.count().get()
        return resultado[0][0].value
    except Exception:
        return sum(1 for _ in col.stream())
