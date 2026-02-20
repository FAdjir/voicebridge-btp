# database.py
import gspread
import datetime
import logging
from app.config import settings

logger = logging.getLogger(__name__)

try:
    gc = gspread.service_account(filename=settings.GOOGLE_CREDENTIALS)
except Exception as e:
    logger.warning(f"⚠️ Impossible de charger credentials.json : {e}")

def save_intervention(json_data):
    try:
        sh = gc.open(settings.SHEET_NAME)
        worksheet = sh.sheet1 # Première feuille
        
        # On extrait les données du JSON
        # Note: json_data est déjà un dictionnaire Python ici
        inter = json_data.get("intervention", {})
        remind = json_data.get("reminder", {})
        
        # Préparation de la ligne
        date_now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        client = inter.get("client", "Inconnu")
        status = inter.get("status", "N/A")
        
        # Formatage des items de facturation en une seule cellule
        billing_text = ""
        for item in inter.get("billing_items", []):
            billing_text += f"- {item['item']} ({item.get('type', '')})\n"
            
        # Formatage du rappel
        reminder_text = ""
        if remind and remind.get("task"):
            reminder_text = f"{remind['task']} (Pour: {remind.get('due_date')})"
            
        # Ajout de la ligne dans le tableau
        worksheet.append_row([
            date_now,
            client,
            status,
            billing_text,
            reminder_text
        ])

        logger.info(f"💾 Sauvegarde réussie pour {client}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur Google Sheets : {e}")
        return False

# Test direct si on lance ce fichier
if __name__ == "__main__":
    # Donnée factice pour tester
    fake_data = {
        "intervention": {
            "client": "Test Codeur",
            "status": "En cours",
            "billing_items": [{"item": "Test unitaire", "type": "Dev"}]
        },
        "reminder": {"task": "Boire un café", "due_date": "Maintenant"}
    }
    
    print("💾 Tentative de sauvegarde...")
    if save_intervention(fake_data):
        print("✅ Succès ! Va voir ton Google Sheet !")
    else:
        print("❌ Échec.")