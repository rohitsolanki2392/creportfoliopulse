import firebase_admin
from firebase_admin import firestore, credentials
import os
from app.config import FIRESTORE_SECRET_KEY


if not firebase_admin._apps:
    if not os.path.exists(FIRESTORE_SECRET_KEY):
        raise FileNotFoundError(
            f"CRITICAL: serviceAccountKey.json not found!\n"
            f"Expected location: {FIRESTORE_SECRET_KEY}\n"
            f"Download it from Firebase Console → Project Settings → Service accounts → Generate new private key"
        )
    
    cred = credentials.Certificate(FIRESTORE_SECRET_KEY)
    firebase_admin.initialize_app(cred)
    print("Firestore initialized successfully using serviceAccountKey.json")

db = firestore.client()