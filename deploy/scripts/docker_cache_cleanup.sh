#!/bin/bash
LOG="/root/docker_cache_cleanup.log"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"
docker builder prune -af --filter "until=168h" >> "$LOG" 2>&1
echo "" >> "$LOG"
