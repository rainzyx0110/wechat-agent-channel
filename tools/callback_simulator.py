#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import time
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape


def signature(token: str, timestamp: str, nonce: str) -> str:
    raw = "".join(sorted([token, timestamp, nonce]))
    return hashlib.sha1(raw.encode(), usedforsecurity=False).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a plaintext WeChat official account callback")
    parser.add_argument("--url", required=True, help="Callback URL ending in the account id")
    parser.add_argument("--token", required=True)
    parser.add_argument("--openid", default="demo-user")
    parser.add_argument("--text", default="你好")
    args = parser.parse_args()

    timestamp = str(int(time.time()))
    nonce = "simulator"
    query = urllib.parse.urlencode(
        {"timestamp": timestamp, "nonce": nonce, "signature": signature(args.token, timestamp, nonce)}
    )
    body = f"""<xml>
<ToUserName><![CDATA[demo-account]]></ToUserName>
<FromUserName>{escape(args.openid)}</FromUserName>
<CreateTime>{timestamp}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content>{escape(args.text)}</Content>
<MsgId>{timestamp}001</MsgId>
</xml>""".encode()
    request = urllib.request.Request(f"{args.url}?{query}", data=body, method="POST")
    request.add_header("Content-Type", "application/xml")
    with urllib.request.urlopen(request, timeout=10) as response:
        print(response.status, response.read().decode())


if __name__ == "__main__":
    main()
