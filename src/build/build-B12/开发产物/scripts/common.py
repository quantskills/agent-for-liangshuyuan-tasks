"""
B12 v2 — 共享常量、工具、调仓指令构造器

阈值参考 jobs/B12 日内仓位动态管理.txt 的核心规则：
    浮盈 > 1%   → 加仓 50%
    浮亏 >= 0.5% → 砍半仓
    浮亏 >= 1%   → 全平
    收盘前 15 分钟 → 强平
"""

# ── 阈值常量 ─────────────────────────────────────────────────────────
PNL_ADD_THRESHOLD       = 0.01    # 浮盈 > 1% 加仓（严格大于）
PNL_HALF_CUT_THRESHOLD  = -0.005  # 浮亏 >= 0.5% 砍半（含边界）
PNL_CLOSE_ALL_THRESHOLD = -0.01   # 浮亏 >= 1% 全平（含边界）
ADD_RATIO               = 0.5
HALF_CUT_RATIO          = 0.5


# ── 数量取整 ─────────────────────────────────────────────────────────
def round_lot(qty: int, lot: int) -> int:
    """向下取整到一手的整数倍。lot<=1 时直接返回非负整数。"""
    qty = max(0, int(qty))
    if lot <= 1:
        return qty
    return (qty // lot) * lot


# ── 调仓指令 dict 构造（严格 8 字段） ────────────────────────────────
def make_instr(code, pnl_pct, current_qty, time_str,
               action, qty_change, target_qty, reason) -> dict:
    """严格按 CLAUDE.md §调仓指令数据结构生成 8 字段 dict。"""
    return {
        "code": code,
        "pnl_pct": pnl_pct,
        "current_qty": current_qty,
        "time": time_str,
        "action": action,
        "qty_change": qty_change,
        "target_qty": target_qty,
        "reason": reason,
    }


def make_hold(code, pnl_pct, total, time_str, reason) -> dict:
    """快捷：构造 hold 指令。"""
    return make_instr(code, pnl_pct, total, time_str, "hold", 0, total, reason)


# ── reason 结构化前缀 ────────────────────────────────────────────────
def reason_prefix(market: str, sellable: int, cash_req: float = 0.0) -> str:
    """生成 [MARKET][sellable=N][cash_req=X] 前缀。调用方解析协议见 api_guide.md。"""
    return f"[{market}][sellable={sellable}][cash_req={cash_req:.2f}]"
