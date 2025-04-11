import os
import openai
from flask import Flask, request
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from datetime import datetime, time
import pytz
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_USERS = [5952554641]  # Sustituir con tu ID real
openai.api_key = OPENAI_API_KEY

tz = pytz.timezone("Europe/Madrid")

def dentro_de_horario():
    ahora = datetime.now(tz).time()
    return time(8, 0) <= ahora <= time(23, 0)

# Vector DB
vectorstore = Chroma(persist_directory="vector_db", embedding_function=OpenAIEmbeddings())

# Flask app
app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong", 200

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Telegram bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in ALLOWED_USERS:
        await update.message.reply_text("Hola, soy tu soporte técnico de Grupo Damar. ¿Te puedo ayudar en algo?")
    else:
        await update.message.reply_text("Acceso denegado. Este bot es privado.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("Acceso denegado. Este bot es privado.")
        return

    if not dentro_de_horario():
        await update.message.reply_text("El soporte está disponible de 8:00 a 23:00. ¡Vuelve más tarde!")
        return

    query = update.message.text
    docs = vectorstore.similarity_search(query, k=2)
    contexto = "\n".join([d.page_content for d in docs])

    prompt = f"""Responde técnicamente a esta pregunta basada en los documentos:
Contexto:
{contexto}

Pregunta: {query}"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    await update.message.reply_text(response.choices[0].message.content.strip())

# Ejecutar todo
if __name__ == "__main__":
    Thread(target=run_flask).start()
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_telegram.run_polling()
