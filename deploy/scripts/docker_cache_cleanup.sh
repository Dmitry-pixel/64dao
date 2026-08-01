#!/bin/bash
LOG="/var/log/64dao-docker-cache.log"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"
docker builder prune -af --filter "until=72h" >> "$LOG" 2>&1
echo "" >> "$LOG"
