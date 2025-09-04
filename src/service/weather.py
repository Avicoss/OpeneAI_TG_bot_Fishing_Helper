from __future__ import annotations

import math
from typing import Optional

import aiohttp
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

EXIT_KB = InlineKeyboardMarkup([[InlineKeyboardButton("Закончить", callback_data="finish")]])

_start_func = None


def register_weather(app: Application, start_func):
    global _start_func
    _start_func = start_func
    app.add_handler(CommandHandler("weather", weather_start))
    app.add_handler(MessageHandler(filters.LOCATION, weather_location_handler))


async def weather_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["weather"] = {}
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton(text="Отправить геолокацию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        selective=True,
    )
    await update.effective_message.reply_text(
        "Отправь свою геолокацию, и я покажу прогноз на 3 дня.\nМожешь нажать кнопку ниже.",
        reply_markup=kb
    )


async def weather_location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.location:
        await update.effective_message.reply_text("Не вижу геолокацию. Попробуй ещё раз через кнопку.")
        return

    lat = update.message.location.latitude
    lon = update.message.location.longitude
    context.user_data.setdefault("weather", {})["last_location"] = (lat, lon)

    data = await _fetch_openmeteo(lat, lon)
    if not data:
        await update.effective_message.reply_text("Не удалось получить прогноз. Попробуем позже.")
        return

    text = _format_forecast(data)
    await update.effective_chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=EXIT_KB)

    if _start_func:
        await _start_func(update, context)

async def _fetch_openmeteo(lat: float, lon: float) -> Optional[dict]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat:.6f}&longitude={lon:.6f}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,surface_pressure_mean"
        "&forecast_days=3&timezone=auto"
    )
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return None
                return await r.json()
    except Exception:
        return None


def _mmhg(hpa: float) -> int:
    return int(round(hpa * 0.75006))


def _format_forecast(payload: dict) -> str:
    d = payload.get("daily") or {}
    dates = d.get("time") or []
    tmax = d.get("temperature_2m_max") or []
    tmin = d.get("temperature_2m_min") or []
    prec = d.get("precipitation_sum") or []
    press = d.get("surface_pressure_mean") or []

    lines = ["*Погода на 3 дня:*"]
    for i in range(min(3, len(dates))):
        day = dates[i]
        day_t = tmax[i] if i < len(tmax) else None
        night_t = tmin[i] if i < len(tmin) else None
        p_mm = _mmhg(press[i]) if i < len(press) and press[i] is not None else None
        pr_mm = prec[i] if i < len(prec) else None

        t_day = f"{int(round(day_t))}°C" if day_t is not None else "—"
        t_night = f"{int(round(night_t))}°C" if night_t is not None else "—"
        p_txt = f"{p_mm} мм рт. ст." if p_mm is not None else "—"
        pr_txt = f"{pr_mm:.1f} мм" if pr_mm is not None else "—"

        lines.append(
            f"*{day}*\n"
            f"Днём: {t_day}  •  Ночью: {t_night}\n"
            f"Осадки: {pr_txt}  •  Давление: {p_txt}"
        )

    return "\n\n".join(lines)
