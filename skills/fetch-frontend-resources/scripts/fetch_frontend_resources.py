#!/usr/bin/env python3
"""Snapshot statically referenced frontend JavaScript and JSON resources."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html.parser
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import date
from pathlib import Path
from urllib.parse import quote


JS_IMPORT_RE = re.compile(
    r"(?:\bfrom\s*|\bimport\s*(?:\(\s*)?)[\"'`]([^\"'`\r\n]{1,1000}?\.(?:m?js)(?:\?[^\"'`\r\n]*)?)[\"'`]",
    re.IGNORECASE,
)
ABSOLUTE_JS_RE = re.compile(
    r"[\"'`]((?:https?:)?//[^\"'`\r\n]{1,1000}?\.(?:m?js)(?:\?[^\"'`\r\n]*)?)[\"'`]",
    re.IGNORECASE,
)
JSON_REF_RE = re.compile(
    r"[\"'`]([^\"'`\r\n]{1,1000}?\.json(?:\?[^\"'`\r\n]*)?)[\"'`]",
    re.IGNORECASE,
)
DYNAMIC_MARKERS = ("${", "{{", "<", "+ encodeURIComponent(")
IMPORT_CALL_RE = re.compile(r"\bimport\s*\(\s*([^)]{1,2000})\)", re.IGNORECASE)
LITERAL_EXPRESSION_RE = re.compile(r"^[\"'`]([^\"'`\r\n]+)[\"'`]$")
WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


class AssetLinkParser(html.parser.HTMLParser):
    """Collect JavaScript entrypoints from script and preload elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []
        self.base_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "base" and attributes.get("href") and self.base_href is None:
            self.base_href = attributes["href"]
        if tag.lower() == "script" and attributes.get("src"):
            self.urls.append(attributes["src"])
            return
        if tag.lower() != "link":
            return
        rel = set(attributes.get("rel", "").lower().split())
        is_script_preload = "modulepreload" in rel or (
            "preload" in rel and attributes.get("as", "").lower() == "script"
        )
        if is_script_preload and attributes.get("href"):
            self.urls.append(attributes["href"])


def absolute_http_url(reference: str, base: str) -> str | None:
    candidate = urllib.parse.urljoin(base, reference.strip())
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    return parsed._replace(fragment="").geturl()


def is_template_or_api_json(url: str, reference: str, context: str) -> str | None:
    if any(marker in reference for marker in DYNAMIC_MARKERS):
        return "not fetched: templated or runtime-dependent JSON reference"
    path = urllib.parse.urlsplit(url).path.lower()
    if context in ("fetch", "xhr", "unknown") and ("/api/" in path or path.startswith("/api/")):
        return "not fetched: API response route, not a static JSON asset"
    return None


def application_slug(name: str) -> str:
    ascii_name = name.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not slug:
        raise ValueError("Application name must contain at least one ASCII letter or digit.")
    return slug


def host_directory(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or "unknown-host"
    if ":" in host:
        host = host.replace(":", "-")
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port and port not in (80, 443):
        host = f"{host}-port-{port}"
    return f"{parsed.scheme.lower()}_{host}"


def safe_path_segment(segment: str) -> str:
    """Encode URL path components so they cannot become Windows path syntax."""
    encoded = quote(segment, safe="-._~ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
    if encoded in (".", ".."):
        encoded = encoded.replace(".", "%2E")
    while encoded.endswith("."):
        encoded = encoded[:-1] + "%2E"
    stem = encoded.split(".", 1)[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        encoded = "_" + encoded
    if len(encoded) > 180:
        suffix = hashlib.sha256(segment.encode("utf-8")).hexdigest()[:12]
        encoded = f"{encoded[:150]}--{suffix}"
    return encoded


def output_path(root: Path, category: str, url: str) -> Path:
    parsed = urllib.parse.urlsplit(url)
    raw_parts = [part for part in parsed.path.split("/") if part]
    safe_parts = [safe_path_segment(part) for part in raw_parts]
    if not safe_parts:
        safe_parts = ["index.js" if category == "javascript" else "index.json"]
    path = root / category / host_directory(url)
    for part in safe_parts[:-1]:
        path /= part
    filename = safe_parts[-1]
    identity = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    stem, extension = os.path.splitext(filename)
    filename = f"{stem}--{identity}{extension}"
    target = path / filename
    resolved_root = root.resolve()
    resolved_target = target.resolve(strict=False)
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError("Resolved asset path escapes the snapshot directory") from error
    if os.name == "nt" and len(str(target)) > 240:
        raise ValueError("Asset path is too long for a portable Windows snapshot")
    return target


def fetch(url: str, timeout: float) -> tuple[int, str, str, bytes]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Codex-Frontend-Snapshot/1.0",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return (
                response.status,
                response.headers.get("Content-Type", ""),
                response.geturl(),
                body,
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            error.headers.get("Content-Type", "") if error.headers else "",
            error.geturl(),
            error.read(),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-name", required=True, help="Application name for the snapshot folder")
    parser.add_argument("--base-url", required=True, help="Absolute URL of the application's main page")
    parser.add_argument(
        "--entry-url",
        action="append",
        default=[],
        help="JavaScript entry URL; repeat for multiple entries. If omitted, entries are discovered from the main page.",
    )
    parser.add_argument("--output-root", default=".scratch", help="Snapshot parent directory (default: .scratch)")
    parser.add_argument("--output-dir", help="Exact snapshot directory; overrides the default name under --output-root")
    parser.add_argument("--date", help="Snapshot date in YYYY-MM-DD format (default: local system date)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout in seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = absolute_http_url(args.base_url, args.base_url)
    if not base_url:
        print("Error: --base-url must be an absolute HTTP or HTTPS URL without embedded credentials.", file=sys.stderr)
        return 2
    try:
        capture_date = date.fromisoformat(args.date) if args.date else date.today()
        slug = application_slug(args.app_name)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    seed_urls: list[str] = []
    page_status: int | None = None
    page_error: str | None = None
    page_reference_base = base_url
    if args.entry_url:
        for entry in args.entry_url:
            normalized = absolute_http_url(entry, base_url)
            if not normalized:
                print(f"Error: invalid entry URL: {entry}", file=sys.stderr)
                return 2
            seed_urls.append(normalized)
    else:
        try:
            page_status, page_type, final_page_url, page_body = fetch(base_url, args.timeout)
            if not 200 <= page_status < 300:
                page_error = f"main page returned HTTP {page_status}"
            else:
                charset_match = re.search(r"charset\s*=\s*([\w.-]+)", page_type, re.IGNORECASE)
                charset = charset_match.group(1) if charset_match else "utf-8"
                document = page_body.decode(charset, errors="replace")
                parser = AssetLinkParser()
                parser.feed(document)
                page_reference_base = urllib.parse.urljoin(final_page_url, parser.base_href or "")
                seed_urls = [
                    normalized
                    for ref in parser.urls
                    if (normalized := absolute_http_url(ref, page_reference_base))
                ]
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as error:
            page_error = str(error)

    if not seed_urls:
        detail = page_error or "no script or module-preload URLs were found in the main page"
        print(f"No JavaScript entry URLs found ({detail}). Provide one or more --entry-url values.", file=sys.stderr)
        return 1

    parent = Path(args.output_root)
    destination = Path(args.output_dir) if args.output_dir else parent / f"{slug}-frontend-{capture_date.isoformat()}"
    if destination.exists():
        print(
            f"Output directory already exists: {destination}. Choose a different --date or --output-root; "
            "the existing snapshot was left untouched.",
            file=sys.stderr,
        )
        return 1

    try:
        destination.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        print(f"Could not create snapshot directory {destination}: {error}", file=sys.stderr)
        return 1
    js_queue: deque[str] = deque(seed_urls)
    seen_js: set[str] = set()
    seen_json: set[str] = set()
    manifest_rows: list[dict[str, str | int]] = []
    reference_rows: list[dict[str, str | int]] = []
    seen_reference_rows: set[tuple[str, str, str, str, str]] = set()
    json_paths: list[Path] = []
    js_bytes = 0
    json_bytes = 0

    def record_reference(
        reference_type: str,
        referring_url: str,
        reference_text: str,
        url: str,
        result: str,
        http_status: str | int = "",
    ) -> None:
        key = (reference_type, referring_url, reference_text, url, result)
        if key in seen_reference_rows:
            return
        seen_reference_rows.add(key)
        reference_rows.append(
            {
                "reference_type": reference_type,
                "referring_url": referring_url,
                "reference_text": reference_text,
                "url": url,
                "result": result,
                "http_status": http_status,
            }
        )

    def save_asset(
        category: str, url: str, reference_type: str, referring_url: str = ""
    ) -> tuple[bool, bytes, str]:
        nonlocal js_bytes, json_bytes
        try:
            status, content_type, final_url, body = fetch(url, args.timeout)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as error:
            record_reference(reference_type, referring_url, url, url, f"failed: {error}")
            return False, b"", url
        if not 200 <= status < 300:
            record_reference(reference_type, referring_url, url, final_url, "failed: non-success HTTP response", status)
            return False, b"", final_url
        try:
            target = output_path(destination, category, url)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        except (OSError, ValueError) as error:
            record_reference(reference_type, referring_url, url, final_url, f"failed: could not save file: {error}", status)
            return False, b"", final_url
        relative = target.relative_to(destination).as_posix()
        manifest_rows.append(
            {
                "path": relative,
                "source_url": url,
                "final_url": final_url,
                "http_status": status,
                "content_type": content_type,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
        if "text/html" in content_type.lower():
            record_reference(reference_type, referring_url, url, final_url, "saved as received, but response content type is HTML", status)
        if category == "javascript":
            js_bytes += len(body)
        else:
            json_bytes += len(body)
            json_paths.append(target)
        return True, body, final_url

    while js_queue:
        url = js_queue.popleft()
        if url in seen_js:
            continue
        seen_js.add(url)
        saved, body, final_js_url = save_asset("javascript", url, "javascript")
        if not saved:
            continue
        source = body.decode("utf-8", errors="replace")
        js_refs = sorted({match.group(1) for match in JS_IMPORT_RE.finditer(source)} | {match.group(1) for match in ABSOLUTE_JS_RE.finditer(source)})
        for reference in js_refs:
            normalized = absolute_http_url(reference, final_js_url)
            if normalized and normalized not in seen_js:
                js_queue.append(normalized)
            elif not normalized:
                record_reference("javascript", final_js_url, reference, reference, "not fetched: could not resolve as an HTTP(S) URL")

        for match in IMPORT_CALL_RE.finditer(source):
            expression = match.group(1).strip()
            literal = LITERAL_EXPRESSION_RE.fullmatch(expression)
            if not literal:
                record_reference("javascript", final_js_url, expression, "", "not fetched: computed dynamic import; runtime evaluation required")

        for match in JSON_REF_RE.finditer(source):
            reference = match.group(1)
            if re.search(r"\+\s*$", source[:match.start()]) or re.match(r"\s*\+", source[match.end():]):
                record_reference(
                    "json",
                    final_js_url,
                    reference,
                    "",
                    "not fetched: JSON URL is assembled from runtime string concatenation",
                )
                continue
            prefix = source[max(0, match.start() - 160):match.start()].lower()
            context = "import" if re.search(r"\bimport\s*(?:\(\s*)?$", prefix) else (
                "fetch" if re.search(r"\bfetch\s*\(\s*$", prefix) else (
                    "xhr" if re.search(r"\.open\s*\(\s*[\"'](?:get|post)[\"']\s*,\s*$", prefix) else "unknown"
                )
            )
            if context == "unknown" and not urllib.parse.urlsplit(reference).scheme and not reference.startswith("/"):
                record_reference("json", final_js_url, reference, "", "not fetched: relative JSON string has no clear asset-loading context")
                continue
            reference_base = page_reference_base if context in ("fetch", "xhr") else final_js_url
            normalized = absolute_http_url(reference, reference_base)
            if not normalized:
                reason = "not fetched: could not resolve as an HTTP(S) URL"
                record_reference("json", final_js_url, reference, reference, reason)
                continue
            exclusion = is_template_or_api_json(normalized, reference, context)
            if exclusion:
                record_reference("json", final_js_url, reference, normalized, exclusion)
                continue
            if normalized in seen_json:
                continue
            seen_json.add(normalized)
            save_asset("json", normalized, "json", final_js_url)

    valid_json = 0
    invalid_json = 0
    for path in json_paths:
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
            valid_json += 1
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            invalid_json += 1
            row = next((item for item in manifest_rows if item["path"] == path.relative_to(destination).as_posix()), {})
            record_reference(
                "json",
                str(row.get("source_url", "")),
                "response body",
                str(row.get("final_url", "")),
                "saved as received, but body is not valid JSON",
                row.get("http_status", ""),
            )

    metadata_errors: list[str] = []
    metadata_specs = [
        (destination / "manifest.csv", ["path", "source_url", "final_url", "http_status", "content_type", "bytes", "sha256"], manifest_rows),
        (destination / "snapshot-references.csv", ["reference_type", "referring_url", "reference_text", "url", "result", "http_status"], reference_rows),
    ]
    for output_pathname, columns, rows in metadata_specs:
        try:
            with output_pathname.open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as error:
            metadata_errors.append(f"{output_pathname.name}: {error}")

    entry_list = "\n".join(f"- `{url}`" for url in seed_urls)
    saved_js_count = sum(1 for row in manifest_rows if str(row['path']).startswith('javascript/'))
    capture_status = "complete" if not reference_rows and not metadata_errors else "partial"
    if saved_js_count == 0:
        capture_status = "failed: no JavaScript files were saved"
    readme = f"""# Frontend asset snapshot — {capture_date.isoformat()}

Application: {args.app_name}

Main URL: {base_url}

Capture date: {capture_date.isoformat()}

Capture status: {capture_status}

Entry URLs:
{entry_list}

- JavaScript files saved: {sum(1 for row in manifest_rows if str(row['path']).startswith('javascript/'))} ({js_bytes:,} bytes)
- JSON files saved: {len(json_paths)} ({json_bytes:,} bytes; {valid_json} parsed as valid JSON, {invalid_json} did not)
- Failed or intentionally unresolved references: {len(reference_rows)}; see `snapshot-references.csv`.
{f"- Metadata write problems: {'; '.join(metadata_errors)}" if metadata_errors else ""}

Files are stored as received. `manifest.csv` records source and final URLs, HTTP status, content type, byte length, and SHA-256. Only statically discoverable JavaScript and JSON URLs were followed; computed runtime chunks and API responses may require parameters, authentication, or application state and are not claimed as captured.
"""
    try:
        (destination / "README.md").write_text(readme, encoding="utf-8")
    except OSError as error:
        metadata_errors.append(f"README.md: {error}")
        print(f"Could not write README.md: {error}", file=sys.stderr)

    print(f"Snapshot: {destination}")
    print(f"JavaScript files: {saved_js_count} ({js_bytes:,} bytes)")
    print(f"JSON files: {len(json_paths)} ({json_bytes:,} bytes; {valid_json} valid JSON, {invalid_json} invalid JSON)")
    print(f"Unresolved/failed references: {len(reference_rows)}")
    return 1 if saved_js_count == 0 or metadata_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
