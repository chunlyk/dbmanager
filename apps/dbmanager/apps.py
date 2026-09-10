from django.apps import AppConfig


class DbmanagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dbmanager"
    verbose_name = "数据库实例管理"