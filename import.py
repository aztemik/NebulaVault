import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

cred = credentials.Certificate("/home/pol/Documentos/seguridad en el desarrollo de aplicaciones/producto1/pure-277a9-firebase-adminsdk-fbsvc-79829ed84d.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

uid = "hola"  # puede ser el UID real de Firebase Auth

# 1) Insert del usuario
user_ref = db.collection("usuarios").document(uid)
user_ref.set({
    "nombre": "Luis martinez martinez",
    "email": "luis@example.com",
    "activo": True
})

# # 2) Insert relacionado al usuario (subcolección)
# alumno_ref = user_ref.collection("alumnos").document()  # auto-id
# alumno_ref.set({
#     "mat": "a1",
#     "promedio": 9.8,     # mejor número que string
#     "createdAt": firestore.SERVER_TIMESTAMP
# })

print("Usuario:", user_ref.id)
# print("Alumno relacionado:", alumno_ref.id)

