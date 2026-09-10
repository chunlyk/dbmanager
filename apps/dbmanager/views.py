from django.shortcuts import render

# Create your views here.
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Cluster, Department, Instance, InstanceStat, RequestLog
from .serializers import (
    ClusterSerializer,
    DepartmentSerializer,
    InstanceSerializer,
    InstanceStatSerializer,
    RequestLogSerializer,
)
from .services import probe_tcp, rotate_instance_password


class DepartmentViewSet(viewsets.ModelViewSet):
    """部门 CRUD"""

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        keyword = self.request.query_params.get("keyword")
        if keyword:
            qs = qs.filter(Q(name__icontains=keyword) | Q(code__icontains=keyword))
        return qs


class ClusterViewSet(viewsets.ModelViewSet):
    """集群 CRUD"""

    serializer_class = ClusterSerializer

    def get_queryset(self):
        qs = Cluster.objects.select_related("department").all()
        params = self.request.query_params
        if department := params.get("department"):
            qs = qs.filter(department_id=department)
        if environment := params.get("environment"):
            qs = qs.filter(environment=environment)
        if keyword := params.get("keyword"):
            qs = qs.filter(name__icontains=keyword)
        return qs


class InstanceViewSet(viewsets.ModelViewSet):
    """实例 CRUD + TCP 端口探测 + 密码轮换"""

    serializer_class = InstanceSerializer

    def get_queryset(self):
        qs = Instance.objects.select_related("cluster", "cluster__department").all()
        params = self.request.query_params
        if cluster := params.get("cluster"):
            qs = qs.filter(cluster_id=cluster)
        if department := params.get("department"):
            qs = qs.filter(cluster__department_id=department)
        if db_type := params.get("db_type"):
            qs = qs.filter(db_type=db_type)
        if (raw_active := params.get("is_active")) not in (None, ""):
            qs = qs.filter(is_active=raw_active.lower() in ("1", "true", "yes"))
        if keyword := params.get("keyword"):
            qs = qs.filter(
                Q(name__icontains=keyword)
                | Q(host__icontains=keyword)
                | Q(username__icontains=keyword)
            )
        return qs

    # ------------------------------------------------------------------
    # 探测实例 TCP 端口是否可达
    # POST /api/instances/{id}/probe/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post", "get"], url_path="probe")
    def probe(self, request, pk=None):
        instance = self.get_object()
        try:
            timeout = float(request.data.get("timeout", 3.0))
        except (TypeError, ValueError):
            timeout = 3.0
        timeout = min(max(timeout, 0.1), 30.0)

        result = probe_tcp(instance.host, instance.port, timeout=timeout)
        result.update(
            {
                "instance_id": instance.id,
                "name": instance.name,
                "host": instance.host,
                "port": instance.port,
            }
        )
        return Response(result, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # 手动轮换单个实例密码
    # POST /api/instances/{id}/rotate-password/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="rotate-password")
    def rotate_password(self, request, pk=None):
        instance = self.get_object()
        plain = rotate_instance_password(instance)
        return Response(
            {
                "id": instance.id,
                "username": instance.username,
                "password": plain,
                "password_updated_at": instance.password_updated_at,
            }
        )

    # ------------------------------------------------------------------
    # 查看明文密码（生产务必加严格权限校验 + 审计）
    # GET /api/instances/{id}/password/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["get"], url_path="password")
    def reveal_password(self, request, pk=None):
        instance = self.get_object()
        return Response(
            {
                "id": instance.id,
                "username": instance.username,
                "password": instance.get_password(),
                "password_updated_at": instance.password_updated_at,
            }
        )


class InstanceStatViewSet(viewsets.ReadOnlyModelViewSet):
    """实例统计数据（只读）"""

    serializer_class = InstanceStatSerializer

    def get_queryset(self):
        qs = InstanceStat.objects.select_related("department", "cluster").all()
        params = self.request.query_params
        if stat_date := params.get("stat_date"):
            qs = qs.filter(stat_date=stat_date)
        if department := params.get("department"):
            qs = qs.filter(department_id=department)
        if cluster := params.get("cluster"):
            qs = qs.filter(cluster_id=cluster)
        return qs


class RequestLogViewSet(viewsets.ReadOnlyModelViewSet):
    """请求耗时日志（只读）"""

    serializer_class = RequestLogSerializer
    queryset = RequestLog.objects.all()