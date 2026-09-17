"""Application configuration and Firebase Admin SDK initialization."""

from __future__ import annotations

import os

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore


load_dotenv()


def _initialize_firestore():
    """Initialize Firebase Admin and return a Firestore client when configured.

    Local development can start without Firebase credentials. In that case,
    ``db`` is ``None`` and the health endpoint reports the missing configuration.
    When credentials are present, malformed values are allowed to raise during
    startup so deployment configuration errors are immediately visible.
    """

    project_id = os.getenv("FIREBASE_PROJECT_ID")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY")

    if not all((project_id, client_email, private_key)):
        return None

    service_account = {
        "type": "service_account",
        "project_id": project_id,
        "private_key": private_key.replace("\\n", "\n"),
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    try:
        firebase_app = firebase_admin.get_app()
    except ValueError:
        firebase_app = firebase_admin.initialize_app(
            credentials.Certificate(service_account)
        )

    return firestore.client(app=firebase_app)


db = _initialize_firestore()
