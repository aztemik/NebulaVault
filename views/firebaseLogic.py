from pathlib import Path
import datetime
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



# ─── Seguridad de acceso ─────────────────────────────────────────────────────

MAX_INTENTOS_TEMP   = 2   # a partir del 2° fallo → bloqueo temporal
MAX_INTENTOS_PERM   = 5   # al 5° fallo → bloqueo permanente
DURACION_BLOQUEO_S  = 60  # segundos de bloqueo temporal


def _enviar_correo_bloqueo_cuenta(email: str) -> None:
    """
    Envía al usuario una notificación de bloqueo de cuenta con instrucciones
    para contactar a soporte.  Usa SMTP con las variables de entorno:

        SMTP_USER     — correo del remitente  (ej: tucuenta@gmail.com)
        SMTP_PASSWORD — app-password de 16 caracteres generada en Google
        SMTP_HOST     — servidor SMTP  (default: smtp.gmail.com)
        SMTP_PORT     — puerto TLS     (default: 587)
        SOPORTE_EMAIL — correo de soporte que aparece en el mensaje

    Si SMTP_USER o SMTP_PASSWORD no están definidos el envío se omite
    silenciosamente; el bloqueo ya quedó persistido en Firestore.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_user     = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_host     = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port     = int(os.getenv("SMTP_PORT", "587"))
    soporte_email = os.getenv("SOPORTE_EMAIL", "soporte@nebulavault.com").strip()

    if not smtp_user or not smtp_password:
        return  # SMTP no configurado; omitir envío sin error

    asunto = "NébulaVault — Cuenta bloqueada por seguridad"

    cuerpo = (
        f"Hola,\n\n"
        f"Hemos detectado {MAX_INTENTOS_PERM} intentos fallidos consecutivos de inicio "
        f"de sesión en la cuenta de NébulaVault asociada a este correo.\n\n"
        f"Por seguridad, tu cuenta ha sido BLOQUEADA.\n\n"
        f"Para recuperar el acceso comunícate con nuestro equipo de soporte:\n\n"
        f"    {soporte_email}\n\n"
        f"Incluye en tu mensaje:\n"
        f"  • Tu correo registrado: {email}\n"
        f"  • El asunto: «Desbloqueo de cuenta NébulaVault»\n\n"
        f"Si no fuiste tú quien intentó iniciar sesión, notifícanos de inmediato "
        f"para que podamos proteger tu información.\n\n"
        f"— Equipo de Seguridad NébulaVault\n\n"
        f"(Mensaje automático. No respondas a este correo.)"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = f"NébulaVault Security <{smtp_user}>"
    msg["To"]      = email
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, email, msg.as_string())
    except Exception:
        pass  # best-effort; el bloqueo ya quedó registrado en Firestore


def _registrar_evento_seguridad(
    uid: str,
    db,
    tipo: str,
    email: str,
    detalle: str = "",
) -> None:
    """
    Persiste un evento de seguridad en usuarios/{uid}/log_seguridad.

    tipos posibles:
        "intento_fallido"   — contraseña incorrecta
        "bloqueo_temporal"  — bloqueo de 60 s aplicado
        "bloqueo_permanente"— cuenta deshabilitada definitivamente
        "login_exitoso"     — acceso correcto (resetea contador)
    """
    try:
        db.collection("usuarios").document(uid).collection("log_seguridad").add({
            "tipo":      tipo,
            "email":     email,
            "detalle":   detalle,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
    except Exception:
        pass  # best-effort; no bloquear el flujo de autenticación


# Versiones actuales de los documentos legales (actualizar al cambiar los textos)
LEGAL_VERSIONS = {
    "terms_version":          "2026-02-06",
    "privacy_version":        "2026-02-06",
    "confidentiality_version":"2026-02-06",
}

class VerificacionRequeridaError(RuntimeError):
    """
    Se lanza cuando el usuario intenta hacer login con un correo no verificado.
    Lleva el idToken y el uid para que la UI pueda:
      · reenviar el correo de verificación sin pedir la contraseña de nuevo.
      · consultar Firebase en cualquier momento para saber si ya fue verificado.
    """
    def __init__(self, mensaje: str, id_token: str, uid: str) -> None:
        super().__init__(mensaje)
        self.id_token = id_token
        self.uid      = uid


class AuthFire:

    # ═══════════════════════════════════════════════════════════════════════════
    #  LÓGICA FIREBASE AUTH  (REST API + Admin SDK)
    # ═══════════════════════════════════════════════════════════════════════════

    def login_con_email(email: str, password: str) -> dict:
        """
        Autentica un usuario con email y contraseña mediante la REST API de Firebase.

        Flujo:
            1. Obtiene el perfil almacenado en Firestore para el email.
            2. Verifica bloqueo permanente (5 intentos fallidos acumulados).
            3. Verifica bloqueo temporal (60 s activo desde el 2° intento fallido).
            4. Comprueba la contraseña contra el hash bcrypt guardado.
               · Correcta → resetea contadores y llama a Firebase REST API.
               · Incorrecta → incrementa contador y aplica política de bloqueo.
            5. Llama a la REST API de Firebase para obtener el idToken.
            6. Actualiza el campo 'email_verificado' en Firestore.

        Retorna:
            dict con 'idToken', 'localId', 'email', 'displayName',
            'emailVerified' y 'email_verificado' (bool).

        Lanza:
            RuntimeError con mensaje legible en cualquier caso de fallo.
        """
        app = get_firebase_app()
        db  = firestore.client(app=app)

        # ── 1. Obtener perfil desde Firestore ────────────────────────────────
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

        # ── 2. Bloqueo permanente ────────────────────────────────────────────
        if perfil.get("cuenta_bloqueada", False):
            raise RuntimeError(
                "⛔  Tu cuenta ha sido bloqueada por múltiples intentos fallidos.\n"
                "Contacta a soporte para recuperar el acceso."
            )

        # ── 3. Bloqueo temporal ──────────────────────────────────────────────
        bloqueado_hasta = perfil.get("bloqueado_temp_hasta")
        if bloqueado_hasta is not None:
            ahora = datetime.datetime.now(datetime.timezone.utc)
            # Firestore devuelve DatetimeWithNanoseconds; asegurar tzinfo UTC
            if hasattr(bloqueado_hasta, "tzinfo") and bloqueado_hasta.tzinfo is None:
                bloqueado_hasta = bloqueado_hasta.replace(tzinfo=datetime.timezone.utc)
            if ahora < bloqueado_hasta:
                segundos_rest = int((bloqueado_hasta - ahora).total_seconds()) + 1
                raise RuntimeError(
                    f"🔒  Demasiados intentos fallidos.\n"
                    f"Espera {segundos_rest} segundo(s) antes de intentarlo de nuevo."
                )

        # ── 4. Verificar contraseña contra hash bcrypt ───────────────────────
        if not hash_guardado or not _verificar_password(password, hash_guardado):
            intentos = perfil.get("intentos_fallidos_login", 0) + 1
            update_data: dict = {
                "intentos_fallidos_login": intentos,
                "ultimo_intento_fallido":  firestore.SERVER_TIMESTAMP,
            }

            if intentos >= MAX_INTENTOS_PERM:
                # ── Bloqueo PERMANENTE ───────────────────────────────────────
                update_data["cuenta_bloqueada"] = True
                db.collection("usuarios").document(uid_firestore).update(update_data)
                _registrar_evento_seguridad(
                    uid_firestore, db, "bloqueo_permanente", email,
                    f"Cuenta bloqueada tras {intentos} intentos fallidos.",
                )
                _enviar_correo_bloqueo_cuenta(email)
                raise RuntimeError(
                    "⛔  Tu cuenta ha sido bloqueada definitivamente por múltiples "
                    "intentos fallidos de inicio de sesión.\n"
                    "Contacta a soporte para recuperar el acceso."
                )

            elif intentos >= MAX_INTENTOS_TEMP:
                # ── Bloqueo TEMPORAL de 60 segundos ─────────────────────────
                hasta = (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(seconds=DURACION_BLOQUEO_S)
                )
                update_data["bloqueado_temp_hasta"] = hasta
                db.collection("usuarios").document(uid_firestore).update(update_data)
                _registrar_evento_seguridad(
                    uid_firestore, db, "bloqueo_temporal", email,
                    f"Bloqueo temporal ({DURACION_BLOQUEO_S} s) tras {intentos} intentos fallidos.",
                )
                raise RuntimeError(
                    f"🔒  Demasiados intentos fallidos.\n"
                    f"Espera {DURACION_BLOQUEO_S} segundos antes de intentarlo de nuevo."
                )

            else:
                # ── 1er intento fallido: solo registrar ──────────────────────
                db.collection("usuarios").document(uid_firestore).update(update_data)
                _registrar_evento_seguridad(
                    uid_firestore, db, "intento_fallido", email,
                    f"Intento {intentos} fallido. "
                    f"Quedan {MAX_INTENTOS_TEMP - intentos} intento(s) antes del bloqueo temporal.",
                )
                raise RuntimeError("Correo o contraseña incorrectos.")

        # ── 5. Contraseña correcta: resetear contadores de bloqueo ──────────
        db.collection("usuarios").document(uid_firestore).update({
            "intentos_fallidos_login": 0,
            "bloqueado_temp_hasta":    None,
        })

        # ── 6. Autenticar con Firebase REST API ──────────────────────────────
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

        # ── 7. Sincronizar verificación de correo en Firestore ───────────────
        # signInWithPassword puede devolver emailVerified desactualizado por
        # latencia de propagación interna de Firebase. Si devuelve False,
        # consultamos accounts:lookup que siempre lee el estado en vivo.
        email_verificado = data.get("emailVerified", False)

        if not email_verificado:
            try:
                lookup_url = _FIREBASE_AUTH_URL.format(
                    endpoint="lookup",
                    api_key=_get_api_key(),
                )
                lr = requests.post(
                    lookup_url,
                    json={"idToken": data["idToken"]},
                    timeout=10,
                )
                if lr.status_code == 200:
                    users_lookup = lr.json().get("users", [])
                    if users_lookup:
                        email_verificado = users_lookup[0].get("emailVerified", False)
            except Exception:
                pass  # best-effort; si falla, se usa el valor de signInWithPassword

        db.collection("usuarios").document(uid_firestore).update({
            "email_verificado": email_verificado,
        })

        if not email_verificado:
            raise VerificacionRequeridaError(
                "Debes verificar tu correo electrónico antes de iniciar sesión.\n"
                "Revisa tu bandeja de entrada y haz clic en el enlace.",
                id_token=data.get("idToken", ""),
                uid=uid_firestore,
            )

        # ── 8. Login completado ───────────────────────────────────────────────
        _registrar_evento_seguridad(uid_firestore, db, "login_exitoso", email)

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


    @staticmethod
    def comprobar_verificacion_email(id_token: str, uid: str) -> bool:
        """
        Consulta Firebase Auth mediante accounts:lookup para obtener el estado
        ACTUAL de emailVerified, sin necesidad de una nueva autenticación.

        Este endpoint siempre devuelve los datos en vivo de Firebase Auth,
        por lo que refleja inmediatamente si el usuario hizo clic en el enlace
        de verificación, aunque el idToken haya sido emitido antes de verificar.

        Si el correo ya fue verificado, actualiza email_verificado = True en
        Firestore para que la base de datos quede sincronizada.

        Retorna:
            True  → correo verificado (Firestore actualizado).
            False → todavía sin verificar.

        Lanza:
            RuntimeError si la consulta a Firebase falla.
        """
        url = _FIREBASE_AUTH_URL.format(
            endpoint="lookup",
            api_key=_get_api_key(),
        )
        resp = requests.post(url, json={"idToken": id_token}, timeout=10)
        if resp.status_code != 200:
            codigo = resp.json().get("error", {}).get("message", "ERROR_DESCONOCIDO")
            raise RuntimeError(f"No se pudo consultar el estado de verificación: {codigo}")

        users = resp.json().get("users", [])
        if not users:
            raise RuntimeError("Usuario no encontrado en Firebase Auth.")

        verificado = users[0].get("emailVerified", False)

        if verificado:
            app = get_firebase_app()
            db  = firestore.client(app=app)
            db.collection("usuarios").document(uid).update({
                "email_verificado": True,
            })

        return verificado

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
 