'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditors: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditTime: 2025-10-22 09:45:08
Description: 
'''
# Cloudreve helper functions
from typing import Any as _AnyType
import json
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
import time
import aiohttp
from datetime import datetime

# Module-level cache for token object
TOKEN_OBJ: Optional[Dict[str, Any]] = None

# Internal helper utilities (DRY): HTTP, parsing, validation


def _to_epoch_sec(v: _AnyType) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        try:
            dt = datetime.fromisoformat(s)
            return int(dt.timestamp())
        except Exception:
            pass
        try:
            t = int(float(s))
        except Exception:
            return None
    else:
        try:
            t = int(v)
        except Exception:
            return None
    if t > 10**12:
        t = t // 1000
    return t


def _ensure_api_success(result: Dict[str, Any], action: str) -> None:
    code = result.get("code")
    if code == 0:
        msg = result.get("msg") or f"{action} failed"
        raise RuntimeError(f"Cloudreve {action} error: code={code}, msg={msg}")


def _extract_token_obj(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data") or {}
    token_obj = data.get("token") or data
    if not isinstance(token_obj, dict):
        raise RuntimeError("Cloudreve token object invalid")
    if not token_obj.get("access_token"):
        raise RuntimeError("Cloudreve access_token not found in response")
    return token_obj


def _http_post_json_sync(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Dict[str, Any]:
    hdrs = dict(headers or {})
    hdrs.setdefault("Content-Type", "application/json")
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=hdrs)
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    try:
        return json.loads(body)
    except Exception:
        snippet = body[:200] if isinstance(
            body, (bytes, bytearray)) else str(body)[:200]
        raise RuntimeError(f"Cloudreve invalid response: {snippet}")


async def _http_post_json_async(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Dict[str, Any]:
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            text = await resp.text()
            try:
                return json.loads(text)
            except Exception:
                raise RuntimeError(f"Cloudreve invalid response: {text[:200]}")


def login_and_cache_cloudreve_token(api_url: str, email: str, password: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Login to Cloudreve, cache the token object globally, and return it.
    (Synchronous)
    """
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    api_base = api_url.rstrip("/")
    token_url = f"{api_base}/api/v4/session/token"

    result = _http_post_json_sync(
        token_url,
        {"email": email, "password": password},
        None,
        timeout,
    )
    _ensure_api_success(result, "login")
    token_obj = _extract_token_obj(result)

    global TOKEN_OBJ
    TOKEN_OBJ = token_obj
    return token_obj


async def async_login_and_cache_cloudreve_token(api_url: str, email: str, password: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Login to Cloudreve asynchronously, cache the token object globally, and return it.
    """
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    api_base = api_url.rstrip("/")
    token_url = f"{api_base}/api/v4/session/token"

    result = await _http_post_json_async(
        token_url,
        {"email": email, "password": password},
        None,
        timeout,
    )
    _ensure_api_success(result, "login")
    token_obj = _extract_token_obj(result)

    global TOKEN_OBJ
    TOKEN_OBJ = token_obj
    return token_obj


def refresh_cloudreve_token(api_url: str, refresh_token: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Refresh Cloudreve session token and update global cache. (Synchronous)
    """
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    api_base = api_url.rstrip("/")
    refresh_url = f"{api_base}/api/v4/session/token/refresh"

    result = _http_post_json_sync(
        refresh_url,
        {"refresh_token": refresh_token},
        None,
        timeout,
    )
    _ensure_api_success(result, "refresh")
    token_obj = _extract_token_obj(result)

    global TOKEN_OBJ
    old_refresh = TOKEN_OBJ.get("refresh_token") if TOKEN_OBJ else None
    if not token_obj.get("refresh_token") and old_refresh:
        token_obj["refresh_token"] = old_refresh

    TOKEN_OBJ = token_obj
    return token_obj


async def async_refresh_cloudreve_token(api_url: str, refresh_token: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Refresh Cloudreve session token asynchronously and update global cache.
    """
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    api_base = api_url.rstrip("/")
    refresh_url = f"{api_base}/api/v4/session/token/refresh"

    result = await _http_post_json_async(
        refresh_url,
        {"refresh_token": refresh_token},
        None,
        timeout,
    )
    _ensure_api_success(result, "refresh")
    token_obj = _extract_token_obj(result)

    global TOKEN_OBJ
    old_refresh = TOKEN_OBJ.get("refresh_token") if TOKEN_OBJ else None
    if not token_obj.get("refresh_token") and old_refresh:
        token_obj["refresh_token"] = old_refresh

    TOKEN_OBJ = token_obj
    return token_obj


def get_cloudreve_access_token(api_url: str, email: str, password: str, timeout: int = 15) -> str:
    """
    Convenience function: ensure login & cache, then return access_token. (Sync)
    """
    token_obj = login_and_cache_cloudreve_token(
        api_url, email, password, timeout)
    return token_obj["access_token"]


async def async_get_cloudreve_access_token(api_url: str, email: str, password: str, timeout: int = 15) -> str:
    """
    Convenience function: async ensure login & cache, then return access_token.
    """
    token_obj = await async_login_and_cache_cloudreve_token(api_url, email, password, timeout)
    return token_obj["access_token"]


def get_cloudreve_token_obj() -> Optional[Dict[str, Any]]:
    """
    Return the cached token object if available.
    """
    return TOKEN_OBJ


def ensure_valid_cloudreve_token(api_url: str, email: str, password: str, skew_seconds: int = 60, timeout: int = 15) -> Dict[str, Any]:
    """
    Ensure a valid token is cached; refresh or re-login if near/after expiry. (Sync)
    """
    global TOKEN_OBJ

    if TOKEN_OBJ is None:
        TOKEN_OBJ = login_and_cache_cloudreve_token(
            api_url, email, password, timeout)
        return TOKEN_OBJ

    now = int(time.time())
    access_expires = _to_epoch_sec(TOKEN_OBJ.get("access_expires"))
    refresh_expires = _to_epoch_sec(TOKEN_OBJ.get("refresh_expires"))
    refresh_token = TOKEN_OBJ.get("refresh_token")

    need_refresh = False
    if access_expires is not None:
        need_refresh = now >= (access_expires - max(0, int(skew_seconds)))

    if need_refresh:
        if refresh_token and (refresh_expires is None or now < refresh_expires):
            try:
                TOKEN_OBJ = refresh_cloudreve_token(
                    api_url, refresh_token, timeout)
                return TOKEN_OBJ
            except Exception:
                pass
        TOKEN_OBJ = login_and_cache_cloudreve_token(
            api_url, email, password, timeout)

    return TOKEN_OBJ


async def async_ensure_valid_cloudreve_token(api_url: str, email: str, password: str, skew_seconds: int = 60, timeout: int = 15) -> Dict[str, Any]:
    """
    Ensure a valid token is cached; refresh or re-login if near/after expiry. (Async)
    """
    global TOKEN_OBJ

    if TOKEN_OBJ is None:
        TOKEN_OBJ = await async_login_and_cache_cloudreve_token(api_url, email, password, timeout)
        return TOKEN_OBJ

    now = int(time.time())
    access_expires = _to_epoch_sec(TOKEN_OBJ.get("access_expires"))
    refresh_expires = _to_epoch_sec(TOKEN_OBJ.get("refresh_expires"))
    refresh_token = TOKEN_OBJ.get("refresh_token")

    need_refresh = False
    if access_expires is not None:
        need_refresh = now >= (access_expires - max(0, int(skew_seconds)))

    if need_refresh:
        if refresh_token and (refresh_expires is None or now < refresh_expires):
            try:
                TOKEN_OBJ = await async_refresh_cloudreve_token(api_url, refresh_token, timeout)
                return TOKEN_OBJ
            except Exception:
                pass
        TOKEN_OBJ = await async_login_and_cache_cloudreve_token(api_url, email, password, timeout)

    return TOKEN_OBJ


def get_valid_cloudreve_access_token(api_url: str, email: str, password: str, skew_seconds: int = 60, timeout: int = 15) -> str:
    """
    Convenience: ensure valid token and return current access_token. (Sync)
    """
    token_obj = ensure_valid_cloudreve_token(
        api_url, email, password, skew_seconds, timeout)
    return token_obj["access_token"]


async def async_get_valid_cloudreve_access_token(api_url: str, email: str, password: str, skew_seconds: int = 60, timeout: int = 15) -> str:
    """
    Convenience: async ensure valid token and return current access_token.
    """
    token_obj = await async_ensure_valid_cloudreve_token(api_url, email, password, skew_seconds, timeout)
    return token_obj["access_token"]


def remote_download(api_url: str, access_token: str, dst: str, src: Any, timeout: int = 15, endpoint: str = "/api/v4/remote/download") -> Dict[str, Any]:
    """
    Create a remote download task. (Synchronous)

    Headers: Authorization: Bearer <access_token>
    Body: {"dst": dst, "src": [string(url)]}
    """
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    if not access_token:
        raise ValueError("Cloudreve access_token is empty")
    if not dst:
        raise ValueError("Remote download dst is empty")

    # Normalize src to a list of one string as required
    if isinstance(src, (list, tuple)):
        if len(src) == 0:
            raise ValueError("Remote download src list is empty")
        url_list = [str(src[0])]
    else:
        url_list = [str(src)]

    api_base = api_url.rstrip("/")
    url = f"{api_base}{endpoint}"

    result = _http_post_json_sync(
        url,
        {"dst": dst, "src": url_list},
        {"Authorization": f"Bearer {access_token}"},
        timeout,
    )
    # Cloudreve API returns code==0 on failure per user clarification
    _ensure_api_success(result, "remote_download")
    return result


async def async_remote_download(api_url: str, access_token: str, dst: str, src: Any, timeout: int = 15, endpoint: str = "/api/v4/remote/download") -> Dict[str, Any]:
    """
    Create a remote download task. (Asynchronous)

    Headers: Authorization: Bearer <access_token>
    Body: {"dst": dst, "src": [string(url)]}
    """
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    if not access_token:
        raise ValueError("Cloudreve access_token is empty")
    if not dst:
        raise ValueError("Remote download dst is empty")

    # Normalize src to a list of one string as required
    if isinstance(src, (list, tuple)):
        if len(src) == 0:
            raise ValueError("Remote download src list is empty")
        url_list = [str(src[0])]
    else:
        url_list = [str(src)]

    api_base = api_url.rstrip("/")
    url = f"{api_base}{endpoint}"

    result = await _http_post_json_async(
        url,
        {"dst": dst, "src": url_list},
        {"Authorization": f"Bearer {access_token}"},
        timeout,
    )
    _ensure_api_success(result, "remote_download")
    return result


def remote_download_url_from_vars(url: str, timeout: int = 15, endpoint: str = "/api/v4/remote/download", skew_seconds: int = 60) -> Dict[str, Any]:
    """
    Convenience: use Var config, auto ensure token, then remote download URL. (Sync)
    Reads: Var.USE_CLOUDEREVE, Var.CLOUDEREVE_API_URL, Var.CLOUDEREVE_USERNAME,
           Var.CLOUDEREVE_PASSWORD, Var.CLOUDEREVE_DOWNLOAD_PATH
    """
    from WebStreamer.vars import Var
    if not Var.USE_CLOUDEREVE:
        raise ValueError("Cloudreve is disabled (USE_CLOUDEREVE is false)")
    api_url = Var.CLOUDEREVE_API_URL
    email = Var.CLOUDEREVE_USERNAME
    password = Var.CLOUDEREVE_PASSWORD
    dst = Var.CLOUDEREVE_DOWNLOAD_PATH
    # Ensure token freshness
    access_token = get_valid_cloudreve_access_token(
        api_url, email, password, skew_seconds=skew_seconds, timeout=timeout)
    # Delegate to base function
    return remote_download(api_url, access_token, dst, src, timeout=timeout, endpoint=endpoint)


async def async_remote_download_url_from_vars(url: str, timeout: int = 15, endpoint: str = "/api/v4/remote/download", skew_seconds: int = 60) -> Dict[str, Any]:
    """
    Convenience: use Var config, auto ensure token, then remote download URL. (Async)
    Reads: Var.USE_CLOUDEREVE, Var.CLOUDEREVE_API_URL, Var.CLOUDEREVE_USERNAME,
           Var.CLOUDEREVE_PASSWORD, Var.CLOUDEREVE_DOWNLOAD_PATH
    """
    from WebStreamer.vars import Var
    if not Var.USE_CLOUDEREVE:
        raise ValueError("Cloudreve is disabled (USE_CLOUDEREVE is false)")
    api_url = Var.CLOUDEREVE_API_URL
    email = Var.CLOUDEREVE_USERNAME
    password = Var.CLOUDEREVE_PASSWORD
    dst = Var.CLOUDEREVE_DOWNLOAD_PATH
    access_token = await async_get_valid_cloudreve_access_token(api_url, email, password, skew_seconds=skew_seconds, timeout=timeout)
    return await async_remote_download(api_url, access_token, dst, src, timeout=timeout, endpoint=endpoint)
