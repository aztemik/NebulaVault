from pathlib import Path
import math
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

import bcrypt
import requests
import firebase_admin
from firebase_admin import credentials, firestore, auth
from firebase_config import get_firebase_app, _get_api_key, _FIREBASE_AUTH_URL

# ─── Carga opcional de .env ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv no es obligatorio; exporta las vars manualmente


# ─── Utilidades de contraseña ────────────────────────────────────────────────

def _encriptar_password(password: str) -> str:
    """
    Genera un hash bcrypt de la contraseña en texto plano.

    Retorna:
        Hash como string UTF-8 (listo para guardar en Firestore).
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _verificar_password(password: str, hashed: str) -> bool:
    """
    Compara una contraseña en texto plano con su hash bcrypt almacenado.

    Retorna:
        True si coinciden, False en caso contrario.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ─── Mensajes de error legibles ──────────────────────────────────────────────

def _traducir_error_firebase(codigo: str) -> str:
    """Convierte códigos de error de Firebase en mensajes legibles en español."""
    tabla = {
        "EMAIL_NOT_FOUND":               "No existe una cuenta con ese correo.",
        "INVALID_PASSWORD":              "Contraseña incorrecta.",
        "USER_DISABLED":                 "Esta cuenta ha sido deshabilitada.",
        "TOO_MANY_ATTEMPTS_TRY_LATER":   "Demasiados intentos fallidos. Inténtalo más tarde.",
        "INVALID_EMAIL":                 "El formato del correo es inválido.",
        "WEAK_PASSWORD":                 "La contraseña debe tener al menos 6 caracteres.",
        "EMAIL_EXISTS":                  "El correo ya está registrado.",
        "INVALID_LOGIN_CREDENTIALS":     "Correo o contraseña incorrectos.",
    }
    for clave, mensaje in tabla.items():
        if clave in codigo:
            return mensaje
    return f"Error de autenticación: {codigo}"



# Versiones actuales de los documentos legales (actualizar al cambiar los textos)
LEGAL_VERSIONS = {
    "terms_version":          "2026-02-06",
    "privacy_version":        "2026-02-06",
    "confidentiality_version":"2026-02-06",
}

class AuthFire:

    # ═══════════════════════════════════════════════════════════════════════════
    #  LÓGICA FIREBASE AUTH  (REST API + Admin SDK)
    # ═══════════════════════════════════════════════════════════════════════════

    def login_con_email(email: str, password: str) -> dict:
        """
        Autentica un usuario con email y contraseña mediante la REST API de Firebase.

        Flujo:
            1. Obtiene el hash bcrypt almacenado en Firestore para el email.
            2. Verifica la contraseña en texto plano contra ese hash.
            3. Si coincide, llama a la REST API de Firebase para obtener el idToken.
            4. Actualiza el campo 'email_verificado' en Firestore con el estado real.

        Retorna:
            dict con 'idToken', 'localId', 'email', 'displayName',
            'emailVerified' y 'email_verificado' (bool).

        Lanza:
            RuntimeError con mensaje legible si las credenciales son incorrectas
            o el usuario no existe en Firestore.
        """
        app = get_firebase_app()
        db  = firestore.client(app=app)

        # ── 1. Obtener hash desde Firestore ──────────────────────────────────
        docs = (
            db.collection("usuarios")
              .where("email", "==", email)
              .limit(1)
              .get()
        )
        if not docs:
            raise RuntimeError("No existe una cuenta con ese correo.")

        perfil        = docs[0].to_dict()
        uid_firestore = docs[0].id
        hash_guardado = perfil.get("password", "")

        # ── 2. Verificar contraseña contra hash bcrypt ───────────────────────
        if not hash_guardado or not _verificar_password(password, hash_guardado):
            raise RuntimeError("Correo o contraseña incorrectos.")

        # ── 3. Autenticar con Firebase REST API ──────────────────────────────
        url = _FIREBASE_AUTH_URL.format(
            endpoint="signInWithPassword",
            api_key=_get_api_key(),
        )
        payload = {
            "email":             email,
            "password":          password,
            "returnSecureToken": True,
        }
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()

        if resp.status_code != 200:
            codigo = data.get("error", {}).get("message", "ERROR_DESCONOCIDO")
            raise RuntimeError(_traducir_error_firebase(codigo))

        # ── 4. Sincronizar estado de verificación en Firestore ───────────────
        email_verificado = data.get("emailVerified", False)
        db.collection("usuarios").document(uid_firestore).update({
            "email_verificado": email_verificado,
        })

        return {
            **data,
            "email_verificado": email_verificado,
        }


    def registrar_usuario(nombre: str, email: str, password: str) -> dict:
        """
        Crea un usuario en Firebase Auth y guarda su perfil en Firestore.

        La contraseña se almacena como hash bcrypt; NUNCA en texto plano.
        El campo 'email_verificado' se inicializa en False hasta que el usuario
        confirme su correo.

        Retorna:
            dict con 'uid', 'email' y 'displayName'.

        Lanza:
            RuntimeError si el correo ya existe o Firebase rechaza la creación.
        """
        app = get_firebase_app()

        try:
            usuario = auth.create_user(
                email=email,
                password=password,
                display_name=nombre,
                email_verified=False,
                app=app,
            )
        except auth.EmailAlreadyExistsError:
            raise RuntimeError("El correo ya está registrado. Inicia sesión.")
        except Exception as exc:
            raise RuntimeError(f"Error al crear la cuenta: {exc}") from exc

        # ── Encriptar contraseña antes de guardar ────────────────────────────
        password_hash = _encriptar_password(password)

        # ── Guardar perfil en Firestore ──────────────────────────────────────
        db = firestore.client(app=app)
        db.collection("usuarios").document(usuario.uid).set({
            "nombre":            nombre,
            "email":             email,
            "password":          password_hash,   # hash bcrypt, nunca texto plano
            "uid":               usuario.uid,
            "creado_en":         firestore.SERVER_TIMESTAMP,
            "activo":            True,
            "rol":               "usuario",
            "modo":              "cloud",
            "email_verificado":  False,            # se actualiza al verificar
        })

        return {
            "uid":         usuario.uid,
            "email":       usuario.email,
            "displayName": usuario.display_name,
        }


    def enviar_correo_verificacion(id_token: str) -> None:
        """
        Envía un correo de verificación al usuario actualmente autenticado.

        Parámetros:
            id_token: Token de ID obtenido tras el login (campo 'idToken' del dict
                      devuelto por login_con_email).

        Nota:
            Firebase gestiona el envío del correo; no se necesita SMTP propio.
            Una vez que el usuario haga clic en el enlace, el campo 'emailVerified'
            se actualizará en Firebase Auth. El campo 'email_verificado' en Firestore
            se sincroniza automáticamente en el próximo login_con_email.

        Lanza:
            RuntimeError si Firebase no puede enviar el correo.
        """
        url = _FIREBASE_AUTH_URL.format(
            endpoint="sendOobCode",
            api_key=_get_api_key(),
        )
        payload = {
            "requestType": "VERIFY_EMAIL",
            "idToken":     id_token,
        }
        resp = requests.post(url, json=payload, timeout=10)

        if resp.status_code != 200:
            codigo = resp.json().get("error", {}).get("message", "ERROR_DESCONOCIDO")
            raise RuntimeError(f"No se pudo enviar el correo de verificación: {codigo}")


    def sincronizar_verificacion(uid: str) -> bool:
        """
        Consulta Firebase Auth y actualiza el campo 'email_verificado' en Firestore.

        Útil para refrescar el estado sin necesidad de un nuevo login.

        Parámetros:
            uid: UID del usuario (campo 'localId' del dict de login).

        Retorna:
            True si el correo está verificado, False si no.

        Lanza:
            RuntimeError si el usuario no existe en Firebase Auth.
        """
        app = get_firebase_app()

        try:
            usuario = auth.get_user(uid, app=app)
        except auth.UserNotFoundError:
            raise RuntimeError(f"Usuario con UID '{uid}' no encontrado en Firebase Auth.")

        verificado = usuario.email_verified

        db = firestore.client(app=app)
        db.collection("usuarios").document(uid).update({
            "email_verificado": verificado,
        })

        return verificado
    

    @staticmethod
    def verificar_aceptacion_terminos(uid: str) -> bool:
        """
        Consulta Firestore para saber si el usuario ya aceptó
        la versión vigente de todos los documentos legales.
 
        Ruta: users/{uid}/legal/acceptance
 
        Devuelve True solo si:
          - El documento existe
          - accepted == True
          - Las versiones guardadas coinciden con las vigentes
            (así se fuerza re-aceptación si los textos cambian)
        """
        db  = firestore.client()
        ref = (db.collection("users")
                 .document(uid)
                 .collection("legal")
                 .document("acceptance"))
        snap = ref.get()
        if not snap.exists:
            return False
 
        datos = snap.to_dict()
        if not datos.get("accepted", False):
            return False
 
        # Verificar que las versiones guardadas siguen siendo vigentes
        for campo, version_vigente in LEGAL_VERSIONS.items():
            if datos.get(campo) != version_vigente:
                return False   # textos actualizados → requiere re-aceptación
 
        return True
 
    @staticmethod
    def guardar_aceptacion_terminos(uid: str) -> None:
        """
        Persiste en Firestore que el usuario aceptó todos los documentos
        legales en su versión actual.
 
        Ruta: users/{uid}/legal/acceptance
 
        Campos guardados:
          uid                    — identificador del usuario
          accepted               — True
          accepted_at            — timestamp del servidor
          terms_version          — versión de Términos de Uso aceptada
          privacy_version        — versión del Aviso de Privacidad aceptada
          confidentiality_version— versión del Acuerdo de Confidencialidad aceptada
        """
        db  = firestore.client()
        ref = (db.collection("users")
                 .document(uid)
                 .collection("legal")
                 .document("acceptance"))
        ref.set({
            "uid":                     uid,
            "accepted":                True,
            "accepted_at":             firestore.SERVER_TIMESTAMP,
            **LEGAL_VERSIONS,
        })
 