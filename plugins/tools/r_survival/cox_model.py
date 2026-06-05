"""Cox proportional hazards prototype model.

Interface boundary: deterministic test fixture path only. This simplified
gradient path is not a production-grade, clinical-grade, or regulatory survival
analysis engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from plugins.tools._common import normal_cdf


@dataclass
class CoxResult:
    """Cox 模型结果"""

    coefficients: list[float]
    hazard_ratios: list[float]
    standard_errors: list[float]
    confidence_intervals: list[tuple[float, float]]
    p_values: list[float]
    log_likelihood: float
    n_subjects: int
    n_events: int


def cox_ph(
    times: list[float],
    events: list[int],
    covariates: list[list[float]],
) -> CoxResult:
    """
    Cox 比例风险模型（简化版，梯度下降优化）

    Args:
        times: 观察时间
        events: 事件指示 (1=事件, 0=删失)
        covariates: 协变量列表，每个元素是一个协变量的值列表

    Returns:
        CoxResult 包含系数估计、风险比、置信区间等
    """
    n = len(times)
    n_covs = len(covariates)

    if len(times) != len(events):
        raise ValueError("时间和事件列表长度必须相同")
    if n == 0:
        raise ValueError("数据不能为空")
    if any(event not in (0, 1) for event in events):
        raise ValueError("事件指示必须只包含 0 或 1")
    if n_covs == 0:
        raise ValueError("至少需要一个协变量")
    if any(len(covariate) != n for covariate in covariates):
        raise ValueError("每个协变量长度必须与观察时间长度相同")

    # 初始化系数
    beta = [0.0] * n_covs

    # 梯度下降
    learning_rate = 0.01
    max_iterations = 1000
    tolerance = 1e-6

    for iteration in range(max_iterations):
        # 计算梯度和 Hessian
        gradient = [0.0] * n_covs
        hessian = [[0.0] * n_covs for _ in range(n_covs)]

        # 按时间排序
        sorted_indices = sorted(range(n), key=lambda i: times[i])

        for idx in sorted_indices:
            if events[idx] == 1:
                # 计算风险集
                risk_set = [i for i in sorted_indices if times[i] >= times[idx]]

                # 计算 Exp(Beta * X)
                exp_bx = [_exp_dot(beta, covariates, i) for i in risk_set]
                sum_exp_bx = sum(exp_bx)

                # 计算加权平均
                weighted_x = [0.0] * n_covs
                weighted_xx = [[0.0] * n_covs for _ in range(n_covs)]

                for j, i in enumerate(risk_set):
                    w = exp_bx[j] / sum_exp_bx
                    for k in range(n_covs):
                        weighted_x[k] += w * covariates[k][i]
                        for m in range(n_covs):
                            weighted_xx[k][m] += w * covariates[k][i] * covariates[m][i]

                # 更新梯度和 Hessian
                for k in range(n_covs):
                    gradient[k] += covariates[k][idx] - weighted_x[k]
                    for m in range(n_covs):
                        hessian[k][m] += (
                            weighted_xx[k][m] - weighted_x[k] * weighted_x[m]
                        )

        # Newton-Raphson 更新
        # 简化：使用梯度下降
        max_grad = max(abs(g) for g in gradient)
        if max_grad < tolerance:
            break

        for k in range(n_covs):
            beta[k] += learning_rate * gradient[k]

    # 计算标准误（从 Hessian 逆矩阵）
    # 简化：使用近似
    se = [0.0] * n_covs
    for k in range(n_covs):
        if hessian[k][k] > 0:
            se[k] = 1.0 / math.sqrt(hessian[k][k])
        else:
            se[k] = float("inf")

    # 计算风险比、置信区间、p 值
    hazard_ratios = [math.exp(b) for b in beta]
    confidence_intervals = [
        (round(math.exp(b - 1.96 * s), 4), round(math.exp(b + 1.96 * s), 4))
        for b, s in zip(beta, se)
    ]
    p_values = []
    for k in range(n_covs):
        if se[k] > 0:
            z = beta[k] / se[k]
            p = 2 * (1 - normal_cdf(abs(z)))
            p_values.append(round(p, 6))
        else:
            p_values.append(1.0)

    # 计算对数似然
    log_lik = 0.0
    sorted_indices = sorted(range(n), key=lambda i: times[i])
    for idx in sorted_indices:
        if events[idx] == 1:
            risk_set = [i for i in sorted_indices if times[i] >= times[idx]]
            exp_bx = [_exp_dot(beta, covariates, i) for i in risk_set]
            log_lik += _exp_dot(beta, covariates, idx) - math.log(sum(exp_bx))

    return CoxResult(
        coefficients=[round(b, 4) for b in beta],
        hazard_ratios=[round(hr, 4) for hr in hazard_ratios],
        standard_errors=[round(s, 4) for s in se],
        confidence_intervals=confidence_intervals,
        p_values=p_values,
        log_likelihood=round(log_lik, 4),
        n_subjects=n,
        n_events=sum(events),
    )


def _exp_dot(beta: list[float], covariates: list[list[float]], idx: int) -> float:
    """计算 Exp(Beta . X)"""
    dot = sum(b * covariates[k][idx] for k, b in enumerate(beta))
    return math.exp(dot)
