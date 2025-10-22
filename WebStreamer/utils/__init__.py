'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditors: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditTime: 2025-10-22 09:05:03
Description: 
'''
# This file is a part of TG-FileStreamBot
# Coding : Jyothis Jayanth [@EverythingSuckz]

from .keepalive import ping_server
from .time_format import get_readable_time
from .file_properties import get_hash, get_name
from .custom_dl import ByteStreamer
from .cloudreve import (
    get_cloudreve_access_token,
    login_and_cache_cloudreve_token,
    get_cloudreve_token_obj,
    refresh_cloudreve_token,
    ensure_valid_cloudreve_token,
    get_valid_cloudreve_access_token,
    async_login_and_cache_cloudreve_token,
    async_refresh_cloudreve_token,
    async_get_cloudreve_access_token,
    async_ensure_valid_cloudreve_token,
    async_get_valid_cloudreve_access_token,
    remote_download,
    async_remote_download,
    remote_download_authed,
    async_remote_download_authed,
    remote_download_url,
    async_remote_download_url,
    remote_download_authed_url,
    async_remote_download_authed_url,
    remote_download_url_from_vars,
    async_remote_download_url_from_vars,
)