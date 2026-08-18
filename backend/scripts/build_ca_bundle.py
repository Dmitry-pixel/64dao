"""Собирает CA-бандл для вызовов к API Точки: certifi + сертификаты НУЦ Минцифры.

Почему не `cat`: файлы с gu-st.ru приходят с CRLF и БЕЗ завершающего перевода
строки. При простой конкатенации последняя строка одного файла склеивается
с первой строкой следующего:

    -----END CERTIFICATE----------BEGIN CERTIFICATE-----

и OpenSSL валит весь бандл с `[X509] PEM lib`. Воспроизведено на сборке
2026-08-18: certifi парсился, бандл — нет.

Скрипт вырезает блоки BEGIN..END регуляркой, нормализует переводы строк и
ПРОВЕРЯЕТ результат загрузкой в ssl. Битый бандл роняет сборку образа, а не
доезжает до рантайма.
"""
import pathlib
import re
import ssl
import sys

import certifi

SRC_DIR = pathlib.Path("/usr/local/share/ca-certificates/russian-trusted")
OUT = pathlib.Path("/etc/ssl/tochka/tochka-ca-bundle.pem")
BLOCK = re.compile(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S)


def blocks_of(path: pathlib.Path) -> list[bytes]:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    found = BLOCK.findall(raw)
    if not found:
        sys.exit(f"СБОРКА ПРЕРВАНА: в {path} нет ни одного PEM-блока")
    return found


certifi_blocks = blocks_of(pathlib.Path(certifi.where()))
if len(certifi_blocks) < 100:
    sys.exit(f"СБОРКА ПРЕРВАНА: в certifi только {len(certifi_blocks)} сертификатов")

russian_files = sorted(SRC_DIR.glob("*.crt"))
if len(russian_files) != 2:
    sys.exit(f"СБОРКА ПРЕРВАНА: ожидалось 2 файла в {SRC_DIR}, найдено {len(russian_files)}")

russian_blocks = [b for f in russian_files for b in blocks_of(f)]
if len(russian_blocks) != 2:
    sys.exit(f"СБОРКА ПРЕРВАНА: ожидалось 2 сертификата Минцифры, найдено {len(russian_blocks)}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(b"\n".join(certifi_blocks + russian_blocks) + b"\n")

# Настоящая проверка: пустой контекст без системных корней, чтобы считать
# ровно то, что мы записали.
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.load_verify_locations(str(OUT))
loaded = ctx.get_ca_certs()

print(f"certifi: {len(certifi_blocks)}, Минцифры: {len(russian_blocks)}")
print(f"бандл: {OUT} ({OUT.stat().st_size} байт), загружено корней: {len(loaded)}")
