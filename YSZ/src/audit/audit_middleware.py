"""FastAPI 감사 미들웨어"""

import time
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .audit_service import AuditService, AuditEntry, AuditEventType, audit_service


class AuditMiddleware(BaseHTTPMiddleware):
    """API 요청/응답 감사 미들웨어

    모든 API 요청과 응답을 자동으로 로깅합니다.
    """

    def __init__(self, app: ASGIApp, audit_service: AuditService = audit_service):
        super().__init__(app)
        self.audit_service = audit_service

    async def dispatch(self, request: Request, call_next):
        """요청 처리 및 감사 로깅

        Args:
            request: HTTP 요청
            call_next: 다음 미들웨어/핸들러

        Returns:
            HTTP 응답
        """
        start_time = time.time()
        request_timestamp = datetime.now()

        # 요청 데이터 추출
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type")
        }

        # 거래 ID 추출 (경로에서)
        transaction_id = self._extract_transaction_id(request.url.path)

        # 요청 감사 엔트리
        request_entry = AuditEntry(
            event_type=AuditEventType.API_REQUEST,
            timestamp=request_timestamp,
            transaction_id=transaction_id,
            request_data=request_data
        )

        await self.audit_service.log_entry(request_entry)

        # 요청 처리
        try:
            response = await call_next(request)
            processing_time = time.time() - start_time

            # 응답 감사 엔트리
            response_entry = AuditEntry(
                event_type=AuditEventType.API_RESPONSE,
                timestamp=datetime.now(),
                transaction_id=transaction_id,
                response_data={
                    "status_code": response.status_code,
                    "processing_time_seconds": processing_time,
                    "headers": dict(response.headers)
                }
            )

            await self.audit_service.log_entry(response_entry)

            return response

        except Exception as e:
            # 에러 감사 엔트리
            error_entry = AuditEntry(
                event_type=AuditEventType.ERROR_OCCURRED,
                timestamp=datetime.now(),
                transaction_id=transaction_id,
                error_data={
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "processing_time_seconds": time.time() - start_time
                }
            )

            await self.audit_service.log_entry(error_entry)

            # 예외 재발생
            raise

    def _extract_transaction_id(self, path: str) -> int | None:
        """URL 경로에서 거래 ID 추출

        Args:
            path: URL 경로

        Returns:
            추출된 거래 ID 또는 None
        """
        # /api/v1/facts/123/confirm 같은 패턴에서 ID 추출
        parts = path.split('/')

        for i, part in enumerate(parts):
            if part in ['facts', 'calculate'] and i + 1 < len(parts):
                try:
                    return int(parts[i + 1])
                except ValueError:
                    pass

        return None
