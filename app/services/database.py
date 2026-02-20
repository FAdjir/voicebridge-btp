import gspread
from gspread.exceptions import WorksheetNotFound # <-- NOUVEL IMPORT IMPORTANT
import datetime
import logging
from app.config import settings

logger = logging.getLogger(__name__)

try:
    gc = gspread.service_account(filename=settings.GOOGLE_CREDENTIALS)
except Exception as e:
    logger.warning(f"⚠️ Impossible de charger credentials.json : {e}")

# On ajoute un nouveau paramètre "artisan_name" à la fonction
def save_intervention(json_data, artisan_name="Inconnu"):
    try:
        sh = gc.open(settings.SHEET_NAME)
        
        # 1. Le Bot cherche l'onglet de l'artisan
        try:
            worksheet = sh.worksheet(artisan_name)
        except WorksheetNotFound:
            # 2. S'il n'existe pas, il le crée avec le nom du Telegram de l'utilisateur
            logger.info(f"✨ Création d'un nouvel onglet pour le testeur : {artisan_name}")
            worksheet = sh.add_worksheet(title=artisan_name, rows="1000", cols="5")
            # On génère la toute première ligne d'en-tête
            worksheet.append_row(["Date", "Client", "Statut", "Détails Facture", "Rappels"])

        # Extraction des données (Inchangé)
        inter = json_data.get("intervention", {})
        remind = json_data.get("reminder", {})
        
        date_now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        client = inter.get("client", "Inconnu")
        status = inter.get("status", "N/A")
        
        billing_text = ""
        for item in inter.get("billing_items", []):
            billing_text += f"- {item.get('item', '')} ({item.get('type', '')})\n"
            
        reminder_text = ""
        if remind and remind.get("task"):
            reminder_text = f"{remind.get('task')} (Pour: {remind.get('due_date', 'bientôt')})"
            
        # Ajout de la ligne dans LE BON ONGLET
        worksheet.append_row([
            date_now,
            client,
            status,
            billing_text,
            reminder_text
        ])
        
        logger.info(f"💾 Sauvegarde réussie dans l'onglet '{artisan_name}'")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur Google Sheets : {e}")
        return False