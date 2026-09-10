"""Celery 异步任务：密码轮换 & 每日统计。"""
import datetime
import logging

from celery import shared_task
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from .crypto import encrypt_password, generate_password
from .models import Instance, InstanceStat

logger = logging.getLogger("dbmanager")


@shared_task(name="dbmanager.rotate_instance_passwords")
def rotate_instance_passwords(batch_size: int = 500) -> dict:
    """
    每 12 小时执行一次：为所有启用的实例生成随机新密码并加密落库。

    注意：真实生产环境还需要用新密码去实例上执行 ALTER USER / CONFIG SET 等操作，
    并做「先改远端成功、再落库」或「双写 + 补偿」的可靠性设计。
    """
    now = timezone.now()
    qs = Instance.objects.filter(is_active=True).only(
        "id", "password_encrypted", "password_updated_at", "updated_at"
    )

    batch, rotated = [], 0
    for instance in qs.iterator(chunk_size=batch_size):
        instance.password_encrypted = encrypt_password(generate_password())
        instance.password_updated_at = now
        instance.updated_at = now
        batch.append(instance)
        if len(batch) >= batch_size:
            Instance.objects.bulk_update(
                batch,
                ["password_encrypted", "password_updated_at", "updated_at"],
                batch_size=batch_size,
            )
            rotated += len(batch)
            batch.clear()

    if batch:
        Instance.objects.bulk_update(
            batch,
            ["password_encrypted", "password_updated_at", "updated_at"],
            batch_size=batch_size,
        )
        rotated += len(batch)

    logger.info("rotate_instance_passwords finished, rotated=%s", rotated)
    return {"rotated": rotated, "finished_at": now.isoformat()}


@shared_task(name="dbmanager.collect_daily_instance_stats")
def collect_daily_instance_stats(stat_date: str | None = None) -> dict:
    """
    每天 00:00 执行：按「部门 + 集群」维度统计启用实例数量并写入 InstanceStat。

    stat_date 支持补跑，格式 YYYY-MM-DD，默认取当天（本地时区）。
    """
    if stat_date:
        target_date = datetime.date.fromisoformat(stat_date)
    else:
        target_date = timezone.localdate()

    rows = (
        Instance.objects.filter(is_active=True)
        .values("cluster_id", "cluster__department_id")
        .annotate(cnt=Count("id"))
    )

    objs = [
        InstanceStat(
            stat_date=target_date,
            department_id=row["cluster__department_id"],
            cluster_id=row["cluster_id"],
            instance_count=row["cnt"],
        )
        for row in rows
    ]

    if objs:
        with transaction.atomic():
            InstanceStat.objects.bulk_create(
                objs,
                update_conflicts=True,
                unique_fields=["stat_date", "cluster"],
                update_fields=["department", "instance_count"],
                batch_size=500,
            )

    logger.info(
        "collect_daily_instance_stats finished, date=%s rows=%s", target_date, len(objs)
    )
    return {"stat_date": str(target_date), "rows": len(objs)}