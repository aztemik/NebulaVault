"""
services/crypto.py
════════════════════════════════════════════════════════════════════════════
NébulaVault — Capa de cifrado simétrico para contraseñas de bóveda.

Diseño de seguridad
───────────────────
• Cada bóveda tiene su propia clave de cifrado, derivada de:
      material  = contraseña de la bóveda  (ingresada por el usuario)
      sal       = uid[:16]                 (único por cuenta)
  → dos bóvedas con la misma contraseña en cuentas distintas producen
    claves distintas.

• La contraseña de la bóveda se almacena como hash bcrypt (nunca en
  texto plano). La clave Fernet se deriva en memoria solo mientras la
  bóveda está desbloqueada.

• Algoritmo de cifrado de entradas: AES-128-CBC + HMAC-SHA256 (Fernet).
• KDF: PBKDF2-HMAC-SHA256, 100 000 iteraciones.
════════════════════════════════════════════════════════════════════════════
"""

import base64

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# ══════════════════════════════════════════════════════════════════════════
#  HASH DE CONTRASEÑA DE BÓVEDA  (bcrypt — para verificación en Firestore)
# ══════════════════════════════════════════════════════════════════════════

def hashear_password_boveda(password: str) -> str:
    """
    Genera un hash bcrypt de la contraseña de la bóveda.

    El hash se almacena en Firestore para verificar que el usuario
    conoce la contraseña antes de derivar la clave y desbloquear.

    Retorna:
        Hash bcrypt como str UTF-8.

    Lanza:
        ValueError si password está vacío.
    """
    if not password:
        raise ValueError("La contraseña de la bóveda no puede estar vacía.")
    salt   = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verificar_password_boveda(password: str, hash_guardado: str) -> bool:
    """
    Compara la contraseña en texto plano con el hash bcrypt almacenado.

    Retorna:
        True si la contraseña es correcta, False en caso contrario.
    """
    if not password or not hash_guardado:
        return False
    return bcrypt.checkpw(password.encode("utf-8"),
                          hash_guardado.encode("utf-8"))


# ══════════════════════════════════════════════════════════════════════════
#  DERIVACIÓN DE CLAVE  (PBKDF2 — por bóveda)
# ══════════════════════════════════════════════════════════════════════════

def derivar_clave_boveda(password_boveda: str, uid: str) -> bytes:
    """
    Deriva una clave Fernet a partir de la contraseña de la bóveda y el
    uid del usuario.

    Parámetros:
        password_boveda — contraseña introducida por el usuario al crear /
                          desbloquear la bóveda.
        uid             — UID de Firebase del propietario (actúa como sal,
                          garantizando unicidad entre cuentas).

    Retorna:
        32 bytes codificados en base64-urlsafe, listos para construir Fernet.
    """
    material = password_boveda.encode("utf-8")
    sal      = (uid[:16] if len(uid) >= 16 else uid.ljust(16, "0")).encode()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=sal,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(material))


def get_fernet_boveda(password_boveda: str, uid: str) -> Fernet:
    """
    Construye y devuelve la instancia Fernet para una bóveda.

    Debe llamarse solo después de verificar la contraseña con
    `verificar_password_boveda`.
    """
    return Fernet(derivar_clave_boveda(password_boveda, uid))


# ══════════════════════════════════════════════════════════════════════════
#  CIFRADO DE ENTRADAS  (Fernet — operar sobre texto plano)
# ══════════════════════════════════════════════════════════════════════════

def cifrar(texto: str, fernet: Fernet) -> str:
    """
    Cifra texto plano con Fernet.

    Retorna:
        Token cifrado como str (base64-urlsafe). Listo para almacenar en
        Firestore.

    Lanza:
        ValueError si texto está vacío.
    """
    if not texto:
        raise ValueError("No se puede cifrar una cadena vacía.")
    return fernet.encrypt(texto.encode("utf-8")).decode("utf-8")


def descifrar(token: str, fernet: Fernet) -> str:
    """
    Descifra un token Fernet generado por `cifrar`.

    Retorna:
        Texto plano como str. Devuelve "" si token está vacío.

    Lanza:
        ValueError si el token fue alterado o la clave no coincide.
    """
    if not token:
        return ""
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "No se pudo descifrar. "
            "El token es inválido o la contraseña de bóveda es incorrecta."
        ) from exc
