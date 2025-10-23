'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditors: ablecats etsy@live.com
LastEditTime: 2025-10-23 16:11:51
Description: Cloudreve helper functions (async only)
'''
# Cloudreve helper functions - async only

import json
import time
import aiohttp
import logging
from typing import Any as _AnyType
from typing import Optional, Dict, Any
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
    if code != 0:
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


async def _http_post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Dict[str, Any]:
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            text = await resp.text()
            try:
                return json.loads(text)
            except Exception:
                raise RuntimeError(f"Cloudreve invalid response: {text[:200]}")


async def _http_get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.get(url, params=params, headers=headers) as resp:
            text = await resp.text()
            try:
                return json.loads(text)
            except Exception:
                raise RuntimeError(f"Cloudreve invalid response: {text[:200]}")


async def login_and_cache_cloudreve_token(timeout: int = 15) -> Dict[str, Any]:
    """
    Login to Cloudreve, cache the token object globally, and return it.
    """
    from WebStreamer.vars import Var
    email = getattr(Var, "CLOUDEREVE_USERNAME", None) or getattr(Var, "CLOUDEREVE_EMAIL", None)
    api_url = getattr(Var, "CLOUDEREVE_API_URL", None)
    password = getattr(Var, "CLOUDEREVE_PASSWORD", None)
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    if not email or not password:
        raise ValueError("CLOUDEREVE_USERNAME/EMAIL or CLOUDEREVE_PASSWORD is empty")
        
    api_base = api_url.rstrip("/")
    token_url = f"{api_base}/api/v4/session/token"
    result = await _http_post_json(
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


async def refresh_cloudreve_token(timeout: int = 15) -> Dict[str, Any]:
    """
    Refresh Cloudreve session token and update global cache.
    """
    from WebStreamer.vars import Var
    api_url = getattr(Var, "CLOUDEREVE_API_URL", None)
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    api_base = api_url.rstrip("/")
    refresh_url = f"{api_base}/api/v4/session/token/refresh"

    global TOKEN_OBJ
    refresh_token = TOKEN_OBJ.get("refresh_token") if TOKEN_OBJ else None
    if not refresh_token:
        # No refresh token available; fallback to login
        return await login_and_cache_cloudreve_token(timeout)

    result = await _http_post_json(
        refresh_url,
        {"refresh_token": refresh_token},
        None,
        timeout,
    )
    _ensure_api_success(result, "refresh")
    token_obj = _extract_token_obj(result)

    old_refresh = TOKEN_OBJ.get("refresh_token") if TOKEN_OBJ else None
    if not token_obj.get("refresh_token") and old_refresh:
        token_obj["refresh_token"] = old_refresh

    TOKEN_OBJ = token_obj
    return token_obj


async def get_cloudreve_access_token(timeout: int = 15) -> str:
    """
    Convenience function: ensure login & cache, then return access_token.
    """
    token_obj = await login_and_cache_cloudreve_token(timeout)
    return token_obj["access_token"]


def get_cloudreve_token_obj() -> Optional[Dict[str, Any]]:
    """
    Return the cached token object if available.
    """
    return TOKEN_OBJ


async def ensure_valid_cloudreve_token(skew_seconds: int = 60, timeout: int = 15) -> Dict[str, Any]:
    """
    Ensure a valid token is cached; refresh or re-login if near/after expiry.
    """
    global TOKEN_OBJ

    if TOKEN_OBJ is None:
        TOKEN_OBJ = await login_and_cache_cloudreve_token(timeout)
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
                TOKEN_OBJ = await refresh_cloudreve_token(timeout)
                return TOKEN_OBJ
            except Exception:
                pass
        TOKEN_OBJ = await login_and_cache_cloudreve_token(timeout)

    return TOKEN_OBJ


async def get_valid_cloudreve_access_token(skew_seconds: int = 60, timeout: int = 15) -> str:
    """
    Convenience: ensure valid token and return current access_token.
    """
    token_obj = await ensure_valid_cloudreve_token(skew_seconds, timeout)
    return token_obj["access_token"]

# 获取文件列表
async def file_list(page_size: int = 20, uri: str = "cloudreve://my/", page: int = 0, timeout: int = 15, skew_seconds: int = 60) -> Dict[str, Any]:
    """
    List files in Cloudreve.
    URL: /api/v4/file
    Headers: Authorization: Bearer <access_token>
    Query: {"page_size": 20, "uri": "cloudreve://my/", "page": 0}
    """
    from WebStreamer.vars import Var
    if not Var.USE_CLOUDEREVE:
        raise ValueError("Cloudreve is disabled (USE_CLOUDEREVE is false)")
    api_url = Var.CLOUDEREVE_API_URL
    access_token = await get_valid_cloudreve_access_token(skew_seconds=skew_seconds, timeout=timeout)
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    if not access_token:
        raise ValueError("Cloudreve access_token is empty")

    api_base = api_url.rstrip("/")
    url = f"{api_base}/api/v4/file"
    result = await _http_get_json(
        url,
        {"Authorization": f"Bearer {access_token}"},
        timeout,
        {"page_size": int(page_size), "uri": str(uri), "page": int(page)}
    )
    logging.info(f"Cloudreve file list: uri={uri}, page={page}, page_size={page_size}")
    _ensure_api_success(result, "file_list")
    return result

# 分享文件
async def share_file(uri: str = "", timeout: int = 15, skew_seconds: int = 60) -> Dict[str, Any]:
    """
    Share a file in Cloudreve.
    URL: /api/v4/share
    Headers: Authorization: Bearer <access_token>
    Body: {"uri": "cloudreve://my/file.txt"}
    """
    from WebStreamer.vars import Var
    if not Var.USE_CLOUDEREVE:
        raise ValueError("Cloudreve is disabled (USE_CLOUDEREVE is false)")
    api_url = Var.CLOUDEREVE_API_URL
    access_token = await get_valid_cloudreve_access_token(skew_seconds=skew_seconds, timeout=timeout)
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    if not access_token:
        raise ValueError("Cloudreve access_token is empty")
    if not uri:
        raise ValueError("Share file uri is empty")

    api_base = api_url.rstrip("/")
    url = f"{api_base}/api/v4/share"
    result = await _http_post_json(
        url,
        {"uri": str(uri)},
        {"Authorization": f"Bearer {access_token}"},
        timeout,
    )
    logging.info(f"Cloudreve share file: uri={uri}")
    _ensure_api_success(result, "share_file")
    return result

# 获取远程下载任务列表
async def remote_list(page_size: int = 20, category: str = "general", timeout: int = 15, skew_seconds: int = 60) -> Dict[str, Any]:
    """
    List remote download tasks.
    URL: /api/v4/workflow
    Headers: Authorization: Bearer <access_token>
    Body: {"uri": 20, "category": "general|downloading|downloaded"}
    """
    from WebStreamer.vars import Var
    if not Var.USE_CLOUDEREVE:
        raise ValueError("Cloudreve is disabled (USE_CLOUDEREVE is false)")
    api_url = Var.CLOUDEREVE_API_URL
    access_token = await get_valid_cloudreve_access_token(skew_seconds=skew_seconds, timeout=timeout)
    if not api_url:
        raise ValueError("CLOUDEREVE_API_URL is empty")
    if not access_token:
        raise ValueError("Cloudreve access_token is empty")

    api_base = api_url.rstrip("/")
    url = f"{api_base}/api/v4/workflow"
    result = await _http_get_json(
        url,
        {"Authorization": f"Bearer {access_token}"},
        timeout,
        {"page_size": int(page_size), "category": str(category)}
    )
    logging.info(f"Cloudreve remote list: category={category}, page_size={page_size}")
    _ensure_api_success(result, "remote_list")
    return result

# 创建远程下载任务
async def remote_download(src: Any, timeout: int = 15, skew_seconds: int = 60) -> Dict[str, Any]:
    """
    Create a remote download task.

    Headers: Authorization: Bearer <access_token>
    Body: {"dst": dst, "src": [string(url)]}
    """
    from WebStreamer.vars import Var
    if not Var.USE_CLOUDEREVE:
        raise ValueError("Cloudreve is disabled (USE_CLOUDEREVE is false)")
    dst = Var.CLOUDEREVE_DOWNLOAD_PATH
    api_url = Var.CLOUDEREVE_API_URL
    access_token = await get_valid_cloudreve_access_token(skew_seconds=skew_seconds, timeout=timeout)
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
    url = f"{api_base}/api/v4/workflow/download"
    result = await _http_post_json(
        url,
        {"dst": dst, "src": url_list},
        {"Authorization": f"Bearer {access_token}"},
        timeout,
    )
    logging.info(f"Cloudreve remote download response: {url_list}")
    _ensure_api_success(result, "remote_download")
    return result