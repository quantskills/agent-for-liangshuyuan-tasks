"""
B12 v2 — 商品期货决策模块（rb / cu / m / au / ag / i 等）

T+0：当日开仓可平。
    sellable = sellable_qty + locked_qty
合约规格按品种前缀（小写字母）查表，每个品种 multiplier / margin_rate / tick_size 不同。
"""
import re

from common import (
    PNL_ADD_THRESHOLD, PNL_HALF_CUT_THRESHOLD, PNL_CLOSE_ALL_THRESHOLD,
    ADD_RATIO, HALF_CUT_RATIO,
    round_lot, make_instr, make_hold, reason_prefix,
)
from specs import CATEGORIES

MARKET = "COMMODITY_FUTURE"

_RE_PREFIX = re.compile(r"^([a-z]{1,3})\d{3,4}$")


def _contract_spec(code: str) -> dict:
    """提取小写字母前缀，查合约规格。调用前 classify 已确保命中白名单。"""
    m = _RE_PREFIX.match(code)
    prefix = m.group(1)
    return CATEGORIES[MARKET]["contracts"][prefix]


def _required_margin(qty: int, price: float, code: str) -> float:
    if qty <= 0 or price <= 0:
        return 0.0
    spec = _contract_spec(code)
    cat  = CATEGORIES[MARKET]
    notional = qty * price * spec["multiplier"]
    margin = notional * spec["margin_rate"]
    fee = notional * cat["fee_rate"]
    return margin + fee


def manage(item: dict) -> dict:
    code     = item["code"]
    pnl_pct  = float(item["pnl_pct"])
    sellable = max(0, int(item["sellable_qty"]) + int(item["locked_qty"]))
    price    = float(item["price"])
    cash     = float(item["available_cash"])
    time_str = item["time"]

    cat     = CATEGORIES[MARKET]
    lot     = cat["lot_size"]
    force_t = cat["force_close_time"]
    total   = sellable

    # 1) 强平
    if time_str >= force_t:
        if sellable <= 0:
            return make_hold(code, pnl_pct, total, time_str,
                             f"{reason_prefix(MARKET, sellable)} {force_t} 强平 无持仓 hold")
        close = round_lot(sellable, lot)
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -close, total - close,
            f"{reason_prefix(MARKET, sellable)} {force_t} 强平 平 {close} 手",
        )

    # 2) 全平
    if pnl_pct <= PNL_CLOSE_ALL_THRESHOLD:
        if sellable <= 0:
            return make_hold(code, pnl_pct, total, time_str,
                             f"{reason_prefix(MARKET, sellable)} 浮亏 {pnl_pct*100:.2f}% 全平 无持仓 hold")
        close = round_lot(sellable, lot)
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -close, total - close,
            f"{reason_prefix(MARKET, sellable)} 浮亏 {pnl_pct*100:.2f}% 全平 {close} 手",
        )

    # 3) 砍半仓
    if pnl_pct <= PNL_HALF_CUT_THRESHOLD:
        raw = int(sellable * HALF_CUT_RATIO)
        cut = round_lot(raw, lot)
        if cut <= 0:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(MARKET, sellable)} 浮亏 {pnl_pct*100:.2f}% "
                f"砍半计算 {raw} 手不足一手 hold",
            )
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -cut, total - cut,
            f"{reason_prefix(MARKET, sellable)} 浮亏 {pnl_pct*100:.2f}% 砍半仓 {cut} 手",
        )

    # 4) 加仓
    if pnl_pct > PNL_ADD_THRESHOLD:
        raw = int(sellable * ADD_RATIO)
        add = round_lot(raw, lot)
        if add <= 0:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(MARKET, sellable)} 浮盈 {pnl_pct*100:.2f}% "
                f"加仓计算 {raw} 手不足一手 hold",
            )
        need = _required_margin(add, price, code)
        if need > cash:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(MARKET, sellable, need)}[v2:cash_insufficient] "
                f"浮盈 {pnl_pct*100:.2f}% 加仓 {add} 手需保证金 {need:.2f} "
                f"现金 {cash:.2f} 不足 hold",
            )
        return make_instr(
            code, pnl_pct, total, time_str, "buy", add, total + add,
            f"{reason_prefix(MARKET, sellable, need)} 浮盈 {pnl_pct*100:.2f}% 加仓 {add} 手",
        )

    # 5) 默认 hold
    return make_hold(
        code, pnl_pct, total, time_str,
        f"{reason_prefix(MARKET, sellable)} 浮盈/亏 {pnl_pct*100:+.2f}% 未触发任何条件 hold",
    )
