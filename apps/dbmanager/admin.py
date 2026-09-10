
# Register your models here.
from django.contrib import admin

from .models import Cluster, Department, Instance, InstanceStat, RequestLog


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "created_at")
    search_fields = ("name", "code")


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "department", "environment", "created_at")
    list_filter = ("environment", "department")
    search_fields = ("name",)


@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "cluster", "host", "port", "db_type", "is_active", "password_updated_at")
    list_filter = ("db_type", "is_active", "cluster__environment")
    search_fields = ("name", "host", "username")
    # 密文不展示，明文更不展示
    exclude = ("password_encrypted",)


@admin.register(InstanceStat)
class InstanceStatAdmin(admin.ModelAdmin):
    list_display = ("stat_date", "department", "cluster", "instance_count")
    list_filter = ("stat_date", "department")


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "path", "status_code", "duration_ms", "created_at")
    list_filter = ("method", "status_code")