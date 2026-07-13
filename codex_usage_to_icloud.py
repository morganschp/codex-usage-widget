#!/usr/bin/env python3
"""Export Codex 5-hour and weekly rate-limit percentages to Scriptable iCloud."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FIVE_HOURS_MINS = 5 * 60
ONE_WEEK_MINS = 7 * 24 * 60
OUTPUT_FILENAME = "codex-limits.json"
REQUEST_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Window:
    duration_mins: int
    used_percent: float
    resets_at: int | None
    priority: int
    source: str


def find_codex() -> str:
    candidates = [
        "/Applications/ChatGPT.app/Contents/Resources/codex",
        "/Applications/Codex.app/Contents/Resources/codex",
        str(Path.home() / "Applications" / "ChatGPT.app" / "Contents" / "Resources" / "codex"),
        str(Path.home() / "Applications" / "Codex.app" / "Contents" / "Resources" / "codex"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError(
        "Could not find the Codex executable bundled with the ChatGPT/Codex "
        "desktop app. Move the app to Applications, open it, and sign in."
    )


def scriptable_directory() -> Path:
    override = os.environ.get("SCRIPTABLE_ICLOUD_DIR")
    if override:
        return Path(override).expanduser()

    return (
        Path.home()
        / "Library"
        / "Mobile Documents"
        / "iCloud~dk~simonbs~Scriptable"
        / "Documents"
    )


def send_message(proc: subprocess.Popen[str], message: dict[str, Any]) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    proc.stdin.flush()


def wait_for_response(
    proc: subprocess.Popen[str], request_id: int, timeout_seconds: int
) -> dict[str, Any]:
    assert proc.stdout is not None
    deadline = time.monotonic() + timeout_seconds

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for Codex response id={request_id}")

        ready, _, _ = select.select([proc.stdout], [], [], remaining)
        if not ready:
            raise TimeoutError(f"Timed out waiting for Codex response id={request_id}")

        line = proc.stdout.readline()
        if line == "":
            raise RuntimeError("Codex app-server exited before returning a response.")

        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue

        if message.get("id") != request_id:
            continue

        if "error" in message:
            error = message["error"]
            raise RuntimeError(
                f"Codex app-server error {error.get('code')}: {error.get('message')}"
            )

        result = message.get("result")
        if not isinstance(result, dict):
            raise RuntimeError(f"Unexpected response for id={request_id}: {message}")
        return result


def fetch_rate_limits() -> dict[str, Any]:
    codex = find_codex()

    with tempfile.TemporaryFile(mode="w+t") as stderr_file:
        proc = subprocess.Popen(
            [codex, "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            bufsize=1,
        )

        try:
            send_message(
                proc,
                {
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "clientInfo": {
                            "name": "codex_limits_widget",
                            "title": "Codex Limits Widget",
                            "version": "1.0.0",
                        }
                    },
                },
            )
            wait_for_response(proc, 1, REQUEST_TIMEOUT_SECONDS)
            send_message(proc, {"method": "initialized", "params": {}})
            send_message(proc, {"method": "account/rateLimits/read", "id": 2})
            return wait_for_response(proc, 2, REQUEST_TIMEOUT_SECONDS)
        except Exception as exc:
            stderr_file.seek(0)
            diagnostics = stderr_file.read().strip()
            if diagnostics:
                raise RuntimeError(f"{exc}\nCodex diagnostics:\n{diagnostics[-4000:]}") from exc
            raise
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)


def collect_windows(result: dict[str, Any]) -> list[Window]:
    windows: list[Window] = []

    def add_bucket(bucket: Any, priority: int, source: str) -> None:
        if not isinstance(bucket, dict):
            return

        for field in ("primary", "secondary"):
            item = bucket.get(field)
            if not isinstance(item, dict):
                continue

            duration = item.get("windowDurationMins")
            used = item.get("usedPercent")
            if not isinstance(duration, (int, float)) or not isinstance(used, (int, float)):
                continue

            resets_at = item.get("resetsAt")
            windows.append(
                Window(
                    duration_mins=int(round(duration)),
                    used_percent=float(used),
                    resets_at=int(resets_at)
                    if isinstance(resets_at, (int, float))
                    else None,
                    priority=priority,
                    source=f"{source}.{field}",
                )
            )

    add_bucket(result.get("rateLimits"), 0, "rateLimits")

    buckets = result.get("rateLimitsByLimitId")
    if isinstance(buckets, dict):
        for limit_id, bucket in buckets.items():
            priority = 1 if limit_id == "codex" else 2
            add_bucket(bucket, priority, f"rateLimitsByLimitId.{limit_id}")

    return windows


def choose_window(windows: list[Window], target_duration: int, label: str) -> Window:
    exact = [w for w in windows if w.duration_mins == target_duration]
    if exact:
        return sorted(exact, key=lambda w: w.priority)[0]

    available = sorted({w.duration_mins for w in windows})
    raise RuntimeError(
        f"Could not find the {label} window ({target_duration} minutes). "
        f"Available window durations: {available or 'none'}"
    )


def remaining_percent(used_percent: float) -> int:
    return int(round(max(0.0, min(100.0, 100.0 - used_percent))))


def write_output(result: dict[str, Any]) -> Path:
    windows = collect_windows(result)
    weekly = choose_window(windows, ONE_WEEK_MINS, "weekly")

    five_hour_windows = [w for w in windows if w.duration_mins == FIVE_HOURS_MINS]
    if five_hour_windows:
        five_hour = sorted(five_hour_windows, key=lambda w: w.priority)[0]
        five_hour_percent = remaining_percent(five_hour.used_percent)
        five_hour_resets_at = five_hour.resets_at
    else:
        # Some account states omit the 5-hour window entirely while continuing
        # to return the weekly window. In that state there is no active 5-hour
        # consumption to subtract, so report the allowance as fully remaining.
        five_hour_percent = 100
        five_hour_resets_at = None

    output = {
        "fiveHourPercent": five_hour_percent,
        "fiveHourResetsAt": five_hour_resets_at,
        "weeklyPercent": remaining_percent(weekly.used_percent),
        "weeklyResetsAt": weekly.resets_at,
        "updatedAt": int(time.time()),
        "basis": "remaining",
    }

    directory = scriptable_directory()
    if not directory.is_dir():
        raise RuntimeError(
            f"Scriptable iCloud folder was not found at:\n{directory}\n"
            "Install and open Scriptable on your iPhone, enable iCloud for it, "
            "and wait for the Scriptable folder to appear in iCloud Drive."
        )

    destination = directory / OUTPUT_FILENAME
    temporary = directory / f".{OUTPUT_FILENAME}.tmp"
    temporary.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    return destination


def main() -> int:
    try:
        result = fetch_rate_limits()
        destination = write_output(result)
        data = json.loads(destination.read_text(encoding="utf-8"))
        print(
            f"Wrote {destination}: "
            f"5h {data['fiveHourPercent']}%, weekly {data['weeklyPercent']}% remaining"
        )
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
