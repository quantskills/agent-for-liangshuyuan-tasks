"""
B12 v2 — 合约规格表加载
"""
import json
import os

_SPEC_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "references", "contract_specs.json",
)

with open(_SPEC_PATH, "r", encoding="utf-8") as _f:
    SPECS = json.load(_f)

CATEGORIES = SPECS["categories"]
HK_LOT_OVERRIDES = SPECS["hk_lot_overrides"]
