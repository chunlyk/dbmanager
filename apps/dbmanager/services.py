"""业务服务层：TCP 探测、密码轮换。"""
import logging
import socket
import time

from django.utils import timezone

from .crypto import encrypt_password, generate_password

logger = logging.getLogger("dbmanager")


def probe_tcp(host: str, port: int, timeout: float = 3.0) -> dict:
    """探测 host:port 是否 TCP 可达。"""
    start = time.perf_counter()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {"reachable": True, "latency_ms": latency_ms, "error": None}
    except socket.timeout:
        return {
            "reachable": False,
            "latency_ms": None,
            "error": f"connect timeout after {timeout}s",
        }
    except OSError as exc:
        return {
            "reachable": False,
            "latency_ms": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def rotate_instance_password(instance, save: bool = True) -> str:
    """为单个实例生成并保存新密码，返回明文（调用方负责安全投递）。"""
    plain = generate_password()
    instance.password_encrypted = encrypt_password(plain)
    instance.password_updated_at = timezone.now()
    if save:
        instance.save(update_fields=["password_encrypted", "password_updated_at", "updated_at"])
    logger.info("instance=%s password rotated", instance.pk)
    return plain