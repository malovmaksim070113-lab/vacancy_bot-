import os
import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================== НАСТРОЙКИ ==================

# // ВСТАВЬ СЮДА ТОКЕН БОТА (Railway → Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# // ВСТАВЬ СЮДА TG-КАНАЛ
CHANNEL_ID = "@tgsdsa"

CHECK_INTERVAL_HOURS = 3
MIN_SALARY = 150_000

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway → Variables")

sent_links = set()

# ================== ФИЛЬТРЫ ==================

def is_sys_analyst(title: str) -> bool:
    title = title.lower()
    keywords = [
        "системный аналитик",
        "system analyst",
        "business analyst",
        "it analyst",
        "аналитик"
    ]
    return any(k in title for k in keywords)


def is_remote(text: str) -> bool:
    keywords = ["удален", "remote", "дистанцион", "home office"]
    return any(k in text for k in keywords)


def salary_ok(salary: dict | None) -> bool:
    if not salary:
        return True

    values = [v for v in [salary.get("from"), salary.get("to")] if v]
    return not values or max(values) >= MIN_SALARY


# ================== HH API ==================

def fetch_hh_vacancies():
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": "системный аналитик",
        "area": 113,  # Россия
        "per_page": 20,
        "only_with_salary": False
    }

    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    data = r.json()

    vacancies = []

    for item in data.get("items", []):
        snippet_text = (
            (item.get("snippet", {}).get("requirement") or "") +
            (item.get("snippet", {}).get("responsibility") or "")
        ).lower()

        vacancies.append({
            "title": item["name"],
            "company": item["employer"]["name"],
            "rating": item["employer"].get("rating", "—"),
            "link": item["alternate_url"],
            "salary": item.get("salary"),
            "experience": item.get("experience", {}).get("name", "Не указан"),
            "snippet": snippet_text
        })

    return vacancies


# ================== TELEGRAM ==================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


def format_salary(salary: dict | None) -> str:
    if not salary:
        return "ЗП не указана"

    frm = salary.get("from")
    to = salary.get("to")
    currency = salary.get("currency", "RUR")

    if frm and to:
        return f"{frm}–{to} {currency}"
    if frm:
        return f"от {frm} {currency}"
    if to:
        return f"до {to} {currency}"

    return "ЗП не указана"


def format_message(v: dict) -> str:
    return (
        f"{v['title']}\n"
        f"{v['company']}\n"
        f"{format_salary(v['salary'])}\n"
        f"Опыт: {v['experience']}\n"
        f"Рейтинг компании: {v['rating']}\n"
        f"{v['link']}"
    )


async def check_and_send():
    for v in fetch_hh_vacancies():
        if not is_sys_analyst(v["title"]):
            continue
        if not salary_ok(v["salary"]):
            continue
        if not is_remote(v["snippet"]):
            continue
        if v["link"] in sent_links:
            continue

        await bot.send_message(CHANNEL_ID, format_message(v))
        sent_links.add(v["link"])


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("🤖 Бот запущен. Вакансии публикуются в канале.")


@dp.message_handler(commands=["check"])
async def manual_check(msg: types.Message):
    await msg.answer("🔍 Проверяю вакансии на hh.ru ...")
    await check_and_send()


# ================== АВТОПРОВЕРКА ==================

async def on_startup(dp):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_send, "interval", hours=CHECK_INTERVAL_HOURS)
    scheduler.start()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
