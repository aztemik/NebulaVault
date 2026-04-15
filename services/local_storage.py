"""
services/local_storage.py
════════════════════════════════════════════════════════════════════════════
NébulaVault — Almacenamiento local SQLite para modo On-Premises.

No requiere dependencias externas: usa sqlite3 de la biblioteca estándar.
El archivo de base de datos se crea en el directorio elegido por el usuario
con el nombre `nebulavault.db`.

Esquema
───────
bovedas
    id                              TEXT  PRIMARY KEY  (UUID v4)
    nombre                          TEXT  NOT NULL
    password_hash                   TEXT  NOT NULL     (bcrypt)
    pregunta_seguridad              TEXT  NOT NULL
    password_cifrada_con_respuesta  TEXT  NOT NULL     (Fernet cifrado con respuesta)
    salt                            TEXT  NOT NULL     (16 bytes aleatorios en hex)
    intentos_password               INTEGER DEFAULT 0
    boveda_bloqueada                INTEGER DEFAULT 0  (0/1)
    boveda_inaccesible              INTEGER DEFAULT 0  (0/1)
    creado_en                       TEXT  NOT NULL     (ISO-8601)

entradas
    id          TEXT  PRIMARY KEY  (UUID v4)
    boveda_id   TEXT  NOT NULL     (FK → bovedas.id)
    correo      TEXT  NOT NULL
    password    TEXT  NOT NULL DEFAULT ''  (Fernet cifrado)
    nota        TEXT  NOT NULL DEFAULT ''
    creado_en   TEXT  NOT NULL     (ISO-8601)

Helpers de cifrado locales
──────────────────────────
A diferencia del modo cloud (que usa el UID de Firebase como sal), aquí
cada bóveda genera su propio salt aleatorio de 16 bytes al crearse.
Las funciones `get_fernet_local`, `cifrar_password_con_respuesta_local` y
`descifrar_password_con_respuesta_local` encapsulan PBKDF2 + Fernet usando
ese salt en lugar del UID.
════════════════════════════════════════════════════════════════════════════
"""

import base64
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


DB_FILENAME = "nebulavault.db"


# ══════════════════════════════════════════════════════════════════════════
#  CONEXIÓN Y ESQUEMA
# ══════════════════════════════════════════════════════════════════════════

def _conn(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db(directory: str) -> str:
    """
    Inicializa (o abre) la base de datos SQLite en `directory`.
    Crea las tablas si no existen.

    Retorna:
        Ruta completa al archivo nebulavault.db.

    Lanza:
        OSError / PermissionError si el directorio no es accesible.
    """
    db_path = str(Path(directory) / DB_FILENAME)
    with _conn(db_path) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS bovedas (
                id                              TEXT PRIMARY KEY,
                nombre                          TEXT NOT NULL,
                password_hash                   TEXT NOT NULL,
                pregunta_seguridad              TEXT NOT NULL,
                password_cifrada_con_respuesta  TEXT NOT NULL,
                salt                            TEXT NOT NULL,
                intentos_password               INTEGER NOT NULL DEFAULT 0,
                boveda_bloqueada                INTEGER NOT NULL DEFAULT 0,
                boveda_inaccesible              INTEGER NOT NULL DEFAULT 0,
                creado_en                       TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS entradas (
                id          TEXT PRIMARY KEY,
                boveda_id   TEXT NOT NULL,
                correo      TEXT NOT NULL,
                password    TEXT NOT NULL DEFAULT '',
                nota        TEXT NOT NULL DEFAULT '',
                creado_en   TEXT NOT NULL,
                FOREIGN KEY (boveda_id) REFERENCES bovedas(id)
            );
        """)
    return db_path


def _row_boveda(row: sqlite3.Row) -> dict:
    """Convierte una fila de bovedas en dict con booleanos correctos."""
    d = dict(row)
    d["boveda_bloqueada"]   = bool(d.get("boveda_bloqueada",   0))
    d["boveda_inaccesible"] = bool(d.get("boveda_inaccesible", 0))
    return d


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS DE CIFRADO LOCALES  (PBKDF2 con salt por bóveda)
# ══════════════════════════════════════════════════════════════════════════

def _fernet_desde_material(material: bytes, salt_bytes: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=100_000,
    )
    return Fernet(base64.urlsafe_b64encode(kdf.derive(material)))


def get_fernet_local(password: str, salt_bytes: bytes) -> Fernet:
    """
    Deriva la clave Fernet para una bóveda local usando su salt exclusivo.

    Parámetros:
        password   — contraseña de la bóveda (texto plano).
        salt_bytes — 16 bytes aleatorios almacenados en la bóveda.

    Retorna:
        Instancia Fernet lista para cifrar/descifrar entradas.
    """
    return _fernet_desde_material(password.encode("utf-8"), salt_bytes)


def cifrar_password_con_respuesta_local(
    password: str, respuesta: str, salt_bytes: bytes
) -> str:
    """
    Cifra la contraseña de la bóveda usando la respuesta de seguridad
    y el salt de la bóveda como material de derivación.

    El token resultante permite recuperar la contraseña si el usuario
    responde correctamente tras agotar los intentos.

    Lanza:
        ValueError si password o respuesta están vacíos.
    """
    if not password or not respuesta.strip():
        raise ValueError("Password y respuesta son obligatorios.")
    material = respuesta.lower().strip().encode("utf-8")
    fernet   = _fernet_desde_material(material, salt_bytes)
    return fernet.encrypt(password.encode("utf-8")).decode("utf-8")


def descifrar_password_con_respuesta_local(
    token: str, respuesta: str, salt_bytes: bytes
) -> str:
    """
    Descifra la contraseña de la bóveda usando la respuesta de seguridad.

    Retorna:
        Contraseña en texto plano si la respuesta es correcta.

    Lanza:
        ValueError si la respuesta es incorrecta o el token está corrupto.
    """
    if not token:
        raise ValueError("No hay token almacenado.")
    material = respuesta.lower().strip().encode("utf-8")
    fernet   = _fernet_desde_material(material, salt_bytes)
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Respuesta de seguridad incorrecta.") from exc


# ══════════════════════════════════════════════════════════════════════════
#  BÓVEDAS
# ══════════════════════════════════════════════════════════════════════════

def cargar_bovedas(db_path: str) -> list[dict]:
    """
    Devuelve todas las bóvedas ordenadas por fecha de creación.

    Cada elemento incluye todos los campos de la tabla, con
    `boveda_bloqueada` y `boveda_inaccesible` como bool Python.
    """
    with _conn(db_path) as con:
        rows = con.execute(
            "SELECT * FROM bovedas ORDER BY creado_en"
        ).fetchall()
    return [_row_boveda(r) for r in rows]


def crear_boveda(
    db_path: str,
    nombre: str,
    password_hash: str,
    pregunta_seguridad: str,
    password_cifrada_con_respuesta: str,
    salt: str,
) -> dict:
    """
    Crea una nueva bóveda en la base de datos local.

    Parámetros:
        db_path                        — ruta al archivo .db.
        nombre                         — nombre legible (no vacío).
        password_hash                  — hash bcrypt de la contraseña.
        pregunta_seguridad             — pregunta de recuperación.
        password_cifrada_con_respuesta — contraseña cifrada con la respuesta.
        salt                           — 16 bytes en hex (32 chars).

    Retorna:
        dict con todos los campos de la bóveda recién creada.

    Lanza:
        ValueError si nombre está vacío.
    """
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la bóveda no puede estar vacío.")

    boveda_id = str(uuid.uuid4())
    creado_en = datetime.now().isoformat()

    datos: dict = {
        "id":                            boveda_id,
        "nombre":                        nombre,
        "password_hash":                 password_hash,
        "pregunta_seguridad":            pregunta_seguridad,
        "password_cifrada_con_respuesta": password_cifrada_con_respuesta,
        "salt":                          salt,
        "intentos_password":             0,
        "boveda_bloqueada":              False,
        "boveda_inaccesible":            False,
        "creado_en":                     creado_en,
    }

    with _conn(db_path) as con:
        con.execute(
            """
            INSERT INTO bovedas
                (id, nombre, password_hash, pregunta_seguridad,
                 password_cifrada_con_respuesta, salt,
                 intentos_password, boveda_bloqueada, boveda_inaccesible,
                 creado_en)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?)
            """,
            (boveda_id, nombre, password_hash, pregunta_seguridad,
             password_cifrada_con_respuesta, salt, creado_en),
        )
    return datos


def actualizar_intentos_boveda(
    db_path: str,
    boveda_id: str,
    intentos: int,
    bloqueada: bool = False,
) -> None:
    """Actualiza contador de intentos fallidos y estado de bloqueo temporal."""
    with _conn(db_path) as con:
        con.execute(
            "UPDATE bovedas SET intentos_password=?, boveda_bloqueada=? WHERE id=?",
            (intentos, int(bloqueada), boveda_id),
        )


def bloquear_boveda_permanente(db_path: str, boveda_id: str) -> None:
    """Marca la bóveda como permanentemente inaccesible."""
    with _conn(db_path) as con:
        con.execute(
            "UPDATE bovedas SET boveda_inaccesible=1 WHERE id=?",
            (boveda_id,),
        )


def resetear_bloqueo_boveda(db_path: str, boveda_id: str) -> None:
    """Restablece contadores y desbloquea la bóveda tras respuesta correcta."""
    with _conn(db_path) as con:
        con.execute(
            "UPDATE bovedas SET intentos_password=0, boveda_bloqueada=0 WHERE id=?",
            (boveda_id,),
        )


def eliminar_boveda(db_path: str, boveda_id: str) -> None:
    """
    Elimina la bóveda y todas sus entradas.
    Las entradas se borran primero para respetar la FK.
    """
    with _conn(db_path) as con:
        con.execute("DELETE FROM entradas WHERE boveda_id=?", (boveda_id,))
        con.execute("DELETE FROM bovedas  WHERE id=?",        (boveda_id,))


# ══════════════════════════════════════════════════════════════════════════
#  ENTRADAS
# ══════════════════════════════════════════════════════════════════════════

def cargar_entradas(db_path: str, boveda_id: str) -> list[dict]:
    """Devuelve todas las entradas de una bóveda, ordenadas por fecha."""
    with _conn(db_path) as con:
        rows = con.execute(
            "SELECT * FROM entradas WHERE boveda_id=? ORDER BY creado_en",
            (boveda_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def crear_entrada(
    db_path: str,
    boveda_id: str,
    correo: str,
    password_cifrada: str,
    nota: str,
) -> dict:
    """
    Crea una nueva entrada en la bóveda indicada.

    Parámetros:
        db_path          — ruta al archivo .db.
        boveda_id        — ID de la bóveda destino.
        correo           — correo o usuario (no vacío).
        password_cifrada — contraseña ya cifrada con Fernet.
        nota             — texto libre, puede estar vacío.

    Retorna:
        dict con todos los campos de la entrada, incluyendo 'id'.

    Lanza:
        ValueError si correo está vacío.
    """
    correo = correo.strip()
    if not correo:
        raise ValueError("El campo correo/usuario es obligatorio.")

    entrada_id = str(uuid.uuid4())
    creado_en  = datetime.now().isoformat()

    datos: dict = {
        "id":        entrada_id,
        "boveda_id": boveda_id,
        "correo":    correo,
        "password":  password_cifrada,
        "nota":      nota.strip(),
        "creado_en": creado_en,
    }

    with _conn(db_path) as con:
        con.execute(
            """
            INSERT INTO entradas (id, boveda_id, correo, password, nota, creado_en)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entrada_id, boveda_id, correo,
             password_cifrada, nota.strip(), creado_en),
        )
    return datos


def actualizar_entrada(
    db_path: str,
    boveda_id: str,
    entrada_id: str,
    correo: str,
    password_cifrada: str,
    nota: str,
) -> dict:
    """
    Actualiza correo, contraseña y nota de una entrada existente.

    Lanza:
        ValueError si correo está vacío.
    """
    correo = correo.strip()
    if not correo:
        raise ValueError("El campo correo/usuario es obligatorio.")

    with _conn(db_path) as con:
        con.execute(
            """
            UPDATE entradas
               SET correo=?, password=?, nota=?
             WHERE id=? AND boveda_id=?
            """,
            (correo, password_cifrada, nota.strip(), entrada_id, boveda_id),
        )

    return {
        "id":        entrada_id,
        "boveda_id": boveda_id,
        "correo":    correo,
        "password":  password_cifrada,
        "nota":      nota.strip(),
    }


def eliminar_entrada(db_path: str, boveda_id: str, entrada_id: str) -> None:
    """Elimina permanentemente una entrada."""
    with _conn(db_path) as con:
        con.execute(
            "DELETE FROM entradas WHERE id=? AND boveda_id=?",
            (entrada_id, boveda_id),
        )


def contar_entradas(db_path: str, boveda_id: str) -> int:
    """Devuelve el número de entradas que tiene una bóveda."""
    with _conn(db_path) as con:
        row = con.execute(
            "SELECT COUNT(*) FROM entradas WHERE boveda_id=?",
            (boveda_id,),
        ).fetchone()
    return row[0] if row else 0
