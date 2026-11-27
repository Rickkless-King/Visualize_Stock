"""K 线多周期重采样引擎 (Day 3: 日线 -> 周线 / 月线平行聚合).

设计铁律（对齐 docs/ARCHITECTURE.md）：
1. 单一权威母本：周线 (1W) 与月线 (1M) 全部直接从权威日线 (1D) 平行聚合，绝不用周线去拼月线（防跨月周污染）。
2. 自然日历分桶：按真实日历周（周一为锚点）/ 自然月分桶，兼容美股法定节假日短周（如感恩节 2~4 天周、马丁路德金日周一休市）。
3. Layer 0 底图只读不可变：重采样永远返回全新的字典列表，绝不原地修改传入的 daily_bars。
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

BarDict = dict[str, Any]
SUPPORTED_TIMEFRAMES = ("1D", "1W", "1M")


def load_daily_csv(csv_path: str | Path) -> list[BarDict]:
    """从本地 CSV 读取美股日线样例数据，转为标准 K 线字典列表（已为你写好，直接可用）."""
    path = Path(csv_path)
    bars: list[BarDict] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append(
                {
                    "time": row["time"].strip(),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
            )
    return bars


# =====================================================================
# 积木 1：分桶贴标签器 —— 算出某根日线属于哪一个周期桶
# =====================================================================
def get_period_key(date_str: str, timeframe: str) -> str:
    """根据交易日字符串 'YYYY-MM-DD' 和目标周期 ('1D' / '1W' / '1M')，返回它的分组桶标签.

    规则约定：
    - '1D'：每根日线自己一桶，直接返回原日期字符串，例如 '2026-01-02'
    - '1W'：返回这天所属自然周的「本周一日期」（'YYYY-MM-DD'）。
            哪怕本周一休市没交易（例如 2026-01-19 马丁路德金日休市，周二 2026-01-20 才开盘），
            周二往前退 1 天、周五往前退 4 天，算出来的本周一都是 '2026-01-19'，会自动落进同一桶！
            哪怕跨年周（如 2025-12-29 周一 ~ 2026-01-02 周五），算出来的本周一也都是 '2025-12-29'！
    - '1M'：返回这天所属自然月的「年月前 7 位」（'YYYY-MM'），例如 '2026-01'
    - 其他非法周期：主动抛出 ValueError（严禁像旧项目那样静默吞错）
    """
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"不支持的周期: {timeframe!r}，仅支持 {SUPPORTED_TIMEFRAMES}")

    # 已帮你把字符串 '2026-01-20' 解析成 Python 日期对象 dt
    # 小提示：dt.weekday() 会返回星期几的数字 —— 周一是 0，周二是 1，……，周五是 4
    dt = datetime.strptime(date_str, "%Y-%m-%d").date()

    if timeframe == "1D":
        return date_str

    if timeframe == "1W":
        monday = dt - timedelta(days=dt.weekday())
        return monday.strftime("%Y-%m-%d")

    return dt.strftime("%Y-%m")


# =====================================================================
# 积木 2：单桶捏合器 —— 把同一个桶里的多根日线捏成 1 根大周期 K 线
# =====================================================================
def aggregate_ohlcv_group(group_bars: list[BarDict]) -> BarDict:
    """将属于同一周（或同一月）且已按日期升序排好的日线列表，合成为 1 根标准 K 线字典.

    金融合成标准规则（Point-in-Time 真实交易日锚定）：
    - time  : 取桶内【最后一根】日线的 time（即该周/该月最后一个真实交易日，绝不编造周六日日期）
    - open  : 取桶内【第一根】日线的 open（该周期第一口开盘价）
    - high  : 取桶内【所有】日线 high 的最大值 max(...)
    - low   : 取桶内【所有】日线 low 的最小值 min(...)
    - close : 取桶内【最后一根】日线的 close（该周期收盘定格价）
    - volume: 取桶内【所有】日线 volume 的累加总和 sum(...)
    """
    if not group_bars:
        raise ValueError("group_bars 不能为空列表")

    return {
        "time": group_bars[-1]["time"],
        "open": group_bars[0]["open"],
        "close": group_bars[-1]["close"],
        "volume": sum(bar["volume"] for bar in group_bars),
        "high": max(bar["high"] for bar in group_bars),
        "low": min(bar["low"] for bar in group_bars),
    }


# =====================================================================
# 积木 3：流水线总装器 —— 串联积木 1 和积木 2，输出完整重采样序列
# =====================================================================
def resample_bars(daily_bars: list[BarDict], timeframe: str = "1D") -> list[BarDict]:
    """输入权威日线列表，输出目标周期 ('1D' / '1W' / '1M') 的新 K 线列表（保持原底图只读不改）."""
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"不支持的周期: {timeframe!r}，仅支持 {SUPPORTED_TIMEFRAMES}")

    if not daily_bars:
        return []

    # 防御上游乱序数据：先按日期从早到晚排好序（不会修改原列表 daily_bars）
    sorted_bars = sorted(daily_bars, key=lambda b: b["time"])

    buckets: dict[str, list[BarDict]] = {}
    for bar in sorted_bars:
        key = get_period_key(bar["time"], timeframe)
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(bar)

    newlist = []
    for group in buckets.values():
        merged_bar = aggregate_ohlcv_group(group)
        newlist.append(merged_bar)
    return newlist
