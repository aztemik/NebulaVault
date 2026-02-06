from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

COMPANY = {
    "name": "Nébula Security",
    "product": "NébulaVault",
    "tagline": "Gestor local de credenciales – versión académica",
    "objective": (
        "NébulaVault es una aplicación de escritorio orientada a la gestión segura "
        "de credenciales de acceso de forma local.\n\n"
        "El proyecto tiene como objetivo principal demostrar el diseño de una "
        "bóveda digital, permitiendo crear, abrir y administrar registros de "
        "credenciales bajo el principio de mínimo privilegio.\n\n"
        "Esta versión corresponde a un MVP académico, enfocado en la estructura, "
        "navegación, presentación de la empresa y definición conceptual de los "
        "mecanismos de seguridad que serán implementados en versiones futuras."
    ),
    "logo_path": ASSETS_DIR / "logo.png",
}

LEGAL_TEXTS = {
    "Aviso de privacidad": (
        "Nébula Security informa que la presente aplicación corresponde a una "
        "versión DEMO con fines académicos.\n\n"
        "• La aplicación no recopila, transmite ni comparte información a través "
        "de internet.\n"
        "• No existe comunicación con servidores externos ni servicios en la nube.\n"
        "• En esta etapa no se implementa cifrado real ni almacenamiento seguro "
        "de contraseñas.\n\n"
        "La información ingresada por el usuario tiene únicamente fines de "
        "simulación y demostración del funcionamiento conceptual del sistema."
    ),
    "Acuerdo de confidencialidad": (
        "El usuario reconoce que esta aplicación se encuentra en fase de desarrollo "
        "y se compromete a no introducir información sensible, real o confidencial "
        "durante su uso.\n\n"
        "Nébula Security no se hace responsable por la exposición de datos que el "
        "usuario decida ingresar voluntariamente en esta versión demo.\n\n"
        "El contenido y la estructura del software forman parte de un proyecto "
        "académico y no deben ser distribuidos o reutilizados con fines comerciales."
    ),
    "Términos de uso": (
        "NébulaVault es un software en desarrollo, distribuido únicamente con fines "
        "educativos y de evaluación académica.\n\n"
        "• El uso está limitado a prácticas escolares o demostraciones.\n"
        "• No se garantiza la seguridad de la información ingresada.\n"
        "• Las funciones de seguridad avanzada (cifrado, derivación de claves, "
        "auditoría y control de accesos) serán consideradas en versiones futuras.\n\n"
        "El uso del software implica la aceptación de estos términos."
    ),
}
