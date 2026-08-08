#!/bin/bash
# ==============================================================
# PostgreSQL 定时备份脚本
#
# 使用步骤：
# 1. 把这个文件放到服务器项目目录下，例如 /root/b2b-leads-system/deploy/backup.sh
# 2. 赋予执行权限：chmod +x deploy/backup.sh
# 3. 手动跑一次测试：./deploy/backup.sh
# 4. 确认能生成备份文件后，加入 crontab 定时任务（见文件末尾说明）
# ==============================================================

set -e  # 出错立即退出，不要在数据库异常时误以为备份成功

# ---- 配置区（按需修改） ----
PROJECT_DIR="/root/b2b-leads-system"     # 项目所在目录，改成你实际的路径
BACKUP_DIR="/root/backups"               # 备份文件存放目录
RETENTION_DAYS=14                        # 保留最近14天的备份，更早的自动删除
COMPOSE_DB_SERVICE="db"                  # docker-compose.yml 里数据库服务的名字

# ---- 从 .env 读取数据库账号信息 ----
source "$PROJECT_DIR/.env"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/b2b_leads_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] 开始备份数据库 -> $BACKUP_FILE"

cd "$PROJECT_DIR"
docker compose exec -T "$COMPOSE_DB_SERVICE" \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"

if [ -s "$BACKUP_FILE" ]; then
  echo "[$(date)] 备份成功，文件大小: $(du -h "$BACKUP_FILE" | cut -f1)"
else
  echo "[$(date)] 备份失败：生成的文件为空" >&2
  rm -f "$BACKUP_FILE"
  exit 1
fi

# ---- 清理过期备份 ----
find "$BACKUP_DIR" -name "b2b_leads_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "[$(date)] 已清理 ${RETENTION_DAYS} 天前的旧备份"

# ==============================================================
# 恢复备份的方法（记录在这里，真的需要恢复时照着执行）：
#
#   gunzip -c /root/backups/b2b_leads_20260101_030000.sql.gz | \
#     docker compose exec -T db psql -U b2b_user b2b_leads
#
# ==============================================================

# ==============================================================
# 加入定时任务（crontab）的方法：
#
#   crontab -e
#
# 在打开的编辑器里加一行，比如每天凌晨3点执行：
#
#   0 3 * * * /root/b2b-leads-system/deploy/backup.sh >> /root/backups/backup.log 2>&1
#
# 保存退出即可，不需要重启任何服务，cron会自动生效。
# 可以用 crontab -l 查看当前生效的定时任务列表。
# ==============================================================
