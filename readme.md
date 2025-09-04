# OpeneAI TG Bot Fishing Helper 🎣

Телеграм-бот для рыболовов с использованием GPT и дополнительных сервисов.  
Поддерживает режимы: факты, GPT-чат, квиз на тему рыбалки, прогноз погоды.

## 📦 Возможности

- **Главное меню** с выбором режимов.
- **Факты** — интересные случайные факты (сгенерированы GPT).
- **GPT-чат** — диалоговый режим с кнопкой выхода.
- **Квиз по рыбалке**  
  - 10 вопросов с тремя вариантами ответа.  
  - Подсчёт правильных ответов.  
  - Кнопка «Закончить» на каждом шаге.  
  - Итоговый результат и возврат в меню.  
- **Погода**  
  - Получение прогноза по геолокации пользователя.  
  - 3 ближайших дня: температура (день/ночь), осадки, давление.  

## 🛠 Технологии

- Python 3.11+
- [python-telegram-bot v20+](https://github.com/python-telegram-bot/python-telegram-bot)
- OpenAI API (через `OpenAiClient`)
- [aiohttp](https://docs.aiohttp.org/en/stable/) для запросов к Open-Meteo API
- Open-Meteo (бесплатный источник прогноза погоды)

## ⚙️ Установка и запуск

1. Клонировать репозиторий:
   ```bash
   git clone https://github.com/<your-username>/OpeneAI_TG_bot_Fishing_Helper.git
   cd OpeneAI_TG_bot_Fishing_Helper
   ```

2. Создать и активировать виртуальное окружение:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / MacOS
   .venv\Scripts\activate      # Windows
   ```

3. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Настроить конфигурацию (файл `config.py` или `.env`):
   ```env
   TG_BOT_API_KEY=ваш_токен_бота
   OPENAI_API_KEY=ваш_api_ключ_OpenAI
   ```

5. Запустить:
   ```bash
   python src/bot.py
   ```

## 📂 Структура проекта

```
src/
 ├─ bot.py                # основной файл бота
 ├─ utils.py              # утилиты (загрузка сообщений, промптов, картинок)
 ├─ openapi_client.py     # клиент для OpenAI
 ├─ service/
 │   ├─ quiz.py           # квиз про рыбалку
 │   └─ weather.py        # прогноз погоды
 └─ resources/            # картинки, тексты и промпты
```
