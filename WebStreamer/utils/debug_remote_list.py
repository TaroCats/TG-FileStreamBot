

from pathlib import Path
from dotenv import load_dotenv
import logging
import asyncio
import argparse
import json
import sys
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Import after sys.path fix
from WebStreamer.utils.cloudreve import remote_list, search_download_by_url
# Load .env early so argparse defaults and env validation see values
load_dotenv()

# Ensure project root is on sys.path when running the script directly
# __file__ is WebStreamer/utils/debug_remote_list.py -> parents[2] is repo root


def ensure_min_env(verbose: bool = False) -> None:
    # Telegram-related vars required by WebStreamer.vars even if unused here
    os.environ.setdefault("API_ID", os.environ.get("API_ID", "12345"))
    os.environ.setdefault("API_HASH", os.environ.get("API_HASH", "testhash"))
    os.environ.setdefault("BOT_TOKEN", os.environ.get("BOT_TOKEN", "123:abc"))
    # Optional conveniences
    os.environ.setdefault("HASH_LENGTH", os.environ.get("HASH_LENGTH", "6"))

    if verbose:
        logging.info(
            "Using minimal TG env: API_ID=%s, API_HASH=%s, BOT_TOKEN=%s",
            os.environ.get("API_ID"),
            os.environ.get("API_HASH"),
            os.environ.get("BOT_TOKEN"),
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Debug Cloudreve remote_list")
    p.add_argument("--api-url", dest="api_url",
                   default=os.environ.get("CLOUDEREVE_API_URL"))
    p.add_argument("--username", dest="username", default=os.environ.get(
        "CLOUDEREVE_USERNAME") or os.environ.get("CLOUDEREVE_EMAIL"))
    p.add_argument("--password", dest="password",
                   default=os.environ.get("CLOUDEREVE_PASSWORD"))
    p.add_argument("--download-path", dest="download_path",
                   default=os.environ.get("CLOUDEREVE_DOWNLOAD_PATH"))
    p.add_argument("--category", dest="category", default="downloaded",
                   choices=["general", "downloading", "downloaded"])
    p.add_argument("--page-size", dest="page_size", type=int, default=20)
    p.add_argument("--timeout", dest="timeout", type=int, default=15)
    p.add_argument("--skew-seconds", dest="skew_seconds", type=int, default=60)
    p.add_argument("--search-url", dest="search_url",
                   default=os.environ.get("http://tg.taro.cat/75d9d051"))
    p.add_argument("--verbose", dest="verbose", action="store_true")
    return p.parse_args()


def apply_cloudreve_env(cfg: argparse.Namespace) -> None:
    os.environ["USE_CLOUDEREVE"] = "1"
    if cfg.api_url:
        os.environ["CLOUDEREVE_API_URL"] = cfg.api_url
    if cfg.username:
        os.environ["CLOUDEREVE_USERNAME"] = cfg.username
    if cfg.password:
        os.environ["CLOUDEREVE_PASSWORD"] = cfg.password
    if cfg.download_path:
        os.environ["CLOUDEREVE_DOWNLOAD_PATH"] = cfg.download_path


def validate_env() -> None:
    missing = []
    for k in [
        "CLOUDEREVE_API_URL",
        "CLOUDEREVE_USERNAME",
        "CLOUDEREVE_PASSWORD",
        "CLOUDEREVE_DOWNLOAD_PATH",
    ]:
        if not os.environ.get(k):
            missing.append(k)
    if missing:
        msg = (
            "Missing Cloudreve configuration: " + ", ".join(missing) +
            "\nProvide via CLI args or environment variables."
        )
        raise SystemExit(msg)


def _extract_tasks_list(result: dict):
    """Extract a list of tasks from remote_list response, trying common keys."""
    data_obj = result.get("data") if isinstance(result, dict) else None
    candidates = None
    if isinstance(data_obj, dict):
        for key in ("task", "items", "list", "workflows"):
            v = data_obj.get(key)
            if isinstance(v, list):
                candidates = v
                break
    if candidates is None and isinstance(result, dict):
        for k, v in result.items():
            if isinstance(v, list):
                candidates = v
                break
    return candidates


def _search_download_by_url(result: dict, url: str):
    """Best-effort search of a download task by source URL in remote_list result."""
    candidates = _extract_tasks_list(result)
    if not candidates:
        return None
    for item in candidates:
        try:
            src = (
                item.get("summary", {})
                .get("props", {})
                .get("src_str")
            )
            if src == url:
                return {
                    "name": item.get("summary", {}).get("props", {}).get("download", {}).get("name"),
                    "status": item.get("status"),
                    "progress": (
                        item.get("summary", {})
                        .get("props", {})
                        .get("download", {})
                        .get("files", {})
                        .get("progress")
                    ),
                    "raw": item,
                }
        except Exception:
            continue
    return None


async def main(cfg: argparse.Namespace) -> int:
    try:
        result = await remote_list(
            page_size=int(cfg.page_size),
            category=str(cfg.category),
            timeout=int(cfg.timeout),
            skew_seconds=int(cfg.skew_seconds),
        )
        # tasks = _extract_tasks_list(result)
        # print(json.dumps(result or {"match": None},
        #       ensure_ascii=False, indent=2))
        # logging.info("remote_list fetched: category=%s, count=%s",
        #              cfg.category, len(tasks) if tasks else 0)
        # If search_url is provided, try to locate the specific task

        matched = await search_download_by_url(result=result, url='https://tg.taro.cat/64/video-2025-11-06_08-45-48.mp4?hash=4d8125', category='downloading')
        print(json.dumps(matched, ensure_ascii=False, indent=2))
    except Exception as e:
        logging.exception("remote_list failed: %s", e)
        print(f"ERROR: {e}")
        return 2


if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    ensure_min_env(verbose=args.verbose)
    apply_cloudreve_env(args)
    validate_env()
    sys.exit(asyncio.run(main(args)))
