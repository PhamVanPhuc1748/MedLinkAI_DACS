from __future__ import annotations

from typing import Any

from torch_geometric.data import HeteroData

try:
    from .mo_hinh_ai import FuzzyGCN
except ImportError:
    from mo_hinh_ai import FuzzyGCN


def khoi_tao_mo_hinh_gnn(
    data_train: HeteroData,
    cau_hinh: Any,
    duong_dan_trong_so: str,
) -> FuzzyGCN:
    # Khoi tao FuzzyGCN tu cau hinh huan luyen va kich thuoc input thuc te.
    return FuzzyGCN(
        so_chieu_thuoc=data_train["drug"].x.size(1),
        so_chieu_benh=data_train["disease"].x.size(1),
        so_chieu_an=cau_hinh.kich_thuoc_an,
        so_chieu_ra=cau_hinh.kich_thuoc_ra,
        so_lop_gcn=cau_hinh.so_lop_gcn,
        duong_dan_trong_so=duong_dan_trong_so,
    )