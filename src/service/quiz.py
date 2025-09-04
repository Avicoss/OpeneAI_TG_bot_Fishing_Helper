# src/service/quiz.py
from __future__ import annotations

import logging
import re
from typing import Optional, Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils import load_prompt
from openapi_client import OpenAiClient

QUIZ_ANS_PREFIX = "quiz_ans:"
QUIZ_TOTAL = 10
MAX_RETRIES = 3

EXIT_KB = InlineKeyboardMarkup([[InlineKeyboardButton("Закончить", callback_data="finish")]])

openai_client = OpenAiClient()
_start_func = None

def register_quiz(start_func):
    global _start_func
    _start_func = start_func

_CODE_FENCE_RE = re.compile(r"^```[\w-]*\s*[\r\n]?|```$", flags=re.MULTILINE)

def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text or "").strip()

def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _parse_quiz_text(raw: str) -> Optional[Dict]:
    text = _strip_code_fences(raw)
    text = re.sub(r"\r\n?", "\n", text)

    q_match   = re.search(r"(?i)Вопрос\s*:\s*(.+)", text)
    a_match   = re.search(r"(?mi)^\s*A\)\s*(.+)", text)
    b_match   = re.search(r"(?mi)^\s*B\)\s*(.+)", text)
    c_match   = re.search(r"(?mi)^\s*C\)\s*(.+)", text)
    ans_match = re.search(r"(?i)Правильный\s*:\s*([ABC])\b", text)

    if not (q_match and a_match and b_match and c_match and ans_match):
        return None

    q = _collapse_spaces(q_match.group(1))
    options = [
        _collapse_spaces(a_match.group(1)),
        _collapse_spaces(b_match.group(1)),
        _collapse_spaces(c_match.group(1)),
    ]
    answer = {"A": 0, "B": 1, "C": 2}[ans_match.group(1).upper()]
    return {"q": q, "options": options, "answer": answer}

async def _generate_fishing_quiz_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
    system_prompt = load_prompt("quiz")
    st = context.user_data.setdefault("quiz_state", {"n": 0, "score": 0})
    seen: List[str] = st.setdefault("seen_questions", [])

    for attempt in range(1, MAX_RETRIES + 1):
        user_prompt = (
            "Сгенерируй ОДИН тестовый вопрос о рыбалке на русском языке с ТРЕМЯ вариантами.\n"
            "ФОРМАТ ОТВЕТА (строго, БЕЗ пояснений, БЕЗ дополнительного текста):\n"
            "Вопрос: <короткий вопрос>\n"
            "Варианты:\n"
            "A) <вариант A>\n"
            "B) <вариант B>\n"
            "C) <вариант C>\n"
            "Правильный: <A|B|C>\n"
            "Требования: без переносов строки внутри вариантов; без кавычек «ёлочек»; новый вопрос, не повторяй предыдущие."
        )

        try:
            raw = await openai_client.ask(user_prompt, system_prompt)
        except Exception as e:
            logging.error(f"[QUIZ] Ошибка GPT-запроса: {e}")
            raw = ""

        parsed = _parse_quiz_text(raw)

        if parsed and parsed["q"] not in seen:
            seen.append(parsed["q"])
            return parsed

        logging.warning(f"[QUIZ] Попытка #{attempt}: формат/дубль не подошёл. Ответ модели: {raw!r}")

    return {
        "q": "Какой тип поводка лучше выбрать для осторожной рыбы?",
        "options": ["Флюорокарбоновый", "Стальной", "Без поводка"],
        "answer": 0,
    }

async def _send_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    st = context.user_data.setdefault("quiz_state", {"n": 0, "score": 0})

    if st["n"] >= QUIZ_TOTAL:
        await _finish_quiz(update, context)
        return

    q = await _generate_fishing_quiz_question_text(update, context)
    st["current_correct"] = int(q["answer"])

    rows = [
        [InlineKeyboardButton(q["options"][0], callback_data=f"{QUIZ_ANS_PREFIX}0")],
        [InlineKeyboardButton(q["options"][1], callback_data=f"{QUIZ_ANS_PREFIX}1")],
        [InlineKeyboardButton(q["options"][2], callback_data=f"{QUIZ_ANS_PREFIX}2")],
        EXIT_KB.inline_keyboard[0],
    ]
    kb = InlineKeyboardMarkup(rows)

    text = f"*Вопрос {st['n'] + 1}/{QUIZ_TOTAL}:*\n{q['q']}"

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logging.warning(f"[QUIZ] edit_message_text не удался, отправляю новое. Причина: {e}")
            await update.effective_message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.effective_message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

async def _finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    st = context.user_data.get("quiz_state", {"score": 0})
    score = int(st.get("score", 0))

    await update.effective_chat.send_message(
        f"Готово! Правильных ответов: *{score}* из *{QUIZ_TOTAL}*.",
        parse_mode=ParseMode.MARKDOWN,
    )

    context.user_data.pop("quiz_state", None)
    context.user_data["mode"] = ""

    if _start_func:
        await _start_func(update, context)

async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["quiz_state"] = {"n": 0, "score": 0}
    await _send_quiz_question(update, context)

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith(QUIZ_ANS_PREFIX):
        try:
            chosen = int(data.split(":", 1)[1])
        except Exception:
            await query.answer("Не удалось распознать ответ")
            return

        st = context.user_data.get("quiz_state")
        if not st:
            context.user_data["quiz_state"] = {"n": 0, "score": 0}
            st = context.user_data["quiz_state"]

        correct_idx = int(st.get("current_correct", -1))
        if chosen == correct_idx:
            st["score"] = int(st.get("score", 0)) + 1
            await query.answer("Верно ✅")
        else:
            await query.answer("Неверно ❌")

        st["n"] = int(st.get("n", 0)) + 1
        await _send_quiz_question(update, context)
        return

    if data == "finish":
        try:
            await query.edit_message_text("Квиз завершён. Возвращаемся в меню…")
        except Exception:
            pass

        context.user_data.pop("quiz_state", None)
        if _start_func:
            await _start_func(update, context)
        return
