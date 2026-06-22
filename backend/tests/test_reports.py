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
