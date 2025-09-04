from config import TG_BOT_API_KEY
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from utils import load_messages_for_bot, load_prompt, get_image_path
from openapi_client import OpenAiClient
from src.service.quiz import quiz_start, quiz_callback, register_quiz
from service.weather import register_weather
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

openai_client = OpenAiClient()

EXIT_KB = InlineKeyboardMarkup([[InlineKeyboardButton("Закончить", callback_data="finish")]])


async def start(update: Update, context: ContextTypes):
    register_quiz(start)
    register_weather(app, start)
    text = load_messages_for_bot("main")
    image_path = get_image_path("main")

    msg = update.effective_message
    with open(image_path, "rb") as photo:
        await msg.reply_photo(photo=photo, caption=text, parse_mode="MARKDOWN")


async def random_fact(update: Update, context: ContextTypes):
    text = load_messages_for_bot("random")
    prompt = load_prompt("random")
    image_path = get_image_path("random")

    keyboard = [
        [InlineKeyboardButton("Еще факт", callback_data="random_again")],
        [InlineKeyboardButton("Закончить", callback_data="finish")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        gpt_response = await openai_client.ask("", prompt)

        with open(image_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"{text}\n\n{gpt_response}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        logging.error(f"Error in random_fact: {e}")
        await update.message.reply_text("ОЙ, случилась ошибка. Давай попробуем позже.")


async def gpt_interface(update: Update, context: ContextTypes):
    text = load_messages_for_bot("gpt")
    image_path = get_image_path("gpt")

    context.user_data["mode"] = "gpt"

    with open(image_path, "rb") as photo:
        await update.message.reply_photo(photo=photo, caption=text, parse_mode="Markdown", reply_markup=EXIT_KB)


async def handle_text_messages(update: Update, context: ContextTypes):
    user_mode = context.user_data.get("mode", "")
    user_text = update.message.text

    if user_mode == "gpt":
        prompt = load_prompt("gpt")
        try:
            gpt_response = await openai_client.ask(user_text, prompt)
            await update.message.reply_text(gpt_response)

        except Exception as e:
            logging.error(f"Error in gpt mode: {e}")
            await update.message.reply_text("ОЙ, случилась ошибка. Давай попробуем позже.")


async def handle_callback(update: Update, context: ContextTypes):
    query = update.callback_query
    await query.answer()

    if query.data == "random_again":
        prompt = load_prompt("random")
        try:
            gpt_response = await openai_client.ask("", prompt)

            keyboard = [
                [InlineKeyboardButton("Хочу еще факт", callback_data="random_again")],
                [InlineKeyboardButton("Закончить", callback_data="finish")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_caption(
                caption=f"{load_messages_for_bot("random")}\n\n{gpt_response}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Error in random_again: {e}")
            await query.edit_message_caption("ОЙ, случилась ошибка. Давай попробуем позже.")

    elif query.data == "finish":
        context.user_data.clear()
        await start(update, context)


app = ApplicationBuilder().token(TG_BOT_API_KEY).build()

app.add_handler(CallbackQueryHandler(quiz_callback, pattern=r"^(quiz_ans:\d+|finish)$"))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("random", random_fact))
app.add_handler(CommandHandler("gpt", gpt_interface))
app.add_handler(CommandHandler("quiz", quiz_start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
app.add_handler(CallbackQueryHandler(handle_callback))

app.run_polling()