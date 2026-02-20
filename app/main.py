# bot.py (VERSION FINALE - PRODUCTION)
import os
import json
import logging
import asyncio
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from app.config import settings
# Nos modules maison
from app.services.brain import analyze_audio
from app.services.database import save_intervention

logger = logging.getLogger("VoiceBridge")

def format_for_human(data):
    """
    Transforme les données (Dictionnaire Python) en message lisible.
    NOTE: Cette version prend un DICTIONNAIRE en entrée, plus du texte brut.
    """
    try:
        inter = data.get("intervention", {})
        remind = data.get("reminder", {})
        
        # 1. En-tête
        msg = f"✅ <b>Intervention : {inter.get('client', 'Inconnu')}</b>\n"
        msg += f"<i>Statut : {inter.get('status', 'N/A')}</i>\n\n"
        
        # 2. Facturation
        msg += "💰 <b>À Facturer :</b>\n"
        items = inter.get("billing_items", [])
        if not items:
            msg += "Aucun élément détecté.\n"
        
        for item in items:
            icon = "🛠️"
            if "MO" in item.get("type", "") or "Main" in item.get("type", ""):
                icon = "⏱️"
            elif "Forfait" in item.get("type", ""):
                icon = "🚗"
                
            msg += f"{icon} {item.get('item')}"
            if item.get("note"):
                msg += f" ({item.get('note')})"
            msg += "\n"
            
        # 3. Rappel
        if remind and remind.get("task"):
            msg += f"\n⏰ <b>Rappel ({remind.get('due_date', 'bientôt')}) :</b>\n"
            msg += f"👉 {remind.get('task')}\n"
            
        return msg

    except Exception as e:
        return f"⚠️ Erreur d'affichage : {e}"

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"🎤 Note vocale reçue de {user.first_name}")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("🎧 J'analyse et je sauvegarde...")

    try:
        # 1. Téléchargement
        new_file = await update.message.voice.get_file()
        file_path = f"temp_{user.id}.ogg"
        await new_file.download_to_drive(file_path)

        # 2. Analyse Gemini (Cerveau)
        loop = asyncio.get_running_loop()
        json_text = await loop.run_in_executor(None, analyze_audio, file_path)

        # 3. Nettoyage et Conversion en Dictionnaire
        # On enlève les balises ```json éventuelles
        clean_json = json_text.replace("```json", "").replace("```", "").strip()
        data_dict = json.loads(clean_json)

        # 4. Sauvegarde Google Sheets (Mémoire)
        # On l'exécute aussi dans le thread pour ne pas ralentir le bot
        saved = await loop.run_in_executor(None, save_intervention, data_dict)
        
        # 5. Réponse à l'utilisateur
        pretty_message = format_for_human(data_dict)
        
        if saved:
            pretty_message += "\n\n💾 <b>Sauvegardé dans le Sheet !</b>"
        else:
            pretty_message += "\n\n⚠️ <b>Erreur de sauvegarde Google Sheets</b>"

        await update.message.reply_text(pretty_message, parse_mode=ParseMode.HTML)

        # 6. Ménage
        os.remove(file_path)

    except Exception as e:
        logger.error(f"❌ Erreur critique : {e}")
        await update.message.reply_text("❌ Oups, je n'ai pas compris cet audio.")

if __name__ == '__main__':
    # Vérification initiale
    try:
        settings.check()
    except ValueError as e:
        logger.critical(e)
        exit(1)
        
    app = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # --- NOUVELLE LOGIQUE DE DÉMARRAGE (Webhook vs Polling) ---
    
    # Render injecte automatiquement ces variables dans le Cloud
    PORT = int(os.environ.get("PORT", "10000"))
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

    if RENDER_URL:
        # Mode Cloud (Render) : On ouvre le port web pour Telegram
        logger.info(f"🌐 Démarrage en mode Webhook sur {RENDER_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=RENDER_URL
        )
    else:
        # Mode Local (Ton PC) : On garde l'ancienne méthode
        logger.info("💻 Démarrage en mode Polling (Local)")
        app.run_polling()