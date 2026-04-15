# Lista de Cotejo — Controles de Seguridad  
## NébulaVault · Gestión de Credenciales

> **Fecha de análisis:** 2026-04-14  
> **Versión analizada:** v1.0.0  
> **Modos cubiertos:** Cloud (Firebase) · On-Premises (SQLite local)  
> **Total de controles identificados:** 16 controles distintos  
> — 7 controles implementados exclusivamente en Cloud  
> — 1 control implementado exclusivamente en On-Premises  
> — 8 controles implementados en **ambos modos** (se contabilizan dos veces cada uno)

---

## Resumen de conteo

| # | Control | Cloud | On-Premises |
|---|---------|:-----:|:-----------:|
| 1 | Autenticación de usuario con email y contraseña | ✅ | — |
| 2 | Verificación de correo electrónico obligatoria | ✅ | — |
| 3 | Hash de contraseñas de usuario (login) con bcrypt | ✅ | — |
| 4 | Bloqueo temporal de cuenta por intentos fallidos | ✅ | — |
| 5 | Bloqueo permanente de cuenta y notificación por correo | ✅ | — |
| 6 | Registro de eventos de seguridad (log de auditoría) | ✅ | — |
| 7 | Documentos legales obligatorios + versionado | ✅ | — |
| 8 | Inicio y cierre de sesión | ✅ | — |
| 9 | Hash de contraseñas de bóveda con bcrypt | ✅ | ✅ |
| 10 | Derivación de clave criptográfica (PBKDF2-HMAC-SHA256) | ✅ | ✅ |
| 11 | Cifrado simétrico de entradas (Fernet / AES-128-CBC) | ✅ | ✅ |
| 12 | Salt criptográfico por bóveda | ✅ | ✅ |
| 13 | Bloqueo de bóveda por intentos fallidos (3 intentos) | ✅ | ✅ |
| 14 | Pregunta de seguridad y cifrado de recuperación | ✅ | ✅ |
| 15 | Bloqueo permanente de bóveda | ✅ | ✅ |
| 16 | Cierre automático de sesión por inactividad | ✅ | ✅ |
| 17 | Validación de permisos de directorio | — | ✅ |

**Total de implementaciones (contando dobles):** 24

---

## Detalle de cada control

---

### CONTROL 1 — Autenticación de usuario con email y contraseña
**Modo:** Cloud únicamente  
**Aplicabilidad:** Acceso al sistema

#### Descripción
El sistema implementa un proceso de autenticación en dos capas antes de conceder acceso:

1. **Verificación local con bcrypt:** Antes de contactar a Firebase, se consulta el perfil del usuario en Firestore y se compara la contraseña ingresada contra el hash bcrypt almacenado. Si no coincide, la petición nunca llega a Firebase Auth.
2. **Autenticación con Firebase REST API:** Si la verificación bcrypt es exitosa, se llama al endpoint `signInWithPassword` de Firebase para obtener un `idToken` de sesión JWT.

#### Archivos involucrados
- `views/firebaseLogic.py` — `AuthFire.login_con_email()` (líneas 189–363)
- `views/cloud.py` — `_hacer_login()` (maneja la UI del flujo)

#### Datos técnicos
- Endpoint Firebase: `identitytoolkit.googleapis.com/v1/accounts:signInWithPassword`
- Token devuelto: `idToken` (JWT firmado por Firebase)
- Timeout de la petición HTTP: 10 segundos

---

### CONTROL 2 — Verificación de correo electrónico obligatoria
**Modo:** Cloud únicamente  
**Aplicabilidad:** Acceso al sistema

#### Descripción
Ningún usuario puede iniciar sesión si su correo electrónico no ha sido verificado. El sistema:

1. Tras el login, consulta el campo `emailVerified` de Firebase Auth (vía `accounts:lookup` para evitar latencia de propagación).
2. Si no está verificado, lanza `VerificacionRequeridaError` e impide el acceso.
3. Ofrece al usuario reenviar el correo de verificación sin necesidad de ingresar la contraseña de nuevo.
4. Permite comprobar en tiempo real si el correo ya fue verificado mediante el botón "Ya lo verifiqué".

#### Archivos involucrados
- `views/firebaseLogic.py` — `VerificacionRequeridaError`, `enviar_correo_verificacion()`, `comprobar_verificacion_email()`, `sincronizar_verificacion()`
- `views/cloud.py` — `_reenviar_verificacion()`, `_comprobar_verificacion()`

#### Datos técnicos
- El estado de verificación se sincroniza en Firestore (`usuarios/{uid}.email_verificado`) en cada login exitoso.
- Se usa `accounts:lookup` (en tiempo real) en lugar de confiar en el valor devuelto por `signInWithPassword` (puede tener latencia).

---

### CONTROL 3 — Hash de contraseñas de usuario (login) con bcrypt
**Modo:** Cloud únicamente  
**Aplicabilidad:** Almacenamiento de credenciales

#### Descripción
Las contraseñas de los usuarios **nunca se almacenan en texto plano**. Al registrarse, la contraseña se transforma en un hash bcrypt con salt autogenerado antes de guardarse en Firestore. En el login, la verificación se realiza localmente con `bcrypt.checkpw` sin necesidad de exponer la contraseña a Firebase.

#### Archivos involucrados
- `views/firebaseLogic.py` — `_encriptar_password()`, `_verificar_password()`
- Campo en Firestore: `usuarios/{uid}.password` (hash bcrypt)

#### Datos técnicos
- Algoritmo: bcrypt con salt generado automáticamente por `bcrypt.gensalt()`
- Factor de trabajo: valor por defecto de la librería `bcrypt` (12 rondas)
- El hash se almacena como string UTF-8 de 60 caracteres

---

### CONTROL 4 — Bloqueo temporal de cuenta por intentos fallidos
**Modo:** Cloud únicamente  
**Aplicabilidad:** Protección contra ataques de fuerza bruta al login

#### Descripción
Tras **2 intentos fallidos consecutivos** de inicio de sesión, la cuenta queda bloqueada temporalmente durante **60 segundos**. El bloqueo se persiste en Firestore con el campo `bloqueado_temp_hasta` (timestamp UTC). Si el usuario intenta iniciar sesión antes de que expire el bloqueo, se le informa cuántos segundos debe esperar.

#### Archivos involucrados
- `views/firebaseLogic.py` — constantes `MAX_INTENTOS_TEMP = 2`, `DURACION_BLOQUEO_S = 60`
- Campo Firestore: `usuarios/{uid}.bloqueado_temp_hasta`, `usuarios/{uid}.intentos_fallidos_login`

#### Datos técnicos
- Umbral: 2 intentos fallidos
- Duración del bloqueo: 60 segundos
- El contador se resetea a 0 al producirse un login exitoso

---

### CONTROL 5 — Bloqueo permanente de cuenta y notificación por correo
**Modo:** Cloud únicamente  
**Aplicabilidad:** Protección contra ataques persistentes, respuesta a incidentes

#### Descripción
Tras **5 intentos fallidos acumulados**, la cuenta queda **bloqueada permanentemente** (`cuenta_bloqueada = True` en Firestore). Adicionalmente, se envía automáticamente un correo de notificación al usuario para alertarle del bloqueo e indicarle cómo contactar al equipo de soporte. El desbloqueo requiere intervención manual del administrador.

#### Archivos involucrados
- `views/firebaseLogic.py` — constante `MAX_INTENTOS_PERM = 5`, `_enviar_correo_bloqueo_cuenta()`
- Campo Firestore: `usuarios/{uid}.cuenta_bloqueada`

#### Datos técnicos
- Umbral de bloqueo permanente: 5 intentos fallidos
- Envío de correo: SMTP con TLS (configurable vía variables de entorno `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_HOST`, `SMTP_PORT`)
- El envío es "best-effort": si el SMTP no está configurado, el bloqueo en Firestore se aplica igualmente

---

### CONTROL 6 — Registro de eventos de seguridad (log de auditoría)
**Modo:** Cloud únicamente  
**Aplicabilidad:** Trazabilidad, auditoría y respuesta a incidentes

#### Descripción
Cada evento relevante de seguridad relacionado con el login queda registrado en Firestore con su tipo, email, detalle descriptivo y timestamp del servidor. Los eventos registrados son:

| Tipo de evento | Descripción |
|---|---|
| `intento_fallido` | Contraseña incorrecta en el login |
| `bloqueo_temporal` | Bloqueo de 60 s aplicado |
| `bloqueo_permanente` | Cuenta deshabilitada definitivamente |
| `login_exitoso` | Acceso correcto al sistema |

#### Archivos involucrados
- `views/firebaseLogic.py` — `_registrar_evento_seguridad()`
- Ruta Firestore: `usuarios/{uid}/log_seguridad/{auto-id}`

#### Datos técnicos
- El registro es "best-effort" (no bloquea el flujo de autenticación si falla)
- Todos los timestamps son `SERVER_TIMESTAMP` (hora del servidor de Firestore)

---

### CONTROL 7 — Documentos legales obligatorios y versionado
**Modo:** Cloud únicamente  
**Aplicabilidad:** Cumplimiento legal, derechos de autor, privacidad

#### Descripción
Antes de acceder a la aplicación por primera vez (o tras una actualización de los documentos), el usuario debe **leer y aceptar explícitamente** los tres documentos legales:

1. **Términos de Uso del Software** — condiciones de uso, responsabilidades, propiedad intelectual y derechos de autor de NébulaVault.
2. **Aviso de Privacidad** — información sobre tratamiento de datos personales.
3. **Acuerdo de Confidencialidad** — obligaciones de confidencialidad sobre la información gestionada con la aplicación.

El sistema implementa **versionado de documentos**: cada documento tiene una versión con fecha (`LEGAL_VERSIONS`). Si los textos legales son actualizados, la versión cambia y el sistema **fuerza re-aceptación** al siguiente login, incluso si el usuario ya aceptó versiones anteriores.

#### Archivos involucrados
- `views/legalTexts.py` — textos completos de los tres documentos, UI de aceptación
- `views/firebaseLogic.py` — `LEGAL_VERSIONS`, `verificar_aceptacion_terminos()`, `guardar_aceptacion_terminos()`
- `views/cloud.py` — `on_login_exitoso()`, `_mostrar_terminos()`, `_tras_aceptar_terminos()`, `_on_rechazo_terminos()`

#### Datos técnicos
- Versión actual de los tres documentos: `2026-02-06`
- Ruta Firestore: `users/{uid}/legal/acceptance`
- Campos almacenados: `accepted`, `accepted_at` (timestamp), `terms_version`, `privacy_version`, `confidentiality_version`
- Si el usuario rechaza los términos: no puede acceder a la aplicación

---

### CONTROL 8 — Inicio y cierre de sesión
**Modo:** Cloud únicamente  
**Aplicabilidad:** Gestión de sesión, trazabilidad

#### Descripción
La aplicación implementa un ciclo completo de sesión:

- **Inicio de sesión:** Proceso de doble verificación (bcrypt local + Firebase Auth REST API). Al iniciar sesión correctamente se registra el evento `login_exitoso` en el log de auditoría.
- **Cierre de sesión explícito:** El usuario puede cerrar sesión desde la pantalla de perfil (`ProfileScreen`). Al hacerlo, se destruye la ventana de bóvedas y se regresa a la pantalla de login (`PantallaCloud`), descartando el `idToken` de sesión de memoria.

#### Archivos involucrados
- `views/cloud.py` — `_hacer_login()`, pantalla de login
- `views/profileScreen.py` — botón de cierre de sesión
- `views/bovedaScreen.py` — `_cerrar_sesion()`

#### Datos técnicos
- El `idToken` de Firebase solo existe en memoria durante la sesión activa; nunca se persiste en disco
- Al cerrar sesión se destruye el objeto `BovedaScreen` y toda la clave Fernet activa queda fuera de alcance (GC de Python)

---

### CONTROL 9 — Hash de contraseñas de bóveda con bcrypt
**Modo:** Cloud ✅ · On-Premises ✅ *(implementado dos veces)*  
**Aplicabilidad:** Almacenamiento seguro de credenciales de acceso a bóvedas

#### Descripción
La contraseña de cada bóveda **nunca se almacena en texto plano**, ni en Firestore ni en la base de datos local. Al crear una bóveda se genera un hash bcrypt con salt autogenerado. En cada intento de desbloqueo, la contraseña ingresada se verifica localmente contra dicho hash.

#### Archivos involucrados
- `services/crypto.py` — `hashear_password_boveda()`, `verificar_password_boveda()`
- Cloud: campo `password_hash` en `users/{uid}/bovedas/{id}` (Firestore)
- On-Premises: campo `password_hash` en tabla `bovedas` (SQLite)

#### Datos técnicos
- Algoritmo: bcrypt con `bcrypt.gensalt()` (salt único por bóveda)
- La verificación se realiza 100% en local; no hay petición de red para desbloquear una bóveda

---

### CONTROL 10 — Derivación de clave criptográfica (PBKDF2-HMAC-SHA256)
**Modo:** Cloud ✅ · On-Premises ✅ *(implementado dos veces)*  
**Aplicabilidad:** Seguridad de la clave de cifrado de entradas

#### Descripción
La clave Fernet que cifra las entradas de cada bóveda **no se almacena**. Se deriva en memoria cada vez que el usuario desbloquea la bóveda, usando PBKDF2-HMAC-SHA256 a partir de:

- **Material:** contraseña de la bóveda (texto plano, solo en memoria)
- **Salt (Cloud):** los primeros 16 caracteres del `uid` de Firebase del usuario
- **Salt (On-Premises):** 16 bytes aleatorios generados con `os.urandom(16)` al crear la bóveda, almacenados como hex en la BD

Al cerrar o bloquear la bóveda, la instancia Fernet se descarta de memoria.

#### Archivos involucrados
- `services/crypto.py` — `derivar_clave_boveda()`, `get_fernet_boveda()`
- `services/local_storage.py` — `_fernet_desde_material()`, `get_fernet_local()`

#### Datos técnicos
- Algoritmo KDF: PBKDF2-HMAC-SHA256
- Iteraciones: **100,000**
- Longitud de la clave derivada: 32 bytes → codificada en base64-urlsafe para Fernet
- Librería: `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC`

---

### CONTROL 11 — Cifrado simétrico de entradas (Fernet / AES-128-CBC + HMAC-SHA256)
**Modo:** Cloud ✅ · On-Premises ✅ *(implementado dos veces)*  
**Aplicabilidad:** Confidencialidad de las contraseñas almacenadas en bóvedas

#### Descripción
Las contraseñas de las entradas se cifran con **Fernet** antes de guardarse (en Firestore o en SQLite). Fernet es un esquema de cifrado autenticado que combina AES-128-CBC para confidencialidad con HMAC-SHA256 para integridad. La clave Fernet es exclusiva por bóveda y se deriva según el Control 10.

Si alguien accede directamente a la base de datos (Firestore o el archivo `.db`) solo encuentra tokens cifrados; sin la contraseña de la bóveda no puede descifrar ninguna entrada.

#### Archivos involucrados
- `services/crypto.py` — `cifrar()`, `descifrar()`
- `views/bovedaScreen.py` — uso al guardar/mostrar entradas
- `views/bovedaScreenLocal.py` — uso al guardar/mostrar entradas

#### Datos técnicos
- Esquema: **Fernet** (de la librería `cryptography`)
- Componentes internos: AES-128-CBC (confidencialidad) + HMAC-SHA256 (integridad y autenticación)
- Los tokens cifrados incluyen un timestamp interno (parte del formato Fernet)
- Ante token manipulado o clave incorrecta se lanza `InvalidToken` → el sistema devuelve `ValueError` con mensaje descriptivo

---

### CONTROL 12 — Salt criptográfico por bóveda
**Modo:** Cloud ✅ · On-Premises ✅ *(implementados de forma diferente)*  
**Aplicabilidad:** Unicidad de claves, protección ante ataques de diccionario entre bóvedas

#### Descripción
El salt garantiza que dos bóvedas con la misma contraseña produzcan claves de cifrado **completamente distintas**.

- **Cloud:** el salt es `uid[:16]`, donde `uid` es el identificador único de Firebase del usuario. Así, dos usuarios con la misma contraseña de bóveda tienen claves distintas.
- **On-Premises:** se genera `os.urandom(16)` (16 bytes completamente aleatorios) al crear cada bóveda. El valor en hex se almacena en la columna `salt` de la tabla `bovedas`. Esto garantiza unicidad incluso dentro del mismo archivo `.db`.

#### Archivos involucrados
- Cloud: `services/crypto.py` — `derivar_clave_boveda()` (parámetro `uid`)
- On-Premises: `views/bovedaScreenLocal.py` — `_on_crear_boveda()` usa `os.urandom(16)`; `services/local_storage.py` — columna `salt`, `get_fernet_local()`

#### Datos técnicos
- Cloud: salt = 16 bytes derivados del UID (texto UTF-8)
- On-Premises: salt = 16 bytes de `os.urandom()` → 128 bits de entropía garantizada
- El salt de On-Premises se almacena en hex (32 caracteres) en la BD y se convierte con `bytes.fromhex()` al usarse

---

### CONTROL 13 — Bloqueo de bóveda por intentos fallidos (3 intentos)
**Modo:** Cloud ✅ · On-Premises ✅ *(implementado dos veces)*  
**Aplicabilidad:** Protección de bóvedas ante acceso no autorizado

#### Descripción
Cada bóveda tiene un contador de intentos fallidos de contraseña independiente:

- **1er intento fallido:** Mensaje de error genérico.
- **2° intento fallido:** Advertencia de "último intento disponible".
- **3er intento fallido:** La bóveda queda marcada como `boveda_bloqueada = True`. La contraseña ya no se puede ingresar; se muestra el diálogo de pregunta de seguridad (Control 14).

El contador se resetea a 0 al desbloquear exitosamente.

#### Archivos involucrados
- `views/bovedaScreen.py` — `_dialogo_desbloquear()`, llama a `actualizar_intentos_boveda()` de `services/bovedas.py`
- `views/bovedaScreenLocal.py` — `_dialogo_desbloquear()`, llama a `actualizar_intentos_boveda()` de `services/local_storage.py`

#### Datos técnicos
- Umbral de bloqueo: 3 intentos fallidos
- Estado persistido en Firestore (`boveda_bloqueada`) o SQLite (columna `boveda_bloqueada`)
- Los intentos se sincronizan a la base de datos en cada fallo (best-effort)

---

### CONTROL 14 — Pregunta de seguridad y cifrado de recuperación de bóveda
**Modo:** Cloud ✅ · On-Premises ✅ *(implementado dos veces)*  
**Aplicabilidad:** Recuperación de acceso tras bloqueo de bóveda

#### Descripción
Al crear una bóveda, el usuario elige una pregunta de seguridad y proporciona su respuesta. El sistema:

1. Cifra la **contraseña de la bóveda** usando la respuesta como material de derivación (PBKDF2 + Fernet) y almacena el token resultante en `password_cifrada_con_respuesta`.
2. Tras el bloqueo por intentos (Control 13), muestra la pregunta de seguridad.
3. Si la respuesta es correcta, descifra `password_cifrada_con_respuesta` para recuperar la contraseña original, resetea los contadores y abre la bóveda.
4. Si la respuesta es incorrecta, la bóveda pasa a **bloqueo permanente** (Control 15).

La respuesta se normaliza (minúsculas, sin espacios extremos) antes de derivar la clave, haciéndola insensible a mayúsculas y espacios accidentales.

#### Archivos involucrados
- `services/crypto.py` — `cifrar_password_con_respuesta()`, `descifrar_password_con_respuesta()`, `_derivar_clave_respuesta()`
- `services/local_storage.py` — `cifrar_password_con_respuesta_local()`, `descifrar_password_con_respuesta_local()`
- `views/bovedaScreen.py` — `_dialogo_pregunta_seguridad()`
- `views/bovedaScreenLocal.py` — `_dialogo_pregunta_seguridad()`

#### Datos técnicos
- KDF de la respuesta: PBKDF2-HMAC-SHA256, 100,000 iteraciones
- Preguntas disponibles: 5 opciones predefinidas (no hay preguntas personalizadas abiertas)

---

### CONTROL 15 — Bloqueo permanente de bóveda
**Modo:** Cloud ✅ · On-Premises ✅ *(implementado dos veces)*  
**Aplicabilidad:** Última barrera de protección de datos en bóvedas

#### Descripción
Si el usuario responde **incorrectamente** la pregunta de seguridad (Control 14), la bóveda queda marcada como `boveda_inaccesible = True`. A partir de ese momento:

- La bóveda aparece marcada con `⛔ [INACCESIBLE]` en la lista.
- No puede abrirse por ningún medio dentro de la aplicación.
- El contenido **no puede recuperarse**; la clave de cifrado se pierde definitivamente.

Esta política es intencional: garantiza que, ante la pérdida de ambos factores de autenticación (contraseña + respuesta de seguridad), los datos cifrados sean irrecuperables incluso con acceso físico a la base de datos.

#### Archivos involucrados
- `services/bovedas.py` — `bloquear_boveda_permanente()`
- `services/local_storage.py` — `bloquear_boveda_permanente()`
- `views/bovedaScreen.py` — `_dialogo_pregunta_seguridad()`, `_seleccionar_boveda()`
- `views/bovedaScreenLocal.py` — `_dialogo_pregunta_seguridad()`, `_seleccionar_boveda()`

#### Datos técnicos
- Estado persistido en Firestore (`boveda_inaccesible`) o SQLite (columna `boveda_inaccesible`)
- No existe función de desbloqueo; la única acción posible es eliminar la bóveda

---

### CONTROL 16 — Cierre automático de sesión por inactividad
**Modo:** Cloud ✅ · On-Premises ✅ *(implementado dos veces, con destinos diferentes)*  
**Aplicabilidad:** Protección ante abandono de sesión activa

#### Descripción
Si el usuario no interactúa con la aplicación durante **5 minutos**, el sistema cierra la sesión automáticamente:

- **Cloud:** Destruye la ventana de bóvedas, descarta la clave Fernet activa de memoria y redirige al login (`PantallaCloud`).
- **On-Premises:** Destruye la ventana de bóvedas, descarta la clave Fernet activa de memoria y redirige al selector de directorio (`OnPremisesPath`), no al `WelcomeScreen`.

La inactividad se detecta mediante `bind_all` sobre la raíz de la aplicación: cualquier movimiento de ratón, pulsación de tecla, clic o scroll reinicia el temporizador. Los eventos se capturan también en los diálogos `Toplevel` (como el de desbloqueo de bóveda).

#### Archivos involucrados
- `views/bovedaScreen.py` — `INACTIVITY_TIMEOUT_MS`, `_iniciar_inactividad()`, `_reiniciar_timer()`, `_on_inactividad()`
- `views/bovedaScreenLocal.py` — mismos métodos con destino `OnPremisesPath`

#### Datos técnicos
- Tiempo de inactividad: **300,000 ms (5 minutos)** (constante `INACTIVITY_TIMEOUT_MS`)
- Implementado con `root.after()` de tkinter (no requiere hilos adicionales)
- Eventos monitoreados: `<Motion>`, `<KeyPress>`, `<Button-1>`, `<Button-2>`, `<Button-3>`, `<MouseWheel>`
- El temporizador se cancela con `after_cancel` al navegar manualmente para evitar callbacks sobre ventanas destruidas

---

### CONTROL 17 — Validación de permisos de directorio
**Modo:** On-Premises únicamente  
**Aplicabilidad:** Integridad del almacenamiento local, prevención de errores de configuración

#### Descripción
Antes de inicializar (o abrir) la base de datos SQLite, el sistema valida que el directorio proporcionado por el usuario:

1. **Existe** en el sistema de archivos (`os.path.isdir()`).
2. **Tiene permisos de escritura** para el proceso actual (`os.access(ruta, os.W_OK)`).

Si alguna condición no se cumple, se muestra un mensaje de error descriptivo y no se procede a crear ni abrir el archivo `nebulavault.db`. Esto previene errores silenciosos o corrupción de datos por permisos insuficientes.

#### Archivos involucrados
- `views/onPremisesPath.py` — `_confirmar()`
- `services/local_storage.py` — `init_db()` (crea las tablas si no existen)

#### Datos técnicos
- Validaciones: existencia del directorio + permisos de escritura del proceso
- Nombre fijo del archivo de base de datos: `nebulavault.db`
- Si el archivo ya existe (sesión previa), `init_db()` lo abre sin reinicializarlo (`CREATE TABLE IF NOT EXISTS`)

---

## Controles no implementados / áreas de mejora sugeridas

Las siguientes funcionalidades **no están implementadas** en la versión actual y podrían considerarse para futuras versiones o para complementar el documento final:

| Control sugerido | Observación |
|---|---|
| Autenticación multifactor (MFA/2FA) | Firebase soporta TOTP; no está habilitado en esta versión |
| Cifrado del archivo `.db` completo | El archivo SQLite en disco no está cifrado; solo las contraseñas de entradas lo están |
| Exportación/importación segura de bóvedas | No existe función de backup/restore |
| Política de contraseña para bóvedas (complejidad mínima) | Solo se valida longitud mínima de 6 caracteres |
| Auditoría de accesos a bóvedas On-Premises | No hay log local equivalente al `log_seguridad` de la nube |
| Borrado seguro de memoria | Las claves Fernet se descartan por GC; no hay sobreescritura explícita |

---

*Documento generado para uso interno. Elaborado con base en el análisis del código fuente de NébulaVault v1.0.0.*
