from __future__ import annotations

import pandas as pd

from factor import calculate_factor, load_real_quotes


def pearson_ic(x: pd.DataFrame) -> float:
    return float(x["factor_value"].corr(x["forward_return"]))


def rank_ic(x: pd.DataFrame) -> float:
    factor_rank = x["factor_value"].rank(method="average")
    return_rank = x["forward_return"].rank(method="average")
    return float(factor_rank.corr(return_rank))


def build_forward_returns(quotes: pd.DataFrame) -> pd.DataFrame:
    df = quotes.sort_values(["ts_code", "trade_date"]).copy()
    # Signals are formed on date t; evaluation uses t+1 return to avoid same-bar leakage.
    df["next_close"] = df.groupby("ts_code")["close"].shift(-1)
    df["forward_return"] = df["next_close"] / df["close"] - 1
    return df[["trade_date", "ts_code", "forward_return"]].dropna()


def information_ratio(returns: pd.Series) -> float:
    std = returns.std()
    if returns.empty or not std:
        return 0.0
    return float(returns.mean() / std * (252**0.5))


def annualized_return(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    cumulative_return = float((1 + returns).prod() - 1)
    years = len(returns) / 252
    if years <= 0:
        return cumulative_return
    return float((1 + cumulative_return) ** (1 / years) - 1)


def run_backtest() -> dict:
    quotes = load_real_quotes()
    factor = calculate_factor(quotes, update_time="2026-05-28T15:30:00")
    forward = build_forward_returns(quotes)
    panel = factor.merge(forward, on=["trade_date", "ts_code"], how="inner")
    if panel.empty:
        raise ValueError("回测样本为空")

    daily_ic = panel.groupby("trade_date").apply(pearson_ic).dropna()
    daily_rank_ic = panel.groupby("trade_date").apply(rank_ic).dropna()
    ic = float(daily_ic.mean()) if not daily_ic.empty else 0.0
    icir = float(daily_ic.mean() / daily_ic.std()) if len(daily_ic) > 1 and daily_ic.std() else 0.0
    rank_ic_value = float(daily_rank_ic.mean()) if not daily_rank_ic.empty else 0.0
    rank_icir = (
        float(daily_rank_ic.mean() / daily_rank_ic.std())
        if len(daily_rank_ic) > 1 and daily_rank_ic.std()
        else 0.0
    )

    panel["group"] = panel.groupby("trade_date")["factor_value"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 2, labels=["low", "high"])
    )
    group_return = panel.groupby("group", observed=False)["forward_return"].mean().round(6).to_dict()
    buy_return = panel[panel["signal"] == "buy"].groupby("trade_date")["forward_return"].mean().fillna(0)
    curve = (1 + buy_return).cumprod()
    cumulative_return = float(curve.iloc[-1] - 1) if not curve.empty else 0.0
    drawdown = curve / curve.cummax() - 1
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0
    calmar = cumulative_return / abs(max_drawdown) if max_drawdown else 0.0

    daily_buy = panel[panel["signal"] == "buy"].groupby("trade_date")["ts_code"].apply(set)
    turnover_values = []
    previous = None
    for current in daily_buy:
        if previous is not None:
            union = current | previous
            turnover_values.append(1 - len(current & previous) / len(union) if union else 0)
        previous = current
    turnover = float(sum(turnover_values) / len(turnover_values)) if turnover_values else 0.0

    return {
        "IC": round(ic, 6),
        "ICIR": round(icir, 6),
        "Rank IC": round(rank_ic_value, 6),
        "Rank ICIR": round(rank_icir, 6),
        "IR(SHR*)": round(information_ratio(buy_return), 6),
        "CR": round(calmar, 6),
        "ARR(%)": round(annualized_return(buy_return) * 100, 6),
        "MDD(%)": round(max_drawdown * 100, 6),
        "分层收益": group_return,
        "换手率": round(turnover, 6),
        "样本数": int(len(panel)),
        "评估口径": "因子在 t 日形成，收益使用 t+1 close / t close - 1；正式策略若需要可交易收益，应改用下一可交易价并计入费用滑点。",
    }


if __name__ == "__main__":
    metrics = run_backtest()
    for key, value in metrics.items():
        print(f"{key}: {value}")
