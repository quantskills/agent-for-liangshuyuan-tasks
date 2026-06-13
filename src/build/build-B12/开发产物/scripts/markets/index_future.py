"""
B12 v2 — 股指期货决策模块（IF / IC / IH / IM）

T+0：当日开仓可平。
    sellable = sellable_qty + locked_qty
    （T+0 品种调用方一般传 locked_qty=0；为容错，把锁仓也视为可卖）
合约最小单位 1 手；资金占用 = qty × price × multiplier × margin_rate + 手续费。
"""
from common import (
    PNL_ADD_THRESHOLD, PNL_HALF_CUT_THRESHOLD, PNL_CLOSE_ALL_THRESHOLD,
    ADD_RATIO, HALF_CUT_RATIO,
    round_lot, make_instr, make_hold, reason_prefix,
)
from specs import CATEGORIES

MARKET = "INDEX_FUTURE"


def _contract_spec(code: str) -> dict:
    """从代码前 2 位（IF/IC/IH/IM）取合约规格。"""
    prefix = code[:2]
    return CATEGORIES[MARKET]["contracts"][prefix]


def _required_margin(qty: int, price: float, code: str) -> float:
    """开仓所需保证金 + 手续费。"""
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
