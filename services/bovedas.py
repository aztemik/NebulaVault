"""
services/bovedas.py
════════════════════════════════════════════════════════════════════════════
NébulaVault — Lógica de negocio y acceso a Firestore para Bóvedas.

Ruta Firestore:  users/{uid}/bovedas/{boveda_id}

Campos de una bóveda:
    nombre                       str       — nombre legible dado por el usuario
    password_hash                str       — hash bcrypt de la contraseña
    pregunta_seguridad           str       — pregunta de seguridad elegida
    password_cifrada_con_respuesta str     — contraseña cifrada con la respuesta
                                             (permite recuperar acceso tras bloqueo)
    intentos_password            int       — intentos fallidos acumulados
    boveda_bloqueada             bool      — True tras 3 intentos fallidos
    boveda_inaccesible           bool      — True si la respuesta fue incorrecta
    creado_en                    Timestamp — fecha de creación

NOTA: la contraseña en texto plano NUNCA se almacena directamente.
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


def crear_boveda(
    uid: str,
    nombre: str,
    password_hash: str,
    pregunta_seguridad: str,
    password_cifrada_con_respuesta: str,
) -> dict:
    """
    Crea una nueva bóveda en Firestore.

    Parámetros:
        uid                          — UID del usuario autenticado.
        nombre                       — Nombre de la bóveda (no vacío).
        password_hash                — Hash bcrypt de la contraseña.
        pregunta_seguridad           — Pregunta de seguridad seleccionada.
        password_cifrada_con_respuesta — Contraseña cifrada con la respuesta
                                         de seguridad (para recuperación).

    Retorna:
        dict con todos los campos iniciales de la bóveda.

    Lanza:
        ValueError  si algún campo obligatorio está vacío.
        Exception   propagada desde Firebase si la escritura falla.
    """
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la bóveda no puede estar vacío.")
    if not password_hash:
        raise ValueError("Se requiere el hash de la contraseña.")
    if not pregunta_seguridad or not password_cifrada_con_respuesta:
        raise ValueError("La pregunta de seguridad y su respuesta son obligatorias.")

    datos = {
        "nombre":                        nombre,
        "password_hash":                 password_hash,
        "pregunta_seguridad":            pregunta_seguridad,
        "password_cifrada_con_respuesta": password_cifrada_con_respuesta,
        "intentos_password":             0,
        "boveda_bloqueada":              False,
        "boveda_inaccesible":            False,
        "creado_en":                     firestore.SERVER_TIMESTAMP,
    }
    ref = _col_bovedas(uid).document()
    ref.set(datos)
    return {"id": ref.id, **datos}


def actualizar_intentos_boveda(
    uid: str,
    boveda_id: str,
    intentos: int,
    bloqueada: bool = False,
) -> None:
    """
    Actualiza el contador de intentos fallidos y el estado de bloqueo temporal.
    Llamar con intentos=0, bloqueada=False para resetear tras login correcto.
    """
    _col_bovedas(uid).document(boveda_id).update({
        "intentos_password": intentos,
        "boveda_bloqueada":  bloqueada,
    })


def bloquear_boveda_permanente(uid: str, boveda_id: str) -> None:
    """
    Marca la bóveda como permanentemente inaccesible tras respuesta
    de seguridad incorrecta.
    """
    _col_bovedas(uid).document(boveda_id).update({
        "boveda_inaccesible": True,
    })


def resetear_bloqueo_boveda(uid: str, boveda_id: str) -> None:
    """
    Restablece contadores y desbloquea la bóveda tras respuesta
    de seguridad correcta.
    """
    _col_bovedas(uid).document(boveda_id).update({
        "intentos_password": 0,
        "boveda_bloqueada":  False,
    })


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
