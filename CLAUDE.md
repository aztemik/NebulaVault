# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**NébulaVault** — Desktop credential management application built with Python + tkinter. Supports two deployment modes: On-Premises (stub, not yet implemented) and Cloud (Firebase).

## Running the app

```bash
source entorno/bin/activate
python main.py
```

The virtual environment (`entorno/`) uses Python 3.12.4. There is no build step or test suite.

## Environment setup

Create a `.env` file in the project root with:
```
FIREBASE_CREDENTIALS=/path/to/service-account.json
FIREBASE_API_KEY=<web-api-key-from-firebase-console>
```

`nebulavault.json` in the repo root is the Firebase service account credentials file.

## Architecture

### Entry point and navigation flow

```
main.py → app.py (run_app) → WelcomeScreen (views/WelcomeScreen.py)
    ├── On-Premises → abrir_pantalla_on_premises() [stub, not implemented]
    └── Cloud → PantallaCloud (views/cloud.py)
                    ├── Login/Register → AuthFire (views/firebaseLogic.py)
                    └── After login → check legal acceptance
                            ├── Accepted → PantallaPrincipal (views/pantallaPrincipal.py)
                            └── Not accepted → WelcomeScreen (views/legalTexts.py) [legal consent]
                                                └── on_accepted → PantallaPrincipal
```

### Key naming collision

`WelcomeScreen` exists in **two** files with different roles:
- `views/WelcomeScreen.py` → initial screen asking On-Premises vs Cloud
- `views/legalTexts.py` → legal consent screen shown after login

### Module responsibilities

| File | Role |
|------|------|
| `firebase_config.py` | Firebase Admin SDK init + REST API URL template; reads `.env` |
| `views/firebaseLogic.py` | `AuthFire` class — login, register, email verification, legal acceptance check/save in Firestore |
| `views/cloud.py` | `PantallaCloud` — login and registration UI for Cloud mode |
| `views/legalTexts.py` | Legal texts (Terms, Privacy, Confidentiality) + consent flow |
| `views/pantallaPrincipal.py` | Post-login main screen stub |
| `views/WelcomeScreen.py` | First screen with mode selection |

### Stub files (empty, not yet implemented)

`views/home.py`, `views/vault.py`, `views/about.py`, `views/welcome.py`, `services/audit.py`

## Firebase data model

- `usuarios/{uid}` — user profile with `nombre`, `email`, `password` (bcrypt hash), `uid`, `activo`, `rol`, `modo`, `email_verificado`
- `users/{uid}/legal/acceptance` — legal consent record with `accepted`, `accepted_at`, and version fields

Passwords are hashed with bcrypt before storing in Firestore. Authentication uses both Firebase Auth REST API (`signInWithPassword`) and the Admin SDK.

Legal document versions are tracked in `LEGAL_VERSIONS` in `views/firebaseLogic.py`. Bump these dates when legal texts change to force re-acceptance.

## UI design system

All view files share the same NébulaVault design tokens (colors, fonts) but each file redefines them locally — there is no shared constants module. When adding a new screen, copy the palette block from an existing view. The aesthetic is dark cybersecurity / cosmic-industrial using `Courier New` monospace fonts.

Custom widgets: `NVButton` (canvas-based button with hover) and `NVEntry` (styled Entry with focus effects) are defined independently in `views/WelcomeScreen.py` and `views/cloud.py`.
