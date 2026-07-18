# -*- coding: utf-8 -*-
"""
Дозаполнение strategies для гексаграмм №43–64 из 64-strategemy-i-czin_polnyi.md.
Стиль полей — как у заполненных 1–42 (образец: ABBBAA).
Только комбинации №43–64; №1–42 не затрагиваются. Идемпотентно.
Также выравнивает названия 57/59 (в сиде были на перепутанных кодах).

Запуск: python /tmp/fill43.py /tmp/64s.md
"""
import asyncio, re, sys

from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models import Strategy
from app.hexagrams import HEXAGRAM_LIST

ASSM_FIELDS = [
    "assm_planning","assm_growth","assm_advertising","assm_feedback","assm_risk",
    "assm_product","assm_service","assm_startup","assm_investment","assm_contracts",
    "assm_sync","assm_creative","assm_interaction","assm_resources","assm_research",
    "assm_trade","assm_failures","assm_success",
]
VALID_STAGES = {"Зарождение","Расцвет","Зрелость","Обновление","Упадок"}
SCENARIO_BLANK = {"focus": "", "growth_strategy": "", "innovation_type": "",
                  "value_discipline": "", "innovation_strategy": "", "leadership_principles": ""}
NUM_TO_COMBO = {num: combo for num, _, combo in HEXAGRAM_LIST}
NUM_TO_NAME  = {num: name for num, name, _ in HEXAGRAM_LIST}


def parse(path: str) -> dict[int, dict]:
    src = open(path, encoding="utf-8").read()
    parts = re.split(r"\n## (\d+)\.\s+", src)
    out = {}
    for i in range(1, len(parts), 2):
        n = int(parts[i]); body = parts[i+1]

        def block(num: int, name: str) -> str:
            m = re.search(rf"\*\*{num}\. {name}\.\*\*\s*(.*?)(?=\n\*\*\d\.|\n---|\Z)", body, re.S)
            assert m, f"#{n}: нет блока {name}"
            return m.group(1).strip()

        strat = block(1, "Стратагема")
        stage = block(3, "Жизненный цикл").rstrip(".")
        assert stage in VALID_STAGES, f"#{n}: неизвестная стадия {stage!r}"
        scenario = block(4, "Сценарий для бизнеса")

        mk_raw = block(5, "Маркетинг")
        mk_lines = []
        for m in re.finditer(r"-\s*(Продукт|Цена|Каналы|Коммуникация):\s*(.+?)(?=\n-|\Z)", mk_raw, re.S):
            mk_lines.append(f"{m.group(1)}:\n{' '.join(m.group(2).split())}")
        assert len(mk_lines) == 4, f"#{n}: маркетинг {len(mk_lines)}/4"

        assm = {}
        for j in range(1, 19):
            m = re.search(rf"-\s*7\.{j}\.\s*(.+?)(?=\n-\s*7\.\d+\.|\n---|\Z)", body, re.S)
            assert m, f"#{n}: нет 7.{j}"
            assm[ASSM_FIELDS[j-1]] = " ".join(m.group(1).split())

        out[n] = {
            "stratagema_title": " ".join(strat.split()),
            "lifecycle_stage": stage,
            "scenario_text": " ".join(scenario.split()),
            "marketing_text": "\n".join(mk_lines),
            "management_text": " ".join(block(6, "Управление").split()),
            **assm,
        }
    assert set(out) == set(range(1, 65)), f"распарсено {len(out)}/64"
    return out


async def main():
    data = parse(sys.argv[1])
    async with AsyncSessionLocal() as session:
        # 1) выравнивание названий 57/59 (только если они на перепутанных кодах)
        s57 = await session.scalar(select(Strategy).where(Strategy.combination == NUM_TO_COMBO[57]))
        s59 = await session.scalar(select(Strategy).where(Strategy.combination == NUM_TO_COMBO[59]))
        if s57 and s59 and s57.title == NUM_TO_NAME[59] and s59.title == NUM_TO_NAME[57]:
            s57.title, s59.title = NUM_TO_NAME[57], NUM_TO_NAME[59]
            print(f"названия 57/59 выровнены: {NUM_TO_COMBO[57]}='{NUM_TO_NAME[57]}', {NUM_TO_COMBO[59]}='{NUM_TO_NAME[59]}'")

        updated = missing = 0
        for n in range(43, 65):
            combo = NUM_TO_COMBO[n]
            strat = await session.scalar(select(Strategy).where(Strategy.combination == combo))
            if strat is None:
                print(f"  ! #{n} {combo}: строки нет — пропуск"); missing += 1
                continue
            for field, value in data[n].items():
                setattr(strat, field, value)
            if not strat.scenario or not isinstance(strat.scenario, dict):
                strat.scenario = dict(SCENARIO_BLANK)
            updated += 1
            print(f"  #{n:2d} {combo} «{strat.title}» — {data[n]['lifecycle_stage']}")
        await session.commit()
        print(f"\nИтого: обновлено {updated}, отсутствует строк {missing}")

if __name__ == "__main__":
    asyncio.run(main())
