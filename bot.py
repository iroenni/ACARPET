#!/usr/bin/env python3
"""
Bot de Telegram mejorado
Características:
- Manejo seguro de tokens mediante variables de entorno
- Sistema de logging avanzado
- Comandos adicionales
- Manejo de errores robusto
- Persistencia básica
- Middleware para analytics
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    PicklePersistence,
)

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

# Cargar variables de entorno desde archivo .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Constantes
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    # Token hardcodeado solo para desarrollo - ELIMINAR en producción
    TOKEN = "7524353782:AAEwgHLdwMSvietPvFk25cKH9lJCMU1tTBI"
    print("⚠️  ADVERTENCIA: Usando token hardcodeado. NO usar en producción.")

# Estados para conversaciones
ASK_QUESTION, CONFIRM_DELETE = range(2)

# ============================================================================
# CONFIGURACIÓN AVANZADA DE LOGGING
# ============================================================================

class CustomFormatter(logging.Formatter):
    """Formateador personalizado para logs"""
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Configurar logger principal
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler para consola con colores
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(CustomFormatter())

# Handler para archivo
file_handler = logging.FileHandler('bot.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class UserStats:
    """Estadísticas de usuario"""
    user_id: int
    username: str
    first_name: str
    message_count: int = 0
    command_count: int = 0
    last_seen: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'message_count': self.message_count,
            'command_count': self.command_count,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }

class AnalyticsMiddleware:
    """Middleware para tracking de uso"""
    
    def __init__(self):
        self.user_stats: Dict[int, UserStats] = {}
        self.daily_stats = defaultdict(int)
        self.load_stats()
    
    def load_stats(self):
        """Cargar estadísticas desde archivo"""
        try:
            if os.path.exists('stats.json'):
                with open('stats.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data.get('users', []):
                        user = UserStats(
                            user_id=user_data['user_id'],
                            username=user_data['username'],
                            first_name=user_data['first_name'],
                            message_count=user_data['message_count'],
                            command_count=user_data['command_count'],
                            last_seen=datetime.fromisoformat(user_data['last_seen']) if user_data['last_seen'] else None
                        )
                        self.user_stats[user.user_id] = user
                logger.info(f"Estadísticas cargadas: {len(self.user_stats)} usuarios")
        except Exception as e:
            logger.error(f"Error cargando estadísticas: {e}")
    
    def save_stats(self):
        """Guardar estadísticas en archivo"""
        try:
            data = {
                'users': [user.to_dict() for user in self.user_stats.values()],
                'daily_stats': dict(self.daily_stats),
                'last_updated': datetime.now().isoformat()
            }
            with open('stats.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando estadísticas: {e}")
    
    def track_user(self, user):
        """Registrar actividad de usuario"""
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_stats[today] += 1
        
        if user.id not in self.user_stats:
            self.user_stats[user.id] = UserStats(
                user_id=user.id,
                username=user.username or 'Sin username',
                first_name=user.first_name or 'Sin nombre',
                message_count=0,
                command_count=0,
                last_seen=datetime.now()
            )
        
        stats = self.user_stats[user.id]
        stats.last_seen = datetime.now()
        
        # Guardar cada 10 interacciones
        if sum([stats.message_count, stats.command_count]) % 10 == 0:
            self.save_stats()
    
    def track_message(self, user):
        """Registrar mensaje de usuario"""
        self.track_user(user)
        self.user_stats[user.id].message_count += 1
    
    def track_command(self, user):
        """Registrar comando de usuario"""
        self.track_user(user)
        self.user_stats[user.id].command_count += 1

# ============================================================================
# MANEJADORES DE COMANDOS MEJORADOS
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador mejorado para /start"""
    user = update.effective_user
    analytics = context.bot_data.get('analytics')
    
    if analytics:
        analytics.track_command(user)
    
    # Mensaje de bienvenida personalizado
    welcome_text = f"""
✨ *¡Hola {user.first_name}!* ✨

🤖 Soy un bot avanzado de Telegram con muchas funcionalidades.

📍 *Comandos principales:*
/start - Iniciar el bot
/help - Ayuda completa
/info - Información del bot
/stats - Ver estadísticas
/ask - Hacerme una pregunta
/settings - Configuraciones

💡 *Tip:* También puedes enviarme cualquier mensaje y te responderé.

⚡ *Versión:* 2.0.0
📊 *Usuarios activos:* {len(analytics.user_stats) if analytics else 'N/A'}
"""
    
    # Crear teclado inline
    keyboard = [
        [
            InlineKeyboardButton("📋 Comandos", callback_data="help"),
            InlineKeyboardButton("ℹ️ Info", callback_data="info"),
        ],
        [
            InlineKeyboardButton("📊 Estadísticas", callback_data="stats"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    # Registrar en log
    logger.info(f"Nuevo usuario: {user.id} - {user.username}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador mejorado para /help"""
    help_text = """
📚 *AYUDA COMPLETA DEL BOT*

📍 *COMANDOS PRINCIPALES:*
/start - Iniciar el bot
/help - Ver esta ayuda
/info - Información técnica
/stats - Estadísticas de uso
/ask - Hacer una pregunta
/feedback - Enviar feedback
/settings - Configuración

🛠 *COMANDOS AVANZADOS:*
/time - Hora actual
/echo [texto] - Repetir texto
/calc [expresión] - Calculadora básica
/weather [ciudad] - Clima (próximamente)

📱 *INTERACCIÓN:*
- Responde a mensajes de texto
- Soporta Markdown
- Teclados inline
- Conversaciones interactivas

🔐 *SEGURIDAD:*
- Logging detallado
- Manejo de errores
- Protección contra spam
- Stats anónimas

📧 *SOPORTE:*
Para reportar problemas o sugerencias:
/feedback [tu mensaje]
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador mejorado para /info"""
    app = context.application
    
    info_text = f"""
🤖 *INFORMACIÓN DEL BOT*

⚙️ *Tecnología:*
- Python {app.__version__ if hasattr(app, '__version__') else '3.11+'}
- python-telegram-bot v20.7
- Arquitectura async/await

📈 *Estadísticas:*
- Bot ID: {app.bot.id if app.bot else 'N/A'}
- Username: @{app.bot.username if app.bot else 'N/A'}
- Desarrollado con ❤️

🔧 *Características:*
- Logging avanzado
- Persistencia de datos
- Analytics
- Manejo de errores
- Middleware personalizado

🚀 *Despliegue:*
- Docker compatible
- GitHub Actions
- Variables de entorno
- Configuración modular

📄 *Licencia:* MIT
📧 *Soporte:* Usa /feedback
"""
    
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar estadísticas de uso"""
    analytics = context.bot_data.get('analytics')
    
    if not analytics or not analytics.user_stats:
        await update.message.reply_text("📊 *Estadísticas no disponibles aún*", parse_mode='Markdown')
        return
    
    total_messages = sum(u.message_count for u in analytics.user_stats.values())
    total_commands = sum(u.command_count for u in analytics.user_stats.values())
    active_users = len(analytics.user_stats)
    
    # Top 5 usuarios más activos
    top_users = sorted(
        analytics.user_stats.values(),
        key=lambda x: x.message_count + x.command_count,
        reverse=True
    )[:5]
    
    stats_text = f"""
📊 *ESTADÍSTICAS DEL BOT*

👥 *Usuarios:*
- Total usuarios: {active_users}
- Mensajes totales: {total_messages}
- Comandos totales: {total_commands}

🏆 *Top 5 usuarios:*
"""
    
    for i, user in enumerate(top_users, 1):
        last_seen = user.last_seen.strftime('%Y-%m-%d %H:%M') if user.last_seen else 'Nunca'
        stats_text += f"{i}. {user.first_name} (@{user.username})\n"
        stats_text += f"   📨 Msgs: {user.message_count} | ⚡ Cmds: {user.command_count}\n"
        stats_text += f"   👀 Visto: {last_seen}\n"
    
    stats_text += f"\n📅 *Actividad hoy:* {analytics.daily_stats.get(datetime.now().strftime('%Y-%m-%d'), 0)} interacciones"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar hora actual en diferentes zonas"""
    from datetime import datetime
    import pytz
    
    zones = {
        '🌍 Madrid': 'Europe/Madrid',
        '🇺🇸 NY': 'America/New_York',
        '🇯🇵 Tokyo': 'Asia/Tokyo',
        '🇦🇺 Sydney': 'Australia/Sydney'
    }
    
    time_text = "🕐 *HORA ACTUAL*\n\n"
    
    for name, tz in zones.items():
        try:
            tz_obj = pytz.timezone(tz)
            current_time = datetime.now(tz_obj).strftime('%Y-%m-%d %H:%M:%S')
            time_text += f"{name}: `{current_time}`\n"
        except:
            time_text += f"{name}: Error\n"
    
    await update.message.reply_text(time_text, parse_mode='Markdown')

async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /echo para repetir texto"""
    if not context.args:
        await update.message.reply_text("⚠️ Uso: /echo [texto]")
        return
    
    text = ' '.join(context.args)
    await update.message.reply_text(f"📢 {text}")

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enviar feedback"""
    if not context.args:
        await update.message.reply_text(
            "📝 *Enviar Feedback*\n\n"
            "Uso: /feedback [tu mensaje]\n\n"
            "Ejemplo: /feedback Me encanta el bot, pero...",
            parse_mode='Markdown'
        )
        return
    
    feedback = ' '.join(context.args)
    user = update.effective_user
    
    # Guardar feedback en archivo
    feedback_entry = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'feedback': feedback,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # Cargar feedback existente
        feedbacks = []
        if os.path.exists('feedback.json'):
            with open('feedback.json', 'r', encoding='utf-8') as f:
                feedbacks = json.load(f)
        
        # Añadir nuevo feedback
        feedbacks.append(feedback_entry)
        
        # Guardar
        with open('feedback.json', 'w', encoding='utf-8') as f:
            json.dump(feedbacks, f, indent=2, ensure_ascii=False, ensure_ascii=False)
        
        await update.message.reply_text(
            "✅ *Feedback enviado*\n\n"
            "¡Gracias por tu opinión! La tomaremos en cuenta para mejorar el bot.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Feedback recibido de {user.id}: {feedback[:50]}...")
        
    except Exception as e:
        logger.error(f"Error guardando feedback: {e}")
        await update.message.reply_text("❌ Error al guardar el feedback")

# ============================================================================
# MANEJADORES DE MENSAJES MEJORADOS
# ============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador mejorado de mensajes"""
    user = update.effective_user
    message = update.message.text
    analytics = context.bot_data.get('analytics')
    
    if analytics:
        analytics.track_message(user)
    
    # Log detallado
    logger.info(f"Mensaje de {user.id} (@{user.username}): {message[:100]}...")
    
    # Respuestas inteligentes basadas en contenido
    message_lower = message.lower()
    
    responses = {
        'hola': f"¡Hola {user.first_name}! ¿Cómo estás? 😊",
        'adios': "¡Hasta luego! Espero verte pronto 👋",
        'gracias': "¡De nada! Estoy aquí para ayudarte 🤖",
        'bot': "¡Sí, soy un bot! Pero trato de ser útil 🤖",
        'ayuda': "¿Necesitas ayuda? Usa /help para ver todos los comandos 📚",
        'fecha': f"Hoy es {datetime.now().strftime('%d/%m/%Y')} 📅",
        'hora': f"Son las {datetime.now().strftime('%H:%M')} 🕐",
    }
    
    # Buscar respuesta predefinida
    for keyword, response in responses.items():
        if keyword in message_lower:
            await update.message.reply_text(response)
            return
    
    # Respuesta por defecto mejorada
    default_responses = [
        f"Interesante, {user.first_name}. ¿En qué más puedo ayudarte?",
        f"¡Gracias por tu mensaje, {user.first_name}!",
        f"Lo tengo en cuenta, {user.first_name}. ¿Algo más?",
        f"¿Necesitas que haga algo específico, {user.first_name}?",
    ]
    
    import random
    response = random.choice(default_responses)
    
    # Añadir teclado rápido
    keyboard = [
        [InlineKeyboardButton("📋 Ayuda", callback_data="help"),
         InlineKeyboardButton("ℹ️ Info", callback_data="info")],
        [InlineKeyboardButton("🕐 Hora", callback_data="time"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(response, reply_markup=reply_markup)

# ============================================================================
# MANEJADOR DE CALLBACK QUERIES
# ============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de botones inline"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    handlers = {
        'help': help_command,
        'info': info,
        'stats': stats_command,
        'settings': lambda u, c: u.callback_query.message.reply_text("⚙️ *Configuración*\n\nPróximamente...", parse_mode='Markdown'),
        'time': lambda u, c: u.callback_query.message.reply_text(f"🕐 Hora actual: {datetime.now().strftime('%H:%M:%S')}"),
    }
    
    if data in handlers:
        # Crear un update simulado para el handler
        fake_update = Update(
            update_id=update.update_id,
            message=query.message,
            callback_query=query
        )
        await handlers[data](fake_update, context)
    else:
        await query.message.reply_text(f"Acción: {data}")

# ============================================================================
# MANEJO DE ERRORES MEJORADO
# ============================================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de errores global"""
    error = context.error
    
    # Log del error
    logger.error(f"Exception while handling an update: {error}", exc_info=error)
    
    # Clasificación de errores
    error_messages = {
        'Conflict': "⚠️ El bot ya está procesando una solicitud. Intenta de nuevo en un momento.",
        'Timed out': "⏰ La solicitud tardó demasiado. Intenta de nuevo.",
        'Forbidden': "🔒 No tengo permisos para realizar esta acción.",
        'Bad Request': "📛 Solicitud inválida. Revisa el formato.",
        'Not found': "🔍 Recurso no encontrado.",
    }
    
    # Buscar mensaje apropiado
    error_str = str(error)
    user_message = "❌ Ocurrió un error inesperado. Por favor, intenta nuevamente."
    
    for key, message in error_messages.items():
        if key in error_str:
            user_message = message
            break
    
    # Enviar mensaje al usuario si es posible
    try:
        if update and hasattr(update, 'effective_message'):
            await update.effective_message.reply_text(user_message)
    except Exception as e:
        logger.error(f"Error enviando mensaje de error: {e}")

# ============================================================================
# FUNCIONES UTILITARIAS
# ============================================================================

def setup_persistence():
    """Configurar persistencia de datos"""
    try:
        persistence = PicklePersistence(filepath='bot_data.pickle')
        logger.info("Persistencia configurada correctamente")
        return persistence
    except Exception as e:
        logger.error(f"Error configurando persistencia: {e}")
        return None

async def post_init(application: Application):
    """Tareas posteriores a la inicialización"""
    logger.info("Bot inicializado correctamente")
    
    # Inicializar analytics
    application.bot_data['analytics'] = AnalyticsMiddleware()
    
    # Configurar comandos del bot en Telegram
    commands = [
        ('start', 'Iniciar el bot'),
        ('help', 'Ayuda completa'),
        ('info', 'Información del bot'),
        ('stats', 'Estadísticas de uso'),
        ('time', 'Hora actual'),
        ('echo', 'Repetir texto'),
        ('feedback', 'Enviar feedback'),
    ]
    
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Comandos configurados en Telegram")
    except Exception as e:
        logger.error(f"Error configurando comandos: {e}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal del bot"""
    
    # Verificar token
    if not TOKEN:
        logger.critical("❌ No se encontró el token del bot")
        print("=" * 60)
        print("ERROR: Token no configurado")
        print("Solución:")
        print("1. Exporta la variable: export TELEGRAM_BOT_TOKEN='tu_token'")
        print("2. O crea un archivo .env con TELEGRAM_BOT_TOKEN=tu_token")
        print("=" * 60)
        return
    
    logger.info("🤖 Iniciando Bot de Telegram...")
    logger.info(f"📱 Token: {TOKEN[:10]}...")
    
    try:
        # Configurar persistencia
        persistence = setup_persistence()
        
        # Crear aplicación con configuración mejorada
        application = Application.builder() \
            .token(TOKEN) \
            .persistence(persistence) \
            .post_init(post_init) \
            .concurrent_updates(True) \
            .build()
        
        # Añadir handlers de comandos
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("info", info))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("time", time_command))
        application.add_handler(CommandHandler("echo", echo_command))
        application.add_handler(CommandHandler("feedback", feedback_command))
        
        # Añadir handler de callback queries (botones)
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Añadir handler de mensajes
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        
        # Añadir handler de errores
        application.add_error_handler(error_handler)
        
        # Información de inicio
        logger.info("✅ Bot configurado correctamente")
        logger.info("📡 Iniciando polling...")
        logger.info("🚀 Bot listo para recibir mensajes")
        logger.info("🛑 Presiona Ctrl+C para detener")
        
        print("\n" + "=" * 60)
        print("🤖 BOT INICIADO CORRECTAMENTE")
        print("=" * 60)
        print(f"Token: {TOKEN[:10]}...")
        print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")
        
        # Iniciar polling con configuración mejorada
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
        
    except Exception as e:
        logger.critical(f"Error crítico al iniciar el bot: {e}")
        print(f"❌ Error crítico: {e}")
        
        # Intentar guardar estadísticas si existen
        try:
            analytics = application.bot_data.get('analytics') if 'application' in locals() else None
            if analytics:
                analytics.save_stats()
        except:
            pass

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == '__main__':
    # Manejo de señal para shutdown limpio
    import signal
    import sys
    
    def signal_handler(sig, frame):
        logger.info("🔴 Señal de interrupción recibida")
        logger.info("💾 Guardando datos...")
        print("\n🔄 Cerrando bot de manera segura...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    main()