from __future__ import annotations

# =============================================================================
# TẦNG FUZZY ĐA KÊNH ĐA QUY TẮC (Multi-channel, Multi-rule Fuzzy Layer)
# =============================================================================
#
# CÔNG THỨC TOÁN HỌC:
# -------------------
# Cho vector đặc trưng x ∈ ℝ^d, mỗi chiều i có tham số riêng μ_i, σ_i ∈ ℝ.
#
# 1. Hàm thành viên Gaussian (trơn, liên tục, tập trung quanh μ):
#       m_gauss_i(x_i) = exp( -(x_i - μ_i)² / (2·σ_i²) )
#
# 2. Hàm thành viên Tam giác (tuyến tính từng đoạn, kháng nhiễu tốt hơn):
#       m_tri_i(x_i)   = max(0,  1 - |x_i - μ_i| / σ_i)
#
# 3. Kết hợp có học (learnable blending):
#       α = sigmoid(α₀) ∈ (0, 1)           (α₀ là tham số học được)
#       m_i(x_i) = α · m_gauss_i + (1 - α) · m_tri_i
#
# 4. Output:
#       LopFuzzy(x)_i = x_i · m_i(x_i)     (suppress nhiễu bằng membership)
#
# Ưu điểm so với phiên bản cũ (scalar μ, σ):
#   - Per-channel: mỗi chiều đặc trưng có ngưỡng fuzzy riêng
#   - Multi-rule:  Gaussian trơn + Triangular kháng nhiễu → bù đắp nhau
#   - Learnable α: mô hình tự học tỉ lệ pha trộn tối ưu
#   - softplus(log_σ): đảm bảo σ > 0 với gradient mượt hơn clamp
# =============================================================================

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class LopFuzzy(nn.Module):
    """Tầng Fuzzy đa kênh, đa quy tắc (Gaussian + Triangular membership).

    Tham số:
        n_features  : số chiều đặc trưng đầu vào (d).
        sigma_init  : giá trị khởi tạo cho σ (mặc định 1.0).
    """

    def __init__(self, n_features: int = 1, sigma_init: float = 1.0) -> None:
        super().__init__()

        # μ ∈ ℝ^d — tâm của hàm thành viên, khởi tạo = 0
        self.mu = nn.Parameter(torch.zeros(n_features))

        # log(σ) ∈ ℝ^d — log-scale để đảm bảo σ > 0 qua softplus
        log_sigma_init = math.log(max(float(sigma_init), 1e-6))
        self.log_sigma = nn.Parameter(torch.full((n_features,), log_sigma_init))

        # α₀ — logit của blend coefficient; sigmoid(0) = 0.5 → khởi đầu 50/50
        self.alpha_logit = nn.Parameter(torch.tensor(0.0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Áp dụng hàm thành viên Fuzzy lên từng chiều của x.

        Quy trình:
        1. Tính σ = softplus(log_σ) + ε  (đảm bảo σ > 0)
        2. Tính diff = x - μ  (khoảng cách từ mỗi x_i đến tâm μ_i)
        3. m_gauss = exp(-diff² / (2σ²))         [Gaussian membership]
        4. m_tri   = max(0, 1 - |diff| / σ)      [Triangular membership]
        5. m       = α·m_gauss + (1-α)·m_tri     [Blend có học]
        6. Output  = x ⊙ m                        [Suppress nhiễu]

        Args:
            x: tensor đầu vào, shape (..., n_features)
        Returns:
            Tensor cùng shape với x, nhưng các chiều ít liên quan đến tâm μ
            bị giảm biên độ (suppress) bởi membership function.
        """
        # σ = softplus(log_σ) + ε > 0
        sigma = F.softplus(self.log_sigma) + 1e-6

        diff = x - self.mu  # x_i - μ_i  shape: (..., d)

        # Hàm thành viên Gaussian: m_gauss = exp(-(x-μ)² / (2σ²))
        m_gauss = torch.exp(-(diff ** 2) / (2.0 * sigma ** 2))

        # Hàm thành viên Tam giác: m_tri = max(0, 1 - |x-μ| / σ)
        m_tri = torch.clamp(1.0 - diff.abs() / sigma, min=0.0)

        # Kết hợp có học: α ∈ (0,1) từ α_logit
        alpha = torch.sigmoid(self.alpha_logit)
        m = alpha * m_gauss + (1.0 - alpha) * m_tri

        # Output: x ⊙ m(x)
        return x * m
