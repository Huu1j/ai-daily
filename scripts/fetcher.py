"""统一 HTTP 请求：带 UA、超时、重试、gzip 解压。只依赖标准库。"""
import gzip
import io
import urllib.error
import urllib.request
import zlib

from config import TIMEOUT

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


class FetchError(Exception):
    pass


def get(url: str, timeout: int = TIMEOUT, retries: int = 2, headers: dict | None = None) -> str:
    """GET 一个 URL，返回解码后的文本。失败抛 FetchError。"""
    hdrs = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }
    if headers:
        hdrs.update(headers)

    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                enc = (resp.headers.get("Content-Encoding") or "").lower()
                if enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                return raw.decode("utf-8", "ignore")
        except Exception as e:  # 网络异常、超时、HTTPError 都重试
            last_err = e
            if attempt < retries:
                continue
    raise FetchError(f"{url} -> {last_err}")
