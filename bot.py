import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================== НАСТРОЙКИ ==================

# // ВСТАВЬ СЮДА ТОКЕН БОТА (Railway → Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# // ВСТАВЬ СЮДА TG-КАНАЛ
CHANNEL_ID = "@tgsdsa"  # например "@my_channel" или -1001234567890

CHECK_INTERVAL_HOURS = 3
MIN_SALARY = 150_000

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway → Variables")

sent_links = set()

# ================== ФИЛЬТРЫ ==================

def parse_salary(text):
    if not text:
        return None
    nums = re.findall(r"\d+", text.replace(" ", ""))
    return max(map(int, nums)) if nums else None


def salary_ok(text):
    salary = parse_salary(text)
    return salary is None or salary >= MIN_SALARY


def is_sys_analyst(title):
    title = title.lower()
    return "системный аналитик" in title or "system analyst" in title


# ================== ПАРСЕР ==================

def fetch_vacancies():
    url = "https://career.habr.com/vacancies"
    params = {"q": "системный аналитик", "remote": "true"}
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, params=params, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    vacancies = []

    for card in soup.select(".vacancy-card"):
        try:
            title = card.select_one(".vacancy-card__title").text.strip()
            link = "https://career.habr.com" + card.select_one("a")["href"]
            company = card.select_one(".vacancy-card__company-title").text.strip()
            salary_el = card.select_one(".vacancy-card__salary")
            salary = salary_el.text.strip() if salary_el else None

            vacancies.append({
                "title": title,
                "company": company,
                "link": link,
                "salary": salary,
                "rating": "—"
            })
        except Exception:
            continue

    return vacancies


# ================== TELEGRAM ==================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


def format_message(v):
    return (
        f"{v['title']}\n"
        f"{v['company']}\n"
        f"{v['link']}\n"
        f"{v['salary'] or 'ЗП не указана'}\n"
        f"Рейтинг компании: {v['rating']}"
    )


async def check_and_send():
    for v in fetch_vacancies():
        if not is_sys_analyst(v["title"]):
            continue
        if not salary_ok(v["salary"]):
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
    await msg.answer("🔍 Проверяю вакансии...")
    await check_and_send()


# ================== АВТОПРОВЕРКА ==================

async def on_startup(dp):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_send, "interval", hours=CHECK_INTERVAL_HOURS)
    scheduler.start()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
