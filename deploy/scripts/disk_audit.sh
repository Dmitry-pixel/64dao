#!/usr/bin/env bash
# 64dao.ru — аудит диска. ТОЛЬКО ЧТЕНИЕ: скрипт ничего не удаляет и не изменяет.
# Запуск: bash /root/disk_audit.sh 2>&1 | tee /root/disk_audit_report.txt

export LC_NUMERIC=C
renice -n 19 -p $$ >/dev/null 2>&1
ionice -c3 -p $$ >/dev/null 2>&1
AUTO=0
PROJ=/var/www/64dao

H(){ printf '\n\n########## %s ##########\n' "$1"; }
hr(){ numfmt --to=iec --suffix=B "${1:-0}" 2>/dev/null || echo "${1}B"; }
total(){ awk '{s+=$1} END{print s+0}'; }
bytes(){ du -sb "$@" 2>/dev/null | total; }
# R <метка> <байты> <объект> [комментарий]; метка АВТО суммируется в итог
R(){ [ "$1" = "АВТО" ] && AUTO=$((AUTO+$2)); printf '%9s  %-55s [%s] %s\n' "$(hr "$2")" "$3" "$1" "$4"; }
P(){ [ -e "$2" ] || return 0; R "$1" "$(bytes "$2")" "$2" "$3"; }
# фильтр строк "размер<TAB>путь": исключает системные ФС, docker и доп. пути
flt(){ awk -F'\t' -v ex="^/(proc|sys|dev|run|snap|var/lib/docker${1:+|$1})(/|\$)" '$2 !~ ex'; }

H "0. ОБЗОР"
df -h /
echo; echo "Топ каталогов в /:"
du -xh --max-depth=1 / 2>/dev/null | sort -rh | head -n 12
echo; echo "Топ каталогов в /var:"
du -xh --max-depth=1 /var 2>/dev/null | sort -rh | head -n 10

H "1. DOCKER"
if command -v docker >/dev/null 2>&1; then
  docker system df
  echo
  docker system df --format '{{.Type}}|{{.Reclaimable}}' | while IFS='|' read -r t r; do
    [ "$t" = "Build Cache" ] && printf '%9s  %-55s [АВТО] %s\n' "${r%% *}" "docker build cache" "docker builder prune -f (cron вс 05:00)"
  done
  echo; echo "--- Образы ---"
  USED=$(docker ps -aq | xargs -r docker inspect --format '{{.Image}}' 2>/dev/null | sort -u)
  while IFS='|' read -r id name size age; do
    if grep -q "$id" <<<"$USED"; then t="НЕ ТРОГАТЬ"; c="используется контейнером"
    elif [ "$name" = "<none>:<none>" ]; then t="АВТО"; c="dangling, $age"
    else t="ПРОВЕРКА"; c="ни один контейнер не использует, $age"; fi
    printf '%9s  %-55s [%s] %s\n' "$size" "$name" "$t" "$c"
  done < <(docker images --no-trunc --format '{{.ID}}|{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}')

  echo; echo "--- Остановленные контейнеры ---"
  docker ps -a -s -f status=exited -f status=created --format '{{.Size}}|{{.Names}}|{{.Status}}' |
    while IFS='|' read -r s n st; do printf '%9s  %-55s [ПРОВЕРКА] %s\n' "${s%% *}" "container:$n" "$st"; done

  echo; echo "--- Тома ---"
  DANG=$(docker volume ls -qf dangling=true)
  for v in $(docker volume ls -q); do
    mp=$(docker volume inspect -f '{{.Mountpoint}}' "$v")
    if grep -qx "$v" <<<"$DANG"; then R "ПРОВЕРКА" "$(bytes "$mp")" "volume:$v" "не подключён ни к одному контейнеру"
    else R "НЕ ТРОГАТЬ" "$(bytes "$mp")" "volume:$v" "используется"; fi
  done

  echo; echo "--- Логи контейнеров ---"
  for f in /var/lib/docker/containers/*/*-json.log; do
    [ -f "$f" ] || continue
    cid=$(basename "$(dirname "$f")"); n=$(docker inspect -f '{{.Name}}' "$cid" 2>/dev/null)
    b=$(stat -c %s "$f")
    if [ "$b" -gt 104857600 ]; then R "ПРОВЕРКА" "$b" "log:${n#/}" "крупный: нужна ротация (max-size), не удаление"
    else R "НЕ ТРОГАТЬ" "$b" "log:${n#/}" ""; fi
  done
else
  echo "docker не найден"
fi

H "2. СИСТЕМНЫЕ ЛОГИ"
P "АВТО(частично)" /var/log/journal "journalctl --vacuum-time=14d"
b=$(find /var/log -type f \( -name '*.gz' -o -name '*.[0-9]' -o -name '*.old' -o -name '*.[0-9].log' \) -printf '%s\n' 2>/dev/null | total)
R "АВТО" "$b" "/var/log: *.gz, *.1, *.old" "архивы ротации"
echo "Крупнейшие активные логи (>20 МБ):"
while IFS=$'\t' read -r b p; do
  case "$p" in *fastpanel2.access.log) c="читается монитором 5xx — только ротация";; *) c="ротация, не удаление";; esac
  R "ПРОВЕРКА" "$b" "$p" "$c"
done < <(find /var/log -type f ! -name '*.gz' ! -name '*.[0-9]' -size +20M -printf '%s\t%p\n' 2>/dev/null | sort -rn | head -n 10)

H "3. КЭШИ ПАКЕТОВ И ИНСТРУМЕНТОВ"
P "АВТО" /var/cache/apt/archives "apt-get clean"
for d in /root/.cache/pip /root/.npm /root/.cache/yarn /root/.cache/node-gyp /root/.cache/go-build /root/.cache/ms-playwright; do
  P "АВТО" "$d" "кэш, восстанавливается сам"
done
for d in /home/*/.cache /home/*/.npm; do P "ПРОВЕРКА" "$d" "кэш пользователя"; done
echo "Отключённые ревизии snap:"
snap list --all 2>/dev/null | awk '/disabled/{print "   [АВТО] "$1" rev "$3}'
echo "apt autoremove (симуляция, пакеты-сироты):"
apt-get -s autoremove 2>/dev/null | awk '/^Remv/{print "   [ПРОВЕРКА] "$2}'
echo "Ядра: текущее $(uname -r); установлены:"
dpkg -l 'linux-image-[0-9]*' 2>/dev/null | awk '/^ii/{print "   "$2}'

H "4. БЭКАПЫ"
B=/var/backups/64dao
if [ -d "$B" ]; then
  R "НЕ ТРОГАТЬ" "$(bytes "$B")" "$B" "$(find "$B" -type f | wc -l) файлов, ротация 30 дн."
  read -r n s < <(find "$B" -type f -mtime +35 -printf '%s\n' | awk '{s+=$1;n++} END{print n+0, s+0}')
  [ "$n" -gt 0 ] && R "ПРОВЕРКА" "$s" "$B: старше 35 дн. ($n шт.)" "ротация не срабатывает?"
fi
P "АВТО" /root/backups "ранее определено как устаревшее"
P "АВТО" /root/backup_64dao.sh "ранее определено как устаревшее"
echo "Прочие дампы/бэкапы >10 МБ:"
find / -xdev -type f -size +10M \( -iname '*.sql' -o -iname '*.sql.gz' -o -iname '*.dump' -o -iname '*.bak' -o -iname '*backup*' \) -printf '%s\t%p\n' 2>/dev/null |
  flt 'var/backups/64dao|root/backups' | sort -rn | head -n 20 |
  while IFS=$'\t' read -r b p; do R "ПРОВЕРКА" "$b" "$p" ""; done

H "5. ПРОЕКТ $PROJ (хост)"
du -h --max-depth=2 "$PROJ" 2>/dev/null | sort -rh | head -n 15
echo
b=$(find "$PROJ" -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec du -sb {} + 2>/dev/null | total)
R "АВТО" "$b" "$PROJ/**/__pycache__, .pytest_cache" "кэш Python на хосте"
while IFS= read -r d; do
  P "ПРОВЕРКА" "$d" "артефакт сборки на хосте; образы собираются в Docker"
done < <(find "$PROJ" -type d \( -name node_modules -o -name .next \) -prune -print 2>/dev/null)
P "ПРОВЕРКА" "$PROJ/uploads" "backend его не читает (данные в volume dao64_uploads)"
P "НЕ ТРОГАТЬ" "$PROJ/.git" "история репозитория"

H "6. УСТАНОВЩИКИ И АРХИВЫ (>5 МБ)"
find / -xdev -type f -size +5M \( -iname '*.deb' -o -iname '*.rpm' -o -iname '*.iso' -o -iname '*.run' -o -iname '*.AppImage' -o -iname '*.tar' -o -iname '*.tar.gz' -o -iname '*.tgz' -o -iname '*.tar.xz' -o -iname '*.tar.bz2' -o -iname '*.zip' -o -iname '*.7z' -o -iname '*.rar' \) -printf '%s\t%p\n' 2>/dev/null |
  flt 'var/backups/64dao|var/cache/apt|usr' | sort -rn | head -n 30 |
  while IFS=$'\t' read -r b p; do R "ПРОВЕРКА" "$b" "$p" ""; done

H "7. КРУПНЫЕ ФАЙЛЫ (>100 МБ, без Docker)"
find / -xdev -type f -size +100M -printf '%s\t%p\n' 2>/dev/null | flt 'usr' | sort -rn | head -n 25 |
  while IFS=$'\t' read -r b p; do
    case "$p" in
      /swap*|*.swap) t="НЕ ТРОГАТЬ"; c="swap";;
      /var/backups/64dao/*) t="НЕ ТРОГАТЬ"; c="актуальный бэкап";;
      *) t="ПРОВЕРКА"; c="";;
    esac
    R "$t" "$b" "$p" "$c"
  done

H "8. ВРЕМЕННЫЕ ФАЙЛЫ И ДАМПЫ ПАДЕНИЙ"
b=$(find /tmp /var/tmp -xdev -type f -mtime +7 -printf '%s\n' 2>/dev/null | total)
R "АВТО" "$b" "/tmp, /var/tmp (старше 7 дн.)" ""
P "АВТО" /var/crash "отчёты о падениях"
b=$(find / -xdev -type f \( -name core -o -name 'core.[0-9]*' \) -printf '%s\t%p\n' 2>/dev/null | flt | cut -f1 | total)
[ "$b" -gt 0 ] && R "ПРОВЕРКА" "$b" "core dumps" ""

H "9. ВОЗМОЖНО ЗАБРОШЕННЫЕ ПРОЕКТЫ И ПРИЛОЖЕНИЯ"
echo "Каталоги >10 МБ без изменений более 90 дней:"
now=$(date +%s)
for d in /var/www/* /var/www/*/data/www/* /root/* /home/* /home/*/* /opt/* /srv/*; do
  [ -d "$d" ] || continue
  case "$d" in "$PROJ"|"$PROJ"/*|/root/snap) continue;; esac
  b=$(bytes "$d"); [ "$b" -lt 10485760 ] && continue
  last=$(find "$d" -xdev -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -n 1); last=${last%.*}
  [ -z "$last" ] && continue
  age=$(( (now - last) / 86400 ))
  [ "$age" -gt 90 ] && R "ПРОВЕРКА" "$b" "$d" "последнее изменение $age дн. назад"
done
echo; echo "Git-репозитории вне $PROJ:"
find / -xdev -type d -name .git -prune -printf '0\t%h\n' 2>/dev/null | flt "${PROJ#/}" | cut -f2 |
  while IFS= read -r d; do P "ПРОВЕРКА" "$d" "другой проект"; done
echo; echo "Крупнейшие установленные пакеты:"
dpkg-query -Wf '${Installed-Size}\t${Package}\n' 2>/dev/null | sort -rn | head -n 12 |
  while IFS=$'\t' read -r k p; do R "ИНФО" "$((k*1024))" "pkg:$p" ""; done
echo; echo "Запущенные сервисы (для поиска лишнего ПО):"
systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null | awk '{print "   "$1}'

H "ИТОГ"
echo "Файловые объекты с меткой [АВТО]: $(hr "$AUTO")"
echo "Плюс Docker build cache и dangling-образы — колонка RECLAIMABLE в разделе 1."
echo "[АВТО] — можно чистить без анализа | [ПРОВЕРКА] — нужно ваше решение"
echo "[НЕ ТРОГАТЬ] — рабочие данные | [ИНФО] — справочно"
echo "Ничего не удалено."
