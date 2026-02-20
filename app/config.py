# app/config.py
import os
import logging
from dotenv import load_dotenv

# Chargement du fichier .env
load_dotenv()

# Configuration des Logs (Standard 2026)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class Config:
    # On vérifie les clés critiques
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    GOOGLE_CREDENTIALS = "credentials.json" # Chemin vers le fichier JSON
    SHEET_NAME = "Suivi Chantiers"

    @classmethod
    def check(cls):
        """Vérifie que tout est prêt avant de démarrer"""
        missing = []
        if not cls.GEMINI_API_KEY: missing.append("GEMINI_API_KEY")
        if not cls.TELEGRAM_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
        
        if missing:
            raise ValueError(f"❌ CONFIGURATION INCOMPLÈTE : Il manque {', '.join(missing)}")
        
        logging.info("✅ Configuration chargée avec succès.")

# On instancie la config
settings = Config()