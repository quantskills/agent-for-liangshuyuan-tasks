"""
B12 v2 — 品种识别

输入 code 字符串，输出 5 类市场标签之一：
    A_STOCK / A_ETF / INDEX_FUTURE / COMMODITY_FUTURE / HK_STOCK / UNKNOWN
"""
import re

from specs import CATEGORIES

_RE_INDEX_FUT     = re.compile(r"^(IF|IC|IH|IM)\d{4}$")
_RE_COMMODITY_FUT = re.compile(r"^([a-z]{1,3})\d{3,4}$")
_RE_A_DIGIT6      = re.compile(r"^\d{6}$")
_RE_HK_DIGIT5     = re.compile(r"^\d{5}$")
_RE_HK_PREFIX     = re.compile(r"^HK\d+$", re.IGNORECASE)
_RE_A_PREFIX      = re.compile(r"^(sh|sz)\d{6}$", re.IGNORECASE)

# A股 ETF 号段
_A_ETF_RANGES = [(510000, 518999), (159000, 159999), (588000, 588999)]
# A股股票号段（沪市主板/科创板/深市主板/中小板/创业板）
_A_STOCK_RANGES = [
    (600000, 605999),  # 沪市主板
    (601000, 601999),
    (603000, 603999),
    (688000, 688999),  # 科创板
    (1,      3999),    # 深市主板（000001-003999）
    (300000, 301999),  # 创业板
]


def _classify_a_digit6(c: str) -> str:
    """6 位数字代码 → A_STOCK / A_ETF / UNKNOWN"""
    n = int(c)
    for lo, hi in _A_ETF_RANGES:
        if lo <= n <= hi:
            return "A_ETF"
    for lo, hi in _A_STOCK_RANGES:
        if lo <= n <= hi:
            return "A_STOCK"
    return "UNKNOWN"


def classify(code: str) -> str:
    """品种识别入口。返回 5 类市场标签或 UNKNOWN。"""
    if not isinstance(code, str) or not code:
        return "UNKNOWN"
    c = code.strip()

    # 股指期货：IF/IC/IH/IM + 4 位数字
    if _RE_INDEX_FUT.match(c):
        return "INDEX_FUTURE"

    # 商品期货：小写字母 + 3~4 位数字（如 rb2410），需命中规格表白名单
    m = _RE_COMMODITY_FUT.match(c)
    if m and c[0].islower():
        prefix = m.group(1)
        if prefix in CATEGORIES["COMMODITY_FUTURE"]["contracts"]:
            return "COMMODITY_FUTURE"
        return "UNKNOWN"

    # 带前缀
    if _RE_A_PREFIX.match(c):
        return _classify_a_digit6(c[2:])
    if _RE_HK_PREFIX.match(c):
        return "HK_STOCK"

    # 5 位数字 → 港股
    if _RE_HK_DIGIT5.match(c):
        return "HK_STOCK"

    # 6 位数字 → A股 / A股ETF
    if _RE_A_DIGIT6.match(c):
        return _classify_a_digit6(c)

    return "UNKNOWN"
