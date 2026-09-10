from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClusterViewSet,
    DepartmentViewSet,
    InstanceStatViewSet,
    InstanceViewSet,
    RequestLogViewSet,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("clusters", ClusterViewSet, basename="cluster")
router.register("instances", InstanceViewSet, basename="instance")
router.register("instance-stats", InstanceStatViewSet, basename="instance-stat")
router.register("request-logs", RequestLogViewSet, basename="request-log")

urlpatterns = [
    path("", include(router.urls)),
]