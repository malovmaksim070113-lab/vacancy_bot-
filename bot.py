import os
import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")      # Railway → Variables
CHANNEL_ID = "@tgsdsa"                  # твой канал

CHECK_INTERVAL_MINUTES = 5
MIN_SALARY = 150_000

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in Railway Variables")

sent_links = set()

# ================== ФИЛЬТР РОЛЕЙ ==================

def is_target_analyst(title: str) -> bool:
    title = title.lower()

    positive_keywords = [
        "системный аналитик",
        "system analyst",
        "product analyst",
        "продуктовый аналитик",
    ]

    negative_keywords = [
        "data",
        "bi",
        "business intelligence",
        "marketing",
        "маркетинг",
        "financial",
        "финансов",
        "junior",
        "стажер",
        "intern"
    ]

    if not any(p in title for p in positive_keywords):
        return False

    if any(n in title for n in negative_keywords):
        return False

    return True


def salary_ok(salary: dict | None) -> bool:
    if not salary:
        return True

    values = [v for v in (salary.get("from"), salary.get("to")) if v]
    return not values or max(values) >= MIN_SALARY


# ================== HH API ==================

def fetch_hh_vacancies():
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": "аналитик",
        "area": 113,           # Россия
        "per_page": 50,
        "only_with_salary": False
    }

    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    data = r.json()

    vacancies = []

    for item in data.get("items", []):
        vacancies.append({
            "title": item["name"],
            "company": item["employer"]["name"],
            "rating": item["employer"].get("rating", "—"),
            "link": item["alternate_url"],
            "salary": item.get("salary"),
            "experience": item.get("experience", {}).get("name", "Не указан")
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
    cur = salary.get("currency", "RUR")

    if frm and to:
        return f"{frm}–{to} {cur}"
    if frm:
        return f"от {frm} {cur}"
    if to:
        return f"до {to} {cur}"

    return "ЗП не указана"


def format_message(v: dict) -> str:
    return (
        f"{v['title']}\n"
        f"{v['company']}\n"
        f"Формат: Удалённая работа\n"
        f"{format_salary(v['salary'])}\n"
        f"Опыт: {v['experience']}\n"
        f"Рейтинг компании: {v['rating']}\n"
        f"{v['link']}"
    )


async def check_and_send():
    vacancies = fetch_hh_vacancies()
    logging.info(f"HH returned {len(vacancies)} vacancies")

    for v in vacancies:
        if not is_target_analyst(v["title"]):
            continue
        if not salary_ok(v["salary"]):
            continue
        if v["link"] in sent_links:
            continue

        await bot.send_message(CHANNEL_ID, format_message(v))
        sent_links.add(v["link"])


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("🤖 Бот запущен. Ищу вакансии системного и продуктового аналитика.")


@dp.message_handler(commands=["check"])
async def manual_check(msg: types.Message):
    await msg.answer("🔍 Проверяю hh.ru …")
    await check_and_send()


# ================== АВТОПРОВЕРКА ==================

async def on_startup(dp):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_send, "interval", minutes=CHECK_INTERVAL_MINUTES)
    scheduler.start()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)



if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
