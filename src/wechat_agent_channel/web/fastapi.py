from typing import Any

from ..channels.official_account.adapter import DuplicateMessageError, OfficialAccountAdapter
from ..channels.wechat_kf import WeChatKFAdapter
from ..registry import ChannelRegistry
from ..runtime import ChannelRuntime


def create_channel_router(runtime: ChannelRuntime, registry: ChannelRegistry):
    try:
        from fastapi import APIRouter, HTTPException, Query, Request, Response
    except ImportError as exc:
        raise RuntimeError(
            'install FastAPI support with: pip install "wechat-agent-channel[fastapi]"'
        ) from exc

    router = APIRouter(tags=["wechat-channels"])

    @router.get("/types")
    async def list_channel_types() -> list[dict[str, Any]]:
        return [manifest.to_dict() for manifest in registry.list()]

    @router.get("/instances")
    async def list_instances() -> list[dict[str, Any]]:
        return [
            {
                "account_id": account_id,
                "channel_type": adapter.channel_type,
                "status": "configured",
            }
            for account_id, adapter in runtime.list_adapters()
        ]

    @router.get("/instances/{account_id}/status")
    async def instance_status(account_id: str) -> dict[str, Any]:
        adapter = _adapter(runtime, account_id)
        status = getattr(adapter, "status", None)
        return await status() if status else {"configured": True}

    @router.post("/instances/{account_id}/login-qrcode")
    async def begin_login(account_id: str) -> dict[str, Any]:
        adapter = _adapter(runtime, account_id)
        action = getattr(adapter, "begin_login", None)
        if action is None:
            raise HTTPException(status_code=400, detail="channel does not support QR login")
        return await action()

    @router.get("/instances/{account_id}/login-status")
    async def login_status(account_id: str, qrcode: str = "", verify_code: str = "") -> dict[str, Any]:
        adapter = _adapter(runtime, account_id)
        action = getattr(adapter, "poll_login", None)
        if action is None:
            raise HTTPException(status_code=400, detail="channel does not support QR login")
        return await action(qrcode, verify_code)

    @router.get("/callbacks/official-account/{account_id}", response_class=Response)
    async def verify_official_account(
        account_id: str,
        signature: str | None = Query(None),
        timestamp: str = Query(...),
        nonce: str = Query(...),
        echostr: str = Query(...),
        msg_signature: str | None = Query(None),
        encrypt_type: str | None = Query(None),
    ) -> Response:
        adapter = _official_account_adapter(runtime, account_id)
        try:
            result = adapter.verify_url(
                timestamp,
                nonce,
                signature,
                echostr,
                msg_signature=msg_signature,
                encrypt_type=encrypt_type,
            )
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return Response(result, media_type="text/plain")

    @router.post("/callbacks/official-account/{account_id}", response_class=Response)
    async def receive_official_account(
        account_id: str,
        request: Request,
        timestamp: str = Query(...),
        nonce: str = Query(...),
        signature: str | None = Query(None),
        msg_signature: str | None = Query(None),
        encrypt_type: str | None = Query(None),
    ) -> Response:
        adapter = _official_account_adapter(runtime, account_id)
        try:
            message = await adapter.parse_callback(
                await request.body(),
                timestamp=timestamp,
                nonce=nonce,
                signature=signature,
                msg_signature=msg_signature,
                encrypt_type=encrypt_type,
            )
            await runtime.dispatch(message)
        except DuplicateMessageError:
            pass
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return Response("success", media_type="text/plain")

    @router.get("/callbacks/wechat-kf/{account_id}", response_class=Response)
    async def verify_wechat_kf(account_id: str, timestamp: str, nonce: str, msg_signature: str, echostr: str) -> Response:
        adapter = _wechat_kf_adapter(runtime, account_id)
        try:
            result = adapter.verify_url(timestamp, nonce, msg_signature, echostr)
        except Exception as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return Response(result, media_type="text/plain")

    @router.post("/callbacks/wechat-kf/{account_id}", response_class=Response)
    async def receive_wechat_kf(account_id: str, request: Request, timestamp: str, nonce: str, msg_signature: str) -> Response:
        adapter = _wechat_kf_adapter(runtime, account_id)
        try:
            await adapter.accept_callback(await request.body(), timestamp=timestamp, nonce=nonce, signature=msg_signature)
        except Exception as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return Response("success", media_type="text/plain")

    return router


def _official_account_adapter(runtime: ChannelRuntime, account_id: str) -> OfficialAccountAdapter:
    try:
        adapter = runtime.get_adapter(account_id)
    except KeyError as exc:
        try:
            from fastapi import HTTPException
        except ImportError:  # pragma: no cover
            raise exc
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not isinstance(adapter, OfficialAccountAdapter):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="account is not an official account")
    return adapter


def _adapter(runtime: ChannelRuntime, account_id: str):
    try:
        return runtime.get_adapter(account_id)
    except KeyError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _wechat_kf_adapter(runtime: ChannelRuntime, account_id: str) -> WeChatKFAdapter:
    adapter = _adapter(runtime, account_id)
    if not isinstance(adapter, WeChatKFAdapter):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="account is not a WeChat KF account")
    return adapter
