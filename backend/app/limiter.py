from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_ip(request) -> str:
    """Настоящий IP клиента за nginx.

    nginx (/api) ставит X-Real-IP = $remote_addr, снаружи его подделать нельзя
    (клиентский заголовок перезатирается прокси). Без этого slowapi ключевался
    бы по request.client.host = IP nginx (127.0.0.1) и лимит становился бы
    ГЛОБАЛЬНЫМ на весь сайт: один актор мог исчерпать 5/мин и заблокировать
    вход всем. Fallback на get_remote_address — для локального запуска без прокси.
    """
    return request.headers.get("x-real-ip") or get_remote_address(request)


limiter = Limiter(key_func=_client_ip)
