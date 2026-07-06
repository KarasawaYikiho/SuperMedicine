from __future__ import annotations

import json
import logging

from cli import _RedactingFormatter
from core.redaction import redact_sensitive
from core.tui.app import SuperMedicineTUI


def test_redact_sensitive_covers_headers_cloud_keys_private_keys_and_query_values():
    openai_key = "sk-redaction-openai-secret"
    aws_key = "AKIAIOSFODNN7EXAMPLE"
    bearer = "bearer-token-value.abc123"
    password = "correct-horse-battery-staple"
    private_key = (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvredactionprivatekeymaterial\n"
        "-----END PRIVATE KEY-----"
    )
    payload = {
        "headers": {
            "Authorization": f"Bearer {bearer}",
            "Cookie": "sessionid=cookie-secret-value",
            "X-Api-Key": openai_key,
        },
        "body": {"password": password, "private_key": private_key},
        "url": (
            "https://example.test/path?api_key="
            f"{openai_key}&token={bearer}&signature=signed-secret&ok=1"
        ),
        "cloud": f"aws_access_key_id={aws_key}",
    }

    redacted = redact_sensitive(payload)
    dumped = json.dumps(redacted, ensure_ascii=False)

    for secret in (
        openai_key,
        aws_key,
        bearer,
        password,
        "cookie-secret-value",
        "signed-secret",
        "MIIEvredactionprivatekeymaterial",
    ):
        assert secret not in dumped
    assert dumped.count("[REDACTED]") >= 8
    assert "ok=1" in dumped


def test_redact_sensitive_redacts_json_strings_without_persisting_original_values():
    secret = "json-body-token-secret"
    raw = json.dumps(
        {
            "request": {
                "headers": {"authorization": f"Bearer {secret}"},
                "query": f"https://example.test/callback?code={secret}&state=public",
            }
        }
    )

    redacted = redact_sensitive(raw)

    assert secret not in redacted
    assert "[REDACTED]" in redacted
    assert "state=public" in redacted
    assert redacted.startswith('{"request": {')


def test_redact_sensitive_preserves_pretty_json_layout_while_redacting_values():
    secret = "sk-pretty-json-secret"
    pretty = '{\n  "a": [\n    1\n  ],\n  "api_key": "' + secret + '"\n}'

    redacted = redact_sensitive(pretty)

    assert secret not in redacted
    assert redacted == '{\n  "a": [\n    1\n  ],\n  "api_key": "[REDACTED]"\n}'


def test_redact_sensitive_redacts_plain_auth_keys_in_structured_and_json_text():
    secret = "auth-secret"

    structured = redact_sensitive({"auth": secret, "nested": {"auth": secret}})
    embedded_json = redact_sensitive(json.dumps({"auth": secret}))
    query = redact_sensitive(f"https://example.test/callback?auth={secret}&ok=1")

    assert secret not in json.dumps(structured, ensure_ascii=False)
    assert secret not in embedded_json
    assert secret not in query
    assert structured["auth"] == "[REDACTED]"
    assert '"auth": "[REDACTED]"' in embedded_json
    assert "ok=1" in query


def test_cli_redacting_formatter_redacts_log_arguments_headers_and_error_reports():
    error_secret = "sk-cli-error-report-secret"
    exception_secret = "sk-cli-exception-secret"
    request_id = "public-request-id"
    formatter = _RedactingFormatter("%(levelname)s:%(message)s")
    cases = [
        {
            "msg": "error_report=%s",
            "args": (
                json.dumps(
                    {
                        "headers": {"Authorization": f"Bearer {error_secret}"},
                        "Cookie": "sid=cookie-secret",
                        "password": "pw-secret",
                        "url": f"https://example.test?api_key={error_secret}",
                    }
                ),
            ),
            "forbidden": (error_secret, "sid=cookie-secret", "pw-secret"),
            "visible": (),
        },
        {
            "msg": "request failed headers=%s url=%s request_id=%s",
            "args": (
                {
                    "authorization": f"Bearer {exception_secret}",
                    "x-api-key": exception_secret,
                    "set-cookie": "session=exception-cookie-secret",
                    "content-type": "application/json",
                },
                f"https://example.test/callback?token={exception_secret}&state=visible-state",
                request_id,
            ),
            "forbidden": (exception_secret, "exception-cookie-secret"),
            "visible": ("visible-state", request_id),
        },
    ]

    for case in cases:
        record = logging.LogRecord(
            name="supermedicine.cli.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg=case["msg"],
            args=case["args"],
            exc_info=None,
        )

        rendered = formatter.format(record)

        assert all(secret not in rendered for secret in case["forbidden"])
        assert "[REDACTED]" in rendered
        assert all(value in rendered for value in case["visible"])


def test_cli_formatter_and_tui_kernel_format_redact_plain_auth_fields():
    secret = "auth-secret"
    formatter = _RedactingFormatter("%(levelname)s:%(message)s")
    record = logging.LogRecord(
        name="supermedicine.cli.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="error_report=%s",
        args=(json.dumps({"auth": secret}),),
        exc_info=None,
    )

    cli_rendered = formatter.format(record)
    tui_rendered = SuperMedicineTUI._format_kernel_result(
        {"status": "success", "output": {"auth": secret, "ok": True}}
    )["message"]

    assert secret not in cli_rendered
    assert secret not in tui_rendered
    assert "[REDACTED]" in cli_rendered
    assert "[已隐藏]" in tui_rendered
    assert '\n  "ok": true' in tui_rendered
