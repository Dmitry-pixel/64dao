-- Инициализация PostgreSQL при первом запуске Docker-контейнера
-- Выполняется автоматически через /docker-entrypoint-initdb.d/

-- Расширения необходимые для работы
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- gen_random_uuid() fallback
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- полнотекстовый поиск (на будущее)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- криптографические функции

-- Права на схему
GRANT ALL PRIVILEGES ON SCHEMA public TO dao64;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dao64;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dao64;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO dao64;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO dao64;
