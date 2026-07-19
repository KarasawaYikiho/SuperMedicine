"""权限约束引擎 — P0 优先级"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .audit import AuditLogger
from .policy import (
    DEFAULT_POLICY_RELATIVE_PATH,
    PermissionPolicy,
    PermissionResult,
    default_policy_path,
    ensure_default_policy,
)


class PermissionPolicyLoadError(RuntimeError):
    """Raised when permission policies cannot be loaded safely."""


class PermissionEngine:
    DEFAULT_POLICY_FILENAME = DEFAULT_POLICY_RELATIVE_PATH.name

    def __init__(self, policy_dir: Path, audit_log: Path):
        self._policy_dir = Path(policy_dir)
        self._audit = AuditLogger(audit_log)
        self._policies: dict[str, PermissionPolicy] = {}
        self._load_policies()

    @classmethod
    def default_policy_path(cls, project_dir: Path | None = None) -> Path:
        """Return the canonical tracked default permission policy path."""
        return default_policy_path(project_dir)

    @classmethod
    def ensure_default_policy(
        cls, project_dir: Path, source_root: Path | None = None
    ) -> Path:
        """Ensure the canonical project default permission policy exists."""
        return ensure_default_policy(project_dir, source_root=source_root)

    def _load_policies(self) -> None:
        if not self._policy_dir.exists():
            raise FileNotFoundError(
                f"Permission policy directory not found: {self._policy_dir}. "
                f"Expected canonical default policy at {self._policy_dir / self.DEFAULT_POLICY_FILENAME}."
            )

        policy_files = sorted(self._policy_dir.glob("*.yaml"))
        if not policy_files:
            raise FileNotFoundError(
                f"No permission policy files found in {self._policy_dir}. "
                f"Expected canonical default policy at {self._policy_dir / self.DEFAULT_POLICY_FILENAME}."
            )

        for f in policy_files:
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                raise PermissionPolicyLoadError(
                    f"Invalid YAML permission policy: {f}: {exc}"
                ) from exc
            except OSError as exc:
                raise PermissionPolicyLoadError(
                    f"Unable to read permission policy: {f}: {exc}"
                ) from exc

            if data is None:
                raise PermissionPolicyLoadError(f"Empty permission policy file: {f}")

            # Support both Single Dict and List of Policies
            policies = data if isinstance(data, list) else [data]
            if not isinstance(policies, list):
                raise PermissionPolicyLoadError(
                    f"Permission policy must be a mapping or list: {f}"
                )

            for item in policies:
                if not isinstance(item, dict) or "agent_id" not in item:
                    raise PermissionPolicyLoadError(
                        f"Invalid permission policy entry in {f}"
                    )
                try:
                    policy = PermissionPolicy.from_dict(item)
                except (KeyError, TypeError, ValueError) as exc:
                    raise PermissionPolicyLoadError(
                        f"Invalid permission policy entry in {f}: {exc}"
                    ) from exc
                self._policies[policy.agent_id] = policy

    def check(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> PermissionResult:
        """检查操作权限

        Args:
            agent_id: Agent ID
            action: 操作名称
            resource: 目标资源
            context: 运行时上下文（用于 hard_limits 检查；Kernel 插件执行也会记录
                plugin/action/task 等上下文，确保 CLI 与运行时共用同一策略路径）
        """
        policy = self._policies.get(agent_id)
        if policy is None:
            return self._deny(agent_id, action, resource, "unknown_agent")

        full_access_denial = self._full_access_denial_reason(context)
        if full_access_denial:
            return self._deny(
                agent_id,
                action,
                resource,
                full_access_denial,
                context=self._full_access_audit_context(context),
            )

        hard_limit_denial = self._hard_limit_denial_reason(policy, context)
        if hard_limit_denial:
            return self._deny(agent_id, action, resource, hard_limit_denial)

        result = policy.check(action, resource)
        reason = self._policy_result_reason(result, context)
        self._audit.log(
            agent_id=agent_id,
            action=action,
            resource=resource,
            result=result.value,
            reason=reason,
            context=self._full_access_audit_context(context),
        )
        return result

    def _deny(
        self,
        agent_id: str,
        action: str,
        resource: str,
        reason: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> PermissionResult:
        self._audit.log(
            agent_id=agent_id,
            action=action,
            resource=resource,
            result="DENIED",
            reason=reason,
            context=context,
        )
        return PermissionResult.DENIED

    @staticmethod
    def _full_access_denial_reason(context: dict[str, Any] | None) -> str | None:
        if not context or context.get("access_mode") != "full":
            return None
        if context.get("high_risk_operation") and not context.get(
            "explicit_authorization"
        ):
            return "full_access_high_risk_requires_explicit_authorization"
        if context.get("high_risk_operation") and not context.get(
            "risk_notice_acknowledged"
        ):
            return "full_access_high_risk_requires_risk_notice_acknowledgement"
        return None

    @staticmethod
    def _hard_limit_denial_reason(
        policy: PermissionPolicy, context: dict[str, Any] | None
    ) -> str | None:
        if not context or not policy.hard_limits:
            return None
        if context.get("requires_network") and policy.hard_limits.network_access is False:
            return "hard_limit_exceeded:network_access:false"
        if (
            context.get("requires_external_api")
            and policy.hard_limits.external_api is False
        ):
            return "hard_limit_exceeded:external_api:false"
        for limit_name, limit_value in policy.hard_limits.items():
            context_value = context.get(limit_name)
            if context_value is not None and context_value > limit_value:
                return f"hard_limit_exceeded:{limit_name}:{context_value}>{limit_value}"
        return None

    @staticmethod
    def _full_access_audit_context(
        context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not context or context.get("access_mode") != "full":
            return None
        keys = (
            "access_mode",
            "explicit_authorization",
            "risk_notice_acknowledged",
            "high_risk_operation",
        )
        return {key: context.get(key) for key in keys}

    @staticmethod
    def _policy_result_reason(
        result: PermissionResult, context: dict[str, Any] | None
    ) -> str:
        if (
            result == PermissionResult.ALLOWED
            and context
            and context.get("access_mode") == "full"
        ):
            return "full_access_explicit_authorization_preserved:risk_notice_required_for_high_risk"
        if result == PermissionResult.ALLOWED:
            return "whitelist_match"
        return "blacklist_match_or_default_deny"
