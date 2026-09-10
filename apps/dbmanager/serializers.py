from rest_framework import serializers

from .models import Cluster, Department, Instance, InstanceStat, RequestLog


class DepartmentSerializer(serializers.ModelSerializer):
    cluster_count = serializers.IntegerField(source="clusters.count", read_only=True)

    class Meta:
        model = Department
        fields = [
            "id", "name", "code", "description",
            "cluster_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "cluster_count"]


class ClusterSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    instance_count = serializers.IntegerField(source="instances.count", read_only=True)

    class Meta:
        model = Cluster
        fields = [
            "id", "name", "department", "department_name", "environment",
            "description", "instance_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "department_name", "instance_count"]


class InstanceSerializer(serializers.ModelSerializer):
    # 只写，用于创建 / 更新时设置密码；读取时永不回显密文
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={"input_type": "password"}
    )
    cluster_name = serializers.CharField(source="cluster.name", read_only=True)
    department_id = serializers.IntegerField(source="cluster.department_id", read_only=True)
    department_name = serializers.CharField(source="cluster.department.name", read_only=True)

    class Meta:
        model = Instance
        fields = [
            "id", "name", "cluster", "cluster_name", "department_id", "department_name",
            "host", "port", "db_type", "username", "password",
            "password_updated_at", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "password_updated_at", "created_at", "updated_at",
            "cluster_name", "department_id", "department_name",
        ]

    def validate_port(self, value):
        if not (1 <= value <= 65535):
            raise serializers.ValidationError("端口必须在 1-65535 之间")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = Instance(**validated_data)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class InstanceStatSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    cluster_name = serializers.CharField(source="cluster.name", read_only=True)

    class Meta:
        model = InstanceStat
        fields = [
            "id", "stat_date", "department", "department_name",
            "cluster", "cluster_name", "instance_count", "updated_at",
        ]
        read_only_fields = fields


class RequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestLog
        fields = ["id", "method", "path", "status_code", "duration_ms", "created_at"]
        read_only_fields = fields