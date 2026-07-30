# -*- coding: utf-8 -*-
"""
Единый источник шаблонов писем: дефолты, чтение, запись, подстановка.

Раньше DEFAULT_TEMPLATES лежал двумя копиями (app/email.py и
routers/admin.py) и они успели разойтись: в админской версии было поле
description, в почтовой нет. Правило проекта запрещает дублировать дефолты
настроек, поэтому единственное определение теперь здесь.

Хранилище: JSON в volume dao64_uploads. Путь резолвится через UPLOAD_DIR,
как в contour_settings.py, иначе тесты пишут в боевой том.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.config import get_settings

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/var/www/64dao/uploads")
TEMPLATES_FILE = Path(UPLOAD_DIR) / "email_templates.json"

DEFAULT_TEMPLATES: dict[str, dict] = {
    "access_grant": {
        "subject": "Вам открыт тестовый доступ к диагностике 64 ДАО",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Вам открыт доступ к стратегической диагностике <b>64 ДАО</b> "
            "без оплаты: <b>{quota}</b> диагностик(и). Доступ действует до "
            "<b>{expires_at}</b> включительно.</p>"
            "<p style=\"margin:24px 0;\">"
            "<a href=\"{app_url}/assessment\" style=\"background:#1a2540;color:#fff;"
            "padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;\">"
            "Пройти диагностику</a></p>"
            "<p>Отчёт формируется сразу после прохождения и остаётся в личном "
            "кабинете — его можно скачать в PDF в любой момент.</p>"
            "<p>Вопросы по методике: <a href=\"mailto:support@64dao.ru\">support@64dao.ru</a></p>"
            "<p style=\"color:#999;font-size:12px;\">Команда 64 ДАО</p>"
        ),
        "description": (
            "Отправляется при выдаче временного бесплатного доступа из админки "
            "(карточка пользователя или раздел «Тестовый доступ»). Переменные: "
            "{name} — имя, {name_part} — оборот «, Имя» или пусто, {quota} — "
            "число диагностик, {expires_at} — дата окончания в формате дд.мм.гггг, "
            "{app_url} — адрес сайта."
        ),
    },
    "account_deactivated": {
        "subject": "Доступ к 64 ДАО приостановлен",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Доступ к вашему личному кабинету <b>64 ДАО</b> приостановлен администратором.</p>"
            "<p>По всем вопросам обращайтесь: <a href=\"mailto:support@64dao.ru\">support@64dao.ru</a></p>"
        ),
        "description": "Отправляется при блокировке пользователя администратором. Переменные: {name} — имя.",
    },
    "account_activated": {
        "subject": "Доступ к 64 ДАО восстановлен",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Доступ к вашему личному кабинету <b>64 ДАО</b> восстановлен.</p>"
            "<p><a href=\"https://64dao.ru/login\">Войти в кабинет</a></p>"
        ),
        "description": "Отправляется при разблокировке пользователя. Переменные: {name} — имя.",
    },
    "otp": {
        "subject": "{code} — код входа в 64DAO",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Ваш код для входа в систему <b>64DAO</b>:</p>"
            "<p style=\"font-size:28px;font-weight:700;letter-spacing:6px;color:#1a2540;\">{code}</p>"
            "<p>Код действует <b>10 минут</b>. Не передавайте его никому.</p>"
            "<p style=\"color:#999;font-size:12px;\">Если вы не запрашивали код — просто проигнорируйте это письмо.</p>"
        ),
        "description": "Отправляется при входе и регистрации. Доступные переменные: {name} — имя, {code} — код OTP.",
    },
    "welcome": {
        "subject": "Добро пожаловать в 64DAO",
        "body_html": (
            "<p>Добро пожаловать{name_part}!</p>"
            "<p>Вы успешно зарегистрировались в системе стратегической диагностики <b>64DAO</b>.</p>"
            "<p>Вы можете войти в свой кабинет и начать первую диагностику.</p>"
            "<p style=\"color:#999;font-size:12px;\">Команда 64DAO</p>"
        ),
        "description": "Отправляется один раз при регистрации. Доступные переменные: {name} — имя пользователя.",
    },
    "forgot_password": {
        "subject": "Сброс пароля 64DAO",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Мы получили запрос на сброс пароля для вашей учётной записи.</p>"
            "<p style=\"margin:24px 0;\">"
            "<a href=\"{reset_link}\" style=\"background:#1a2540;color:#fff;padding:12px 24px;"
            "border-radius:6px;text-decoration:none;font-weight:600;\">Сбросить пароль</a>"
            "</p>"
            "<p>Или скопируйте ссылку в браузер:<br>"
            "<span style=\"color:#1e3a8a;font-size:13px;\">{reset_link}</span></p>"
            "<p>Ссылка действует <b>1 час</b>.</p>"
            "<p style=\"color:#999;font-size:12px;\">Если вы не запрашивали сброс пароля — просто проигнорируйте это письмо.</p>"
        ),
        "description": "Отправляется при запросе сброса пароля. Доступные переменные: {name}, {name_part}, {reset_link} — ссылка на форму сброса.",
    },
    "repeat_diagnostic": {
        "subject": "Пора обновить стратегическую диагностику",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>С последней диагностики{company_part} прошло около {days_since} дн. "
            "Регулярная переоценка помогает вовремя увидеть смену фазы жизненного "
            "цикла и скорректировать стратегию.</p>"
            "<p>Повторная диагностика идёт по той же сетке вопросов: в отчёте будет "
            "виден сдвиг, а не новое мнение.</p>"
            "<p><a href=\"{app_url}/companies\">Запустить повторную диагностику</a></p>"
        ),
        "description": (
            "Отправляется через N дней после последней диагностики компании. "
            "Включение и периодичность — на странице «Рассылка». Переменные: "
            "{name}, {name_part}, {company} — название компании, {company_part} — "
            "готовый оборот « компании «Х»» или пусто, {days_since} — дней с "
            "последней диагностики, {app_url} — адрес сайта."
        ),
    },
}


def read_templates() -> dict:
    """Сохранённые значения поверх дефолтов.

    Мердж, а не замена: новый шаблон появляется в админке сразу после
    деплоя, не дожидаясь пересохранения файла. Описание всегда берётся из
    кода: это документация для администратора, её не редактируют.
    """
    result = {k: dict(v) for k, v in DEFAULT_TEMPLATES.items()}
    try:
        saved = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return result
    if not isinstance(saved, dict):
        return result
    for key, tpl in saved.items():
        if not isinstance(tpl, dict):
            continue
        merged = dict(result.get(key, {}))
        merged.update(tpl)
        if key in DEFAULT_TEMPLATES:
            merged["description"] = DEFAULT_TEMPLATES[key].get("description", "")
        result[key] = merged
    return result


def write_templates(data: dict) -> None:
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def render(key: str, variables: dict) -> tuple[str, str]:
    """(subject, body_html) с подставленными переменными."""
    tpl = read_templates().get(key, DEFAULT_TEMPLATES.get(key, {}))
    subject = tpl.get("subject", "")
    body = tpl.get("body_html", "")
    for name, val in variables.items():
        token = "{" + name + "}"
        subject = subject.replace(token, str(val))
        body = body.replace(token, str(val))
    return subject, body


# ── Отправитель письма ──────────────────────────────────────────────────────
# Провайдер разрешает ставить в From только адреса, которыми реально владеет
# домен и которые допускает его политика. Список задаётся в .env, а не в
# админке: иначе через интерфейс можно было бы подставить чужой адрес.

def default_sender() -> str:
    return get_settings().smtp_from_address


def allowed_senders() -> list[str]:
    raw = os.getenv("SMTP_SENDERS", "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    base = default_sender()
    if base not in items:
        items.insert(0, base)
    return items


def sender(key: str) -> str:
    """Адрес для шаблона. Неизвестный адрес молча откатывается на умолчание."""
    tpl = read_templates().get(key) or {}
    value = (tpl.get("from_address") or "").strip()
    return value if value in allowed_senders() else default_sender()
