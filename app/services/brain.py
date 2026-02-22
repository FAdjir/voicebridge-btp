# brain.py (Version 2.0 - Compatible 2026)
import os
import json
from google import genai
from google.genai import types
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# 1. Charger les variables d'environnement
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# 3. Le Prompt Système (Inchangé, il est parfait)
SYSTEM_PROMPT = """
Tu es un assistant administratif expert en BTP (Plomberie, Électricité, Chauffage).
Ta mission est de structurer des notes vocales d'artisans pour la facturation.

RÈGLES CRITIQUES DE VOCABULAIRE :
1. Utilise UNIQUEMENT le vocabulaire technique du bâtiment.
2. Corrige les erreurs phonétiques courantes :
   - "Chaise d'eau" -> "Chasse d'eau"
   - "Vesse" -> "Vessie"
   - "Paire" -> "PER" (Tuyau)
   - "Multi-couches" -> "Multicouche"
3. Si un mot est ambigu, privilégie le contexte technique (ex: "Joint" est un joint d'étanchéité, pas autre chose).
4. S'il n'y a pas de rappel, renvoie une liste vide []. S'il y en a plusieurs, ajoute-les tous à la liste.

FORMAT DE SORTIE (JSON STRICT) :
{
  "intervention": {
    "client": "Nom du client (Format: Nom Prénom ou M./Mme Nom)",
    "status": "Terminé ou En cours",
    "billing_items": [
      {
        "item": "Nom précis de l'article (Corrigé)", 
        "type": "Matériel ou Main d'oeuvre ou Forfait", 
        "quantity": "Quantité précise (ex: 3 mètres, 2 heures, 1 unité)", 
        "note": "Autres détails éventuels (Dimensions, couleur...)"
      }
    ]
  },
  "reminders": [
    {
      "task": "Action à réaliser (Verbe à l'infinitif)",
      "due_date": "Date ou moment"
    }
  ],
  "audio_quality_score": 0.9
}
"""

def analyze_audio(audio_path):
    logger.info(f"🎤 Traitement audio : {audio_path}")
    
    # Lecture du fichier audio en binaire
    with open(audio_path, "rb") as f:
        audio_content = f.read()

    # Envoi direct (Plus simple qu'avant !)
    # On utilise le modèle Flash 2.0 pour la vitesse
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=audio_content, mime_type="audio/mp3"),
                    types.Part.from_text(text=SYSTEM_PROMPT),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )
    
    logger.info("✅ Analyse terminée !")
    return response.text

# Zone de test
if __name__ == "__main__":
    AUDIO_FILE = "chantier_test.mp3"
    
    if os.path.exists(AUDIO_FILE):
        try:
            json_text = analyze_audio(AUDIO_FILE)
            # On vérifie que c'est bien du JSON valide
            data = json.loads(json_text)
            
            print("\n--- 🎯 RÉSULTAT VALIDÉ ---")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("-" * 30)
            print(f"Client: {data['intervention']['client']}")
            print(f"Rappel: {data['reminder']['task']}")
            
        except Exception as e:
            print(f"❌ Une erreur est survenue : {e}")
    else:
        print(f"❌ Fichier '{AUDIO_FILE}' introuvable.")