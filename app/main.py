# bot.py (VERSION FINALE - PRODUCTION)
import os
import json
import logging
import asyncio
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

from app.config import settings
# Nos modules maison
from app.services.brain import analyze_audio
from app.services.database import save_intervention, export_artisan_data

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
        saved = await loop.run_in_executor(None, save_intervention, data_dict, user.first_name)
        
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

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📊 Demande d'export reçue de {user.first_name}")

    # On fait patienter l'utilisateur
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")
    await update.message.reply_text("📊 Je prépare ton fichier de comptabilité, un instant...")

    try:
        # On va chercher les données dans Google Sheets
        loop = asyncio.get_running_loop()
        csv_data = await loop.run_in_executor(None, export_artisan_data, user.first_name)

        if csv_data is None:
            await update.message.reply_text("🤷‍♂️ Je n'ai trouvé aucune donnée pour toi. Fais ta première intervention vocalement !")
        elif csv_data is False:
            await update.message.reply_text("❌ Oups, un problème technique m'empêche de lire tes données.")
        else:
            # On transforme le texte en un "vrai" fichier téléchargeable
            file_bytes = csv_data.encode('utf-8-sig') # le "-sig" aide Excel à bien lire les accents (é, à)
            
            # On envoie le document !
            await update.message.reply_document(
                document=file_bytes,
                filename=f"Compta_{user.first_name}.csv",
                caption="✅ Et voilà ! Voici ton fichier prêt à être envoyé à ton comptable."
            )

    except Exception as e:
        logger.error(f"Erreur d'export : {e}")
        await update.message.reply_text("❌ Erreur inattendue.")

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"🚀 Nouvel utilisateur démarré : {user.first_name}")

    welcome_message = (
        f"Salut {user.first_name} et bienvenue sur VoiceBridge BTP (Version Bêta) ! 🏗️\n\n"
        "Je suis ton assistant vocal. Dicte-moi tes fins de chantier, et je prépare ta facturation.\n\n"
        "🎙️ *Comment ça marche ?*\n"
        "1. Envoie un vocal : *\"Chantier Dupont terminé, j'ai passé 2h et posé un siphon.\"*\n"
        "2. Je trie le matériel et la main-d'œuvre.\n"
        "3. Tape /export le vendredi pour récupérer ton tableau Excel.\n\n"
        "⚠️ *CONDITIONS D'UTILISATION (BÊTA) :*\n"
        "_Cet outil est actuellement en phase de test gratuit. En l'utilisant, tu acceptes que tes données (via Telegram et Google) soient traitées pour générer ta comptabilité. Cet outil est une aide : la vérification finale de tes factures et devis reste sous ton entière responsabilité. Aucune réclamation ne pourra être faite en cas d'erreur de l'IA ou de perte de données._\n\n"
        "👉 *Envoie ton premier vocal pour commencer !*"
    )

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

if __name__ == '__main__':
    # Vérification initiale
    try:
        settings.check()
    except ValueError as e:
        logger.critical(e)
        exit(1)
        
    app = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CommandHandler("export", handle_export))
    
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