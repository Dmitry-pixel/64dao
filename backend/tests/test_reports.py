"""
test_reports.py — regression-тесты роутера /api/reports.

download_report отдаёт реальный файл с диска (FileResponse) — для теста
успешного скачивания создаём настоящий маленький файл во временной
директории контейнера, а не мокаем FileResponse (это сама суть эндпоинта).
"""
import uuid

import pytest

from app.models import Assessment, Report


VALID_COMBINATION = "AABABA"


@pytest.fixture
def tmp_pdf_path(tmp_path):
    """Реальный файл на диске контейнера — имитирует сгенерированный PDF."""
    pdf_file = tmp_path / "test-report.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake content for test")
    return str(pdf_file)


@pytest.mark.asyncio
async def test_download_report_owner_succeeds(auth_client, db_session, test_user, tmp_pdf_path):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    report = Report(
        assessment_id=assessment.id,
        user_id=test_user.id,
        pdf_path=tmp_pdf_path,
        pdf_filename="my-report.pdf",
    )
    db_session.add(report)
    await db_session.flush()

    resp = await auth_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "my-report.pdf" in resp.headers["content-disposition"]
    assert resp.content == b"%PDF-1.4 fake content for test"


@pytest.mark.asyncio
async def test_download_report_admin_can_access_any(admin_client, db_session, test_user, tmp_pdf_path):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    report = Report(
        assessment_id=assessment.id,
        user_id=test_user.id,
        pdf_path=tmp_pdf_path,
        pdf_filename="my-report.pdf",
    )
    db_session.add(report)
    await db_session.flush()

    resp = await admin_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_download_report_other_user_forbidden(auth_client, db_session, test_admin, tmp_pdf_path):
    assessment = Assessment(user_id=test_admin.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    report = Report(
        assessment_id=assessment.id,
        user_id=test_admin.id,
        pdf_path=tmp_pdf_path,
        pdf_filename="my-report.pdf",
    )
    db_session.add(report)
    await db_session.flush()

    resp = await auth_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_download_report_not_found_404(auth_client):
    resp = await auth_client.get(f"/api/reports/{uuid.uuid4()}/download")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_report_without_auth_401(client):
    resp = await client.get(f"/api/reports/{uuid.uuid4()}/download")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_download_report_no_pdf_path_404(auth_client, db_session, test_user):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    report = Report(
        assessment_id=assessment.id,
        user_id=test_user.id,
        pdf_path=None,
        pdf_filename=None,
    )
    db_session.add(report)
    await db_session.flush()

    resp = await auth_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_report_file_missing_on_disk_404(auth_client, db_session, test_user):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    report = Report(
        assessment_id=assessment.id,
        user_id=test_user.id,
        pdf_path="/nonexistent/path/report.pdf",
        pdf_filename="report.pdf",
    )
    db_session.add(report)
    await db_session.flush()

    resp = await auth_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_report_filename_fallback_when_none(auth_client, db_session, test_user, tmp_pdf_path):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION, status="completed")
    db_session.add(assessment)
    await db_session.flush()

    report = Report(
        assessment_id=assessment.id,
        user_id=test_user.id,
        pdf_path=tmp_pdf_path,
        pdf_filename=None,
    )
    db_session.add(report)
    await db_session.flush()

    resp = await auth_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 200
    assert f"report-{report.id}.pdf" in resp.headers["content-disposition"]


# ── PDF не хранится ───────────────────────────────────────────────────────────
# Отчёт собирается заново на каждое скачивание, поэтому копия на диске никому
# не нужна и только копится. Проверяем, что после отдачи файла не остаётся.

@pytest.fixture
def regenerate_on(monkeypatch):
    """Боевой режим: пересборка при скачивании. В тестах по умолчанию выключена,
    иначе каждый вызов поднимает Chromium."""
    import app.routers.reports as reports_router

    monkeypatch.setattr(reports_router.settings, "regenerate_pdf_on_download", True)


@pytest.fixture
def fake_pdf_generator(monkeypatch):
    """Подменяет генерацию: пишет файл-заглушку и запоминает путь.

    Настоящий Playwright здесь не нужен — проверяется судьба файла, а не его
    содержимое.
    """
    from pathlib import Path
    import app.routers.reports as reports_router

    written: list[Path] = []

    async def _fake(html, output_path):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4 generated")
        written.append(path)

    monkeypatch.setattr(reports_router, "generate_pdf", _fake)
    return written


@pytest.mark.asyncio
async def test_regenerated_pdf_is_removed_after_download(
    auth_client, db_session, test_user, regenerate_on, fake_pdf_generator,
):
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION,
                            status="completed")
    db_session.add(assessment)
    await db_session.flush()
    report = Report(assessment_id=assessment.id, user_id=test_user.id,
                    pdf_path=None, pdf_filename="my-report.pdf")
    db_session.add(report)
    await db_session.flush()

    resp = await auth_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 generated"

    assert len(fake_pdf_generator) == 1
    assert not fake_pdf_generator[0].exists(), "временный PDF должен удаляться после отдачи"


@pytest.mark.asyncio
async def test_regenerated_pdf_does_not_touch_uploads(
    auth_client, db_session, test_user, regenerate_on, fake_pdf_generator,
):
    """Файл пишется во временный каталог, а не в uploads: там он пережил бы
    и запрос, и перезапуск."""
    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION,
                            status="completed")
    db_session.add(assessment)
    await db_session.flush()
    report = Report(assessment_id=assessment.id, user_id=test_user.id,
                    pdf_path=None, pdf_filename="r.pdf")
    db_session.add(report)
    await db_session.flush()

    await auth_client.get(f"/api/reports/{report.id}/download")

    import app.routers.reports as reports_router
    uploads = str(reports_router.settings.uploads_dir)
    assert uploads not in str(fake_pdf_generator[0])


@pytest.mark.asyncio
async def test_stored_file_is_kept_when_regeneration_is_off(
    auth_client, db_session, test_user, tmp_pdf_path,
):
    """Выключенная пересборка — прежнее поведение: отдаём сохранённый файл и
    не удаляем его. На этом режиме держатся тесты и запасной путь на проде."""
    from pathlib import Path

    assessment = Assessment(user_id=test_user.id, method1_combination=VALID_COMBINATION,
                            status="completed")
    db_session.add(assessment)
    await db_session.flush()
    report = Report(assessment_id=assessment.id, user_id=test_user.id,
                    pdf_path=tmp_pdf_path, pdf_filename="kept.pdf")
    db_session.add(report)
    await db_session.flush()

    resp = await auth_client.get(f"/api/reports/{report.id}/download")
    assert resp.status_code == 200
    assert Path(tmp_pdf_path).exists(), "сохранённый файл удалять нельзя"
