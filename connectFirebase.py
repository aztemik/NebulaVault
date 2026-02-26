import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("/home/pol/Documentos/seguridad en el desarrollo de aplicaciones/producto1/pure-277a9-firebase-adminsdk-fbsvc-79829ed84d.json")
firebase_admin.initialize_app(cred)
