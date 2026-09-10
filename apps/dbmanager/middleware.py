"""请求耗时统计中间件。"""
import logging
import time

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("request.timing")


class RequestTimingMiddleware(MiddlewareMixin):
    """
    记录每个请求的耗时：
      1) 写入 `request.timing` logger
      2) 在响应头返回 X-Request-Duration-Ms
      3) 可选持久化到 RequestLog 表（settings.REQUEST_TIMING_LOG_TO_DB）
    """

    def process_request(self, request):
        request._start_perf = time.perf_counter()
        return None

    def process_response(self, request, response):
        start = getattr(request, "_start_perf", None)
        if start is None:
            return response

        duration_ms = (time.perf_counter() - start) * 1000.0
        response["X-Request-Duration-Ms"] = f"{duration_ms:.2f}"
        logger.info(
            "%s %s -> %s %.2fms",
            request.method,
            request.get_full_path(),
            getattr(response, "status_code", "-"),
            duration_ms,
        )
        self._persist(request, getattr(response, "status_code", 0), duration_ms)
        return response

    def process_exception(self, request, exception):
        start = getattr(request, "_start_perf", None)
        if start is not None:
            duration_ms = (time.perf_counter() - start) * 1000.0
            logger.warning(
                "%s %s raised %s after %.2fms",
                request.method,
                request.get_full_path(),
                type(exception).__name__,
                duration_ms,
            )
        return None  # 交给 Django 默认异常处理

    @staticmethod
    def _persist(request, status_code: int, duration_ms: float) -> None:
        if not getattr(settings, "REQUEST_TIMING_LOG_TO_DB", True):
            return
        try:
            from .models import RequestLog

            RequestLog.objects.create(
                method=request.method[:10],
                path=request.get_full_path()[:512],
                status_code=status_code or 0,
                duration_ms=round(duration_ms, 2),
            )
        except Exception:  # pragma: no cover - 日志写入失败不能影响主流程
            logger.exception("persist request log failed")