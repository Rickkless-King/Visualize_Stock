"""Day 3 闯关单元测试：验证 K 线多周期重采样引擎 (1D -> 1W / 1M).

运行方式（在项目根目录终端激活 .venv 后）：
    pytest -x
参数 `-x` 的意思是「遇到第一个没通过的测试就立刻停下来」，方便你按 TODO 1 -> TODO 2 -> TODO 3 逐关打怪！
"""

from pathlib import Path

import pytest

from engine.resampler import (
    aggregate_ohlcv_group,
    get_period_key,
    load_daily_csv,
    resample_bars,
)

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


# =====================================================================
# 第一关：检验 TODO 1 —— get_period_key（自然周 / 自然月分桶标签）
# =====================================================================
def test_1_get_period_key_basic_and_holiday_week() -> None:
    # 1D 原样返回日期
    assert get_period_key("2026-01-20", "1D") == "2026-01-20"

    # 1W 节假日短周验证：2026-01-19 是美股马丁路德金日（周一休市），周二 01-20 才开盘
    # 周二 (01-20) 与周五 (01-23) 必须落进同一个周桶（锚定周一 '2026-01-19'）
    tue_key = get_period_key("2026-01-20", "1W")
    fri_key = get_period_key("2026-01-23", "1W")
    assert tue_key == "2026-01-19"
    assert tue_key == fri_key

    # 1W 跨年跨月周验证：2025-12-29(周一) 与 2026-01-02(周五) 属于同一个交易周！
    assert get_period_key("2025-12-29", "1W") == "2025-12-29"
    assert get_period_key("2026-01-02", "1W") == "2025-12-29"

    # 1M 自然月分桶验证：上面那两个跨年日期在月线模式下必须干净拆进两个不同的月份桶！
    assert get_period_key("2025-12-31", "1M") == "2025-12"
    assert get_period_key("2026-01-02", "1M") == "2026-01"


def test_2_get_period_key_rejects_invalid_timeframe() -> None:
    with pytest.raises(ValueError):
        get_period_key("2026-01-20", "5m")


# =====================================================================
# 第二关：检验 TODO 2 —— aggregate_ohlcv_group（单桶 OHLCV 合成规则）
# =====================================================================
def test_3_aggregate_ohlcv_group_rules() -> None:
    # 取真实 NVDA 跨年节假日短周（2025-12-29 ~ 2026-01-02，周四元旦休市，共 4 根日线）
    holiday_week = [
        {"time": "2025-12-29", "open": 187.71, "high": 188.76, "low": 185.91, "close": 188.22, "volume": 120006100},
        {"time": "2025-12-30", "open": 188.24, "high": 188.99, "low": 186.93, "close": 187.54, "volume": 97687300},
        {"time": "2025-12-31", "open": 189.57, "high": 190.56, "low": 186.49, "close": 186.50, "volume": 120100500},
        {"time": "2026-01-02", "open": 189.84, "high": 192.93, "low": 188.26, "close": 188.85, "volume": 148240500},
    ]
    merged = aggregate_ohlcv_group(holiday_week)

    assert merged["time"] == "2026-01-02"    # 桶内最后一个真实交易日
    assert merged["open"] == 187.71          # 周一第一口开盘价
    assert merged["high"] == 192.93          # 全周最高价（出现在周五）
    assert merged["low"] == 185.91           # 全周最低价（出现在周一）
    assert merged["close"] == 188.85         # 周五收盘定格价
    assert merged["volume"] == 486034400     # 4 天成交量精确累加


# =====================================================================
# 第三关：检验 TODO 3 —— resample_bars（完整流水线 + 真实 NVDA/AAPL 数据实证）
# =====================================================================
def test_4_resample_bars_immutability_and_sorting() -> None:
    # 故意传入乱序日线，且后续修改返回值，验证：(1) 自动按日期排序；(2) Layer 0 原底图绝对不被污染
    raw_bars = [
        {"time": "2026-01-06", "open": 190.52, "high": 192.17, "low": 186.82, "close": 187.24, "volume": 100},
        {"time": "2026-01-05", "open": 191.76, "high": 193.63, "low": 186.15, "close": 188.12, "volume": 200},
    ]
    daily_copy = resample_bars(raw_bars, "1D")
    assert [b["time"] for b in daily_copy] == ["2026-01-05", "2026-01-06"]

    # 恶意篡改下游返回结果，检查上游 raw_bars 底图必须毫发无损！
    daily_copy[0]["close"] = 99999.0
    assert raw_bars[1]["close"] == 188.12

    # 空列表边界条件
    assert resample_bars([], "1W") == []


def test_5_real_nvda_parallel_resampling_beats_prototype_bug() -> None:
    """用真实 NVDA 一年日线实证：为什么不能像原型那样每 5 根切一周，也不能拿周线拼月线！"""
    nvda_daily = load_daily_csv(SAMPLE_DIR / "nvda_daily.csv")
    assert len(nvda_daily) == 251

    nvda_weekly = resample_bars(nvda_daily, "1W")
    nvda_monthly = resample_bars(nvda_daily, "1M")

    # 1) 守恒定律：无论切成周线还是月线，全年总成交量、全年最高价、全年最低价必须与日线 100% 相等！
    assert sum(b["volume"] for b in nvda_weekly) == sum(b["volume"] for b in nvda_daily)
    assert sum(b["volume"] for b in nvda_monthly) == sum(b["volume"] for b in nvda_daily)
    assert max(b["high"] for b in nvda_weekly) == max(b["high"] for b in nvda_daily)
    assert min(b["low"] for b in nvda_monthly) == min(b["low"] for b in nvda_daily)

    # 2) 验证感恩节短周（2025-11-26 周三 + 11-28 周五，仅 2 个交易日）自成第一根周线，绝不串味到 12 月！
    first_week = nvda_weekly[0]
    assert first_week["time"] == "2025-11-28"
    assert first_week["open"] == 181.63
    assert first_week["close"] == 177.00

    # 3) 实证 Day 2 病历重点：跨月周 (2025-12-29 ~ 2026-01-02) 在周线里合为一根，
    #    但从日线平行聚合出的 2025-12 月线和 2026-01 月线边界干干净净！
    dec_2025 = next(b for b in nvda_monthly if b["time"].startswith("2025-12"))
    jan_2026 = next(b for b in nvda_monthly if b["time"].startswith("2026-01"))
    assert dec_2025["open"] == 174.76        # 2025-12-01 开盘价
    assert dec_2025["close"] == 186.50       # 2025-12-31 收盘价（绝不混入 1 月 2 日数据）
    assert jan_2026["open"] == 189.84        # 2026-01-02 新年首日开盘价（绝不混入 12 月底数据）
    assert jan_2026["time"] == "2026-01-30"  # 1 月 31 日是周六，锚定真实月末交易日 01-30


def test_6_real_aapl_weekly_and_monthly_consistency() -> None:
    """同步验证真实 AAPL 一年日线重采样."""
    aapl_daily = load_daily_csv(SAMPLE_DIR / "aapl_daily.csv")
    aapl_weekly = resample_bars(aapl_daily, "1W")
    aapl_monthly = resample_bars(aapl_daily, "1M")

    assert 50 <= len(aapl_weekly) <= 54
    assert 12 <= len(aapl_monthly) <= 13
    assert sum(b["volume"] for b in aapl_weekly) == sum(b["volume"] for b in aapl_daily)
    assert sum(b["volume"] for b in aapl_monthly) == sum(b["volume"] for b in aapl_daily)
