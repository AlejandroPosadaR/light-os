import os
from google.cloud import firestore
from google.auth.credentials import AnonymousCredentials


def get_db() -> firestore.Client:
    """Get Firestore client. Uses emulator if FIRESTORE_EMULATOR_HOST is set."""
    emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST")
    
    if emulator_host:
        project_id = os.getenv("GCP_PROJECT_ID", "test-project")
        return firestore.Client(project=project_id, credentials=AnonymousCredentials())
    
    project_id = os.getenv("GCP_PROJECT_ID")
    if project_id:
        return firestore.Client(project=project_id)
    
    return firestore.Client()
