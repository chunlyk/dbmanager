from django.db import models

# Create your models here.

from .crypto import decrypt_password, encrypt_password


class Department(models.Model):
    """部门"""

    name = models.CharField("部门名称", max_length=128, unique=True)
    code = models.CharField("部门编码", max_length=64, unique=True)
    description = models.TextField("描述", blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "db_department"
        ordering = ["id"]
        verbose_name = verbose_name_plural = "部门"

    def __str__(self):
        return f"{self.name}({self.code})"


class Cluster(models.Model):
    """数据库集群"""

    class Environment(models.TextChoices):
        PROD = "prod", "生产"
        STAGING = "staging", "预发"
        TEST = "test", "测试"
        DEV = "dev", "开发"

    name = models.CharField("集群名称", max_length=128)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="clusters", verbose_name="所属部门"
    )
    environment = models.CharField(
        "环境", max_length=16, choices=Environment.choices, default=Environment.PROD
    )
    description = models.TextField("描述", blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "db_cluster"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["department", "name"], name="uniq_dept_cluster_name"),
        ]
        verbose_name = verbose_name_plural = "集群"

    def __str__(self):
        return f"{self.name}[{self.environment}]"


class Instance(models.Model):
    """数据库实例"""

    class DBType(models.TextChoices):
        MYSQL = "mysql", "MySQL"
        POSTGRESQL = "postgresql", "PostgreSQL"
        REDIS = "redis", "Redis"
        MONGODB = "mongodb", "MongoDB"
        OTHER = "other", "Other"

    name = models.CharField("实例名称", max_length=128)
    cluster = models.ForeignKey(
        Cluster, on_delete=models.CASCADE, related_name="instances", verbose_name="所属集群"
    )
    host = models.CharField("主机", max_length=255)
    port = models.PositiveIntegerField("端口")
    db_type = models.CharField(
        "数据库类型", max_length=32, choices=DBType.choices, default=DBType.MYSQL
    )
    username = models.CharField("账号", max_length=128, blank=True, default="")
    password_encrypted = models.TextField("加密密码", blank=True, default="")
    password_updated_at = models.DateTimeField("密码更新时间", null=True, blank=True)
    is_active = models.BooleanField("是否启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "db_instance"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["host", "port"]),
            models.Index(fields=["cluster", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["host", "port"], name="uniq_instance_host_port"),
        ]
        verbose_name = verbose_name_plural = "实例"

    def __str__(self):
        return f"{self.name}({self.host}:{self.port})"

    # ---- 密码相关 -----------------------------------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_encrypted = encrypt_password(raw_password)
        from django.utils import timezone

        self.password_updated_at = timezone.now()

    def get_password(self) -> str:
        return decrypt_password(self.password_encrypted)

    @property
    def department(self) -> Department:
        return self.cluster.department


class InstanceStat(models.Model):
    """按「日期 + 部门 + 集群」维度统计的实例数量快照。"""

    stat_date = models.DateField("统计日期", db_index=True)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="instance_stats", verbose_name="部门"
    )
    cluster = models.ForeignKey(
        Cluster, on_delete=models.CASCADE, related_name="instance_stats", verbose_name="集群"
    )
    instance_count = models.PositiveIntegerField("实例数量", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "db_instance_stat"
        ordering = ["-stat_date", "department_id", "cluster_id"]
        constraints = [
            models.UniqueConstraint(fields=["stat_date", "cluster"], name="uniq_stat_date_cluster"),
        ]
        verbose_name = verbose_name_plural = "实例统计"

    def __str__(self):
        return f"{self.stat_date} {self.department_id}/{self.cluster_id}={self.instance_count}"


class RequestLog(models.Model):
    """请求耗时明细（由中间件写入，可按需关闭）。"""

    method = models.CharField(max_length=10)
    path = models.CharField(max_length=512)
    status_code = models.PositiveIntegerField(default=0)
    duration_ms = models.FloatField(default=0.0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "db_request_log"
        ordering = ["-id"]
        verbose_name = verbose_name_plural = "请求耗时日志"