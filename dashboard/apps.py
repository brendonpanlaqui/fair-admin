from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
import os

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        # Initialize Firebase Admin SDK
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
        
        if cred_path and not firebase_admin._apps:
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Firebase Admin initialized successfully in dashboard app.")
            except Exception as e:
                print(f"Failed to initialize Firebase: {e}")