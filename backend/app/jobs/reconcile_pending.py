"""Досверка зависших заказов: оплата есть в банке, а у нас всё ещё pending.

Запуск (host cron, раз в час):
    docker compose exec -T backend python -m app.jobs.reconcile_pending

Зачем нужно, если вебхук и так приходит. Точка повторяет доставку 30 раз с
интервалом 10 секунд — это примерно пять минут. Если наш сервер в это окно
недоступен (деплой, перезапуск, сбой сети), повторы заканчиваются, и заказ
остаётся pending навсегда: деньги у банка списаны, доступ клиенту не выдан.
Кредиты считаются по оплаченным заказам (paid_credits), поэтому один
незакрытый статус — это ровно один неоткрытый отчёт.

Ручная сверка для этого есть — POST /api/payments/admin/reconcile, — но она
требует, чтобы кто-то заметил проблему и нажал кнопку. На практике замечает
клиент.

Отличия от ручной сверки, намеренные:

1. Берём только pending и только в окне [STALE_MINUTES, MAX_AGE_DAYS].
   Ручная сверка проходит по всем pending и paid без ограничения по времени:
   для кнопки это нормально, для ежечасной задачи — тысячи запросов к банку
   на ровном месте.
2. Возвраты не трогаем. Заказ в pending с возвратом в банке — случай редкий
   и неоднозначный, у ручной сверки он разобран вместе с paid. Здесь важно
   одно: не потерять оплату.

Окно настраивается переменными окружения:
  RECONCILE_STALE_MINUTES (по умолчанию 15) — раньше этого срока заказ ещё
    может закрыться штатным вебхуком, дёргать банк рано;
  RECONCILE_MAX_AGE_DAYS (по умолчанию 7) — дальше этой границы pending
    почти всегда брошенная корзина, а не потерянная оплата.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Order
from app.tochka_client import extract_operation, get_tochka_client

logger = logging.getLogger(__name__)

STALE_MINUTES = int(os.environ.get("RECONCILE_STALE_MINUTES", "15"))
MAX_AGE_DAYS = int(os.environ.get("RECONCILE_MAX_AGE_DAYS", "7"))

FAILED_STATUSES = {"REJECTED", "DECLINED"}


async def reconcile_pending(session) -> dict:
    """Сверяет зависшие pending-заказы с банком. Возвращает счётчики."""
    now = datetime.now(UTC)
    rows = (await session.execute(
        select(Order).where(
            Order.status == "pending",
            Order.tochka_operation_id.is_not(None),
            Order.created_at < now - timedelta(minutes=STALE_MINUTES),
            Order.created_at > now - timedelta(days=MAX_AGE_DAYS),
        )
    )).scalars().all()

    client = get_tochka_client()
    marked_paid = marked_failed = errors = 0

    for order in rows:
        try:
            resp = await client.get_payment_status(order.tochka_operation_id)
        except Exception:
            # Один недоступный заказ не должен уносить с собой остальные:
            # следующий запуск через час попробует снова.
            logger.exception("reconcile_pending: нет статуса операции %s (заказ %s)",
                             order.tochka_operation_id, order.id)
            errors += 1
            continue

        remote_status = str(extract_operation(resp).get("status") or "").upper()
        if remote_status == "APPROVED":
            order.status = "paid"
            order.paid_at = now
            marked_paid += 1
            # Движение денег — обязательно след в логах: таблица orders
            # хранит только итоговый статус и не помнит, кто его поставил.
            logger.warning("reconcile_pending: заказ %s подтверждён банком, "
                           "вебхук не дошёл (операция %s)", order.id,
                           order.tochka_operation_id)
        elif remote_status in FAILED_STATUSES:
            order.status = "failed"
            marked_failed += 1

    await session.commit()
    return {"checked": len(rows), "marked_paid": marked_paid,
            "marked_failed": marked_failed, "errors": errors}


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    async with AsyncSessionLocal() as session:
        stats = await reconcile_pending(session)
    logger.info("reconcile_pending done: checked=%d paid=%d failed=%d errors=%d",
                stats["checked"], stats["marked_paid"],
                stats["marked_failed"], stats["errors"])


if __name__ == "__main__":
    asyncio.run(main())
