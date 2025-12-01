import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuración del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token de tu bot
TOKEN = "7524353782:AAEwgHLdwMSvietPvFk25cKH9lJCMU1tTBI"

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"¡Hola {user.first_name}! Soy tu bot de Telegram.\n"
        "Escribe /help para ver los comandos disponibles."
    )

# Comando /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    📍 *Comandos disponibles:*
    /start - Iniciar el bot
    /help - Ver este mensaje de ayuda
    /info - Información sobre el bot
    
    ✨ *Características:*
    - Responde a mensajes de texto
    - Comandos básicos
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Comando /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = """
    🤖 *Información del Bot*
    
    Este es un bot de Telegram creado con:
    - python-telegram-bot
    - Python
    
    Token: 7524353782:AAEwgHLdwMSvietPvFk25cKH9lJCMU1tTBI
    """
    await update.message.reply_text(info_text, parse_mode='Markdown')

# Manejar mensajes de texto
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logger.info(f"Mensaje de {update.effective_user.username}: {user_message}")
    
    # Respuesta simple
    response = f"Recibí tu mensaje: {user_message}"
    await update.message.reply_text(response)

# Manejar errores
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    if update and hasattr(update, 'message'):
        await update.message.reply_text("❌ Ocurrió un error. Intenta nuevamente.")

def main():
    """Iniciar el bot"""
    # Crear la aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Añadir manejadores de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info))
    
    # Añadir manejador de mensajes de texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Añadir manejador de errores
    application.add_error_handler(error_handler)
    
    # Iniciar el bot
    print("🤖 Bot iniciado...")
    print("Presiona Ctrl+C para detenerlo")
    
    # Iniciar el polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()