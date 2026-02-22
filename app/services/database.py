import gspread
from gspread.exceptions import WorksheetNotFound # <-- NOUVEL IMPORT IMPORTANT
import datetime
import logging
import io
import csv
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
            nom = item.get("item", "")
            type_item = item.get("type", "")
            quantite = item.get("quantity", "") # On récupère enfin la quantité !
            
            # Si on a une quantité, on l'affiche, sinon on met juste le nom
            if quantite:
                billing_text += f"- {nom} : {quantite} ({type_item})\n"
            else:
                billing_text += f"- {nom} ({type_item})\n"

        reminders_list = json_data.get("reminders", [])
        
        # Rétrocompatibilité au cas où l'IA utilise encore l'ancien mot "reminder"
        if "reminder" in json_data and isinstance(json_data["reminder"], dict):
            reminders_list.append(json_data["reminder"])
            
        reminder_text = ""
        for rem in reminders_list:
            tache = rem.get("task", "")
            date_prevue = rem.get("due_date", "bientôt")
            if tache:
                reminder_text += f"- {tache} (Pour: {date_prevue})\n"
            
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
    
def export_artisan_data(artisan_name):
    """Récupère les données d'un artisan et génère un CSV"""
    try:
        sh = gc.open(settings.SHEET_NAME)
        
        # 1. On cherche l'onglet
        try:
            worksheet = sh.worksheet(artisan_name)
        except WorksheetNotFound:
            return None # L'onglet n'existe pas encore
            
        # 2. On récupère TOUTES les données du tableau
        data = worksheet.get_all_values()
        
        if not data or len(data) <= 1:
            return None # Le tableau est vide (ou n'a que la ligne d'en-tête)
            
        # 3. On crée le fichier CSV en mémoire (sans le sauvegarder sur le disque dur)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(data)
        
        logger.info(f"📤 Données exportées pour {artisan_name}")
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'export pour {artisan_name} : {e}")
        return False