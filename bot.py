import os
import re
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

CHECK_INTERVAL_HOURS = 1
MIN_SALARY = 150_000

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway → Variables")

sent_links = set()

# ================== ФИЛЬТРЫ ==================

def parse_salary_from_hh(salary: dict | None) -> int | None:
    """
    HH salary format:
    { "from": 150000, "to": 250000, "currency": "RUR" }
    """
    if not salary:
        return None

    values = [v for v in [salary.get("from"), salary.get("to")] if v]
    return max(values) if values else None


def salary_ok(salary_dict: dict | None) -> bool:
    salary = parse_salary_from_hh(salary_dict)
    return salary is None or salary >= MIN_SALARY


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


# ================== HH ПАРСЕР ==================

def fetch_hh_vacancies():
    url = "https://api.hh.ru/vacancies"
    para
