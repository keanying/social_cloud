"""公开的系统状态汇总，供首页右下角的状态面板使用。

只返回开关状态、可用平台数以及近 24 小时的成功率与平均耗时（比例与均值），不公开调用量等运营数据。
结果按数据库缓存 30 秒，避免频繁查询。
"""
import threading
import time
from datetime import datetime, timezone

from flask import current_app

from configs.general_constants import DOMAIN_TO_NAME
from configs.logging_config import get_logger
from src.db import get_db, setting

logger = get_logger(__name__)

CACHE_SECONDS = 30
# 成功率低于该值视为「部分异常」（样本过少时不判定）
DEGRADED_SUCCESS_RATE = 80.0
MIN_SAMPLES = 10

_cache = {}
_lock = threading.Lock()


def _compute():
    platforms = set(DOMAIN_TO_NAME.values())
    data = {
        "api_enabled": True,
        "parser_enabled": True,
        "login_required": True,
        "platforms_total": len(platforms),
        "platforms_available": len(platforms),
        "success_rate_24h": None,
        "avg_ms_24h": None,
        "database_ok": True,
    }
    try:
        db = get_db()
        data["api_enabled"] = setting("global_api_enabled", "1") == "1"
        data["parser_enabled"] = data["api_enabled"] and setting("demo_enabled", "1") == "1"
        data["login_required"] = setting("demo_login_required", "1") == "1"
        disabled = {row["platform"] for row in db.execute("SELECT platform FROM platform_settings WHERE enabled = 0")}
        data["platforms_available"] = len(platforms - disabled)
        row = db.execute(
            "SELECT COUNT(*) AS calls, SUM(status_code < 400) AS ok, "
            "AVG(CASE WHEN status_code < 400 THEN duration_ms END) AS avg_ms "
            "FROM request_logs WHERE datetime(created_at) >= datetime('now', '-1 day')"
        ).fetchone()
        calls = row["calls"] or 0
        if calls >= MIN_SAMPLES:
            data["success_rate_24h"] = round((row["ok"] or 0) * 100.0 / calls, 1)
        if row["avg_ms"] is not None:
            data["avg_ms_24h"] = int(row["avg_ms"])
    except Exception:
        logger.exception("系统状态查询失败")
        data["database_ok"] = False

    if not data["api_enabled"] or not data["database_ok"]:
        overall = "down"
    elif (not data["parser_enabled"]
          or data["platforms_available"] < data["platforms_total"]
          or (data["success_rate_24h"] is not None and data["success_rate_24h"] < DEGRADED_SUCCESS_RATE)):
        overall = "degraded"
    else:
        overall = "ok"
    data["overall"] = overall
    data["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return data


def public_status():
    key = current_app.config.get("DATABASE")
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    data = _compute()
    with _lock:
        _cache[key] = (now, data)
    return data


def clear_cache():
    with _lock:
        _cache.clear()
