# 数据库实例管理系统 — 方案 A
# 基于 Django + DRF + Celery + Redis 的企业内部数据库实例管理系统。

## 项目结构

```
dbmanager/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── config/
│   ├── __init__.py          # 加载 Celery app
│   ├── settings.py
│   ├── celery.py
│   ├── urls.py
│   └── wsgi.py
└── apps/
    └── dbmanager/
        ├── apps.py
        ├── crypto.py         # 密码加密
        ├── models.py         
        ├── serializers.py
        ├── services.py       # TCP 探测、密码轮换
        ├── views.py          
        ├── urls.py
        ├── tasks.py          # Celery 定时任务
        ├── middleware.py     # 请求耗时中间件
        ├── admin.py
        └── migrations/
```
## 数据模型设计

### Department（部门）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | CharField(128) | 部门名称，唯一 |
| code | CharField(64) | 部门编码，唯一 |
| description | TextField | 描述，可空 |
| created_at / updated_at | DateTimeField | 时间戳 |

### Cluster（集群）

| 字段 | 类型 | 说明                       |
|------|------|--------------------------|
| name | CharField(128) | 集群名称                     |
| department | FK → Department | 所属部门                     |
| environment | CharField | 环境：dev/test/prod/staging |
| description | TextField | 描述                       |
| created_at / updated_at | DateTimeField | 时间戳                      |

### Instance（数据库实例）

| 字段 | 类型 | 说明 |
|------|------|----|
| name | CharField(128) | 实例名称 |
| host | CharField(255) | 主机 |
| port | PositiveIntegerField | 端口，默认 3306 |
| db_type | CharField | mysql/postgresql/redis/mongodb 等 |
| cluster | FK → Cluster | 所属集群 |
| is_active | CharField | 是否启用 |
| username | CharField(128) | 账号 |
| password_encrypted | TextField | Fernet 加密密码 |
| password_updated_at | DateTimeField | 密码更新时间 |
| created_at / updated_at | DateTimeField | 时间戳 |

> 密码不以明文落库；读取时通过 `get_password()` / `set_password()` 加解密。

### InstanceStat（每日统计）

| 字段 | 类型 | 说明 |
|------|------|------|
| stat_date | DateField | 统计日期 |
| department | FK → Department | 部门 |
| cluster | FK → Cluster | 集群 |
| instance_count | PositiveIntegerField | 实例数量 |
| created_at / updated_at | DateTimeField | 写入时间 |

### RequestLog（请求耗时明细）

| 字段 | 类型 | 说明 |
|------|------|--|
| method | CharField |
| path | CharField |
| status_code | PositiveIntegerField |
| duration_ms | FloatField |
| created_at | DateTimeField |

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET / POST | `/api/departments/` | 部门列表 / 创建 |
| GET / PUT / PATCH / DELETE | `/api/departments/{id}/` | 部门详情 / 更新 / 删除 |
| GET / POST | `/api/clusters/` | 集群列表 / 创建 |
| GET / PUT / PATCH / DELETE | `/api/clusters/{id}/` | 集群详情 / 更新 / 删除 |
| GET / POST | `/api/instances/` | 实例列表 / 创建（body 可带 `password`） |
| GET / PUT / PATCH / DELETE | `/api/instances/{id}/` | 实例详情 / 更新 / 删除 |
| POST / GET | `/api/instances/{id}/probe/` | **TCP 端口探测** |
| POST | `/api/instances/{id}/rotate-password/` | 手动轮换密码，返回一次性明文 |
| GET | `/api/instances/{id}/password/` | 查看明文密码（生产需加权限） |
| GET | `/api/instance-stats/?stat_date=YYYY-MM-DD` | 统计结果查询 |
| GET | `/api/request-logs/` | 请求耗时日志 |

### 调用示例

**探测实例是否可达**

```bash
curl -X POST http://127.0.0.1:8000/api/instances/1/probe/ \
     -H "Content-Type: application/json" \
     -d '{"timeout": 3}'
```

响应：

```json
{
  "instance_id": 1,
  "name": "mysql-prod-01",
  "host": "10.0.0.10",
  "port": 3306,
  "reachable": true,
  "latency_ms": 12.34,
  "error": null
}
```

**手动轮换密码**

```bash
curl -X POST http://127.0.0.1:8000/api/instances/1/rotate-password/
```

## 定时任务

| 任务名 | 调度 | 说明 |
|---|---|---|
| `dbmanager.rotate_instance_passwords` | `crontab(minute=0, hour="*/12")` | 每 12 小时轮换所有启用实例密码 |
| `dbmanager.collect_daily_instance_stats` | `crontab(minute=0, hour=0)` | 每天 00:00 按部门 + 集群统计实例数量 |

手动补跑统计：

```bash
python manage.py shell -c "from apps.dbmanager.tasks import collect_daily_instance_stats; collect_daily_instance_stats.delay('2025-01-01')"
```

## 本地自测

```bash
# 触发一次密码轮换
python manage.py shell -c "from apps.dbmanager.tasks import rotate_instance_passwords; rotate_instance_passwords.delay()"

# 触发一次统计
python manage.py shell -c "from apps.dbmanager.tasks import collect_daily_instance_stats; collect_daily_instance_stats.delay()"
```

## 本地运行步骤

## 1. 克隆项目

```bash
# GitHub
git clone https://github.com/<your-name>/dbmanager.git
# Gitee
git clone https://gitee.com/<your-name>/dbmanager.git

cd dbmanager
```

## 2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## 3. 配置环境变量

```bash
cp .env .env
# 编辑 .env，至少修改 DJANGO_SECRET_KEY 与 PASSWORD_ENCRYPTION_KEY
```

## 4. 初始化数据库

```bash
python manage.py makemigrations dbmanager
python manage.py migrate
python manage.py createsuperuser
```

## 5. 启动服务

```bash
# Web
python manage.py runserver 0.0.0.0:8000

# Celery Worker（另开终端）
celery -A config worker -l info

# Celery Beat 定时调度（另开终端）
celery -A config beat -l info
```