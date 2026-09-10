# 数据库实例管理系统（DB Instance Manager）

基于 **Django + DRF + Celery + Redis** 的企业内部数据库实例管理系统，用于统一管理数据库实例、集群与部门，并提供密码自动轮换、实例统计、TCP 端口探测与请求耗时监控能力。

## ✨ 功能特性

- 🗂 **资源建模**：部门（Department）、集群（Cluster）、实例（Instance）三级模型
- 🔧 **完整 CRUD**：基于 Django REST Framework 的标准增删改查接口，支持过滤与分页
- 🔐 **密码安全**：实例密码使用 Fernet（AES-128-CBC + HMAC-SHA256）加密存储，明文永不出库
- 🔁 **自动轮换**：Celery Beat 每 12 小时（00:00 / 12:00）为所有启用实例随机生成并加密保存新密码
- 📊 **每日统计**：每天 00:00 按「部门 + 集群」维度统计启用实例数量并幂等写入数据库
- 🌐 **TCP 探测**：提供 API 探测实例的 TCP 端口是否可达，返回延迟与错误信息
- ⏱ **耗时监控**：中间件统计每个请求的耗时，写入日志、响应头，并可选持久化到数据库
- 🛠 **Admin 后台**：Django Admin 可视化管理所有资源

## 🧱 技术栈

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | >= 3.10 | 语言运行时 |
| Django | >= 4.2, < 5.1 | Web 框架 |
| Django REST Framework | >= 3.14 | REST API |
| Celery | >= 5.3 | 异步任务 & 定时调度 |
| Redis | >= 5.0 | 消息队列 / 结果后端 |
| cryptography | >= 42.0 | 密码加解密 |
| SQLite / PostgreSQL / MySQL | - | 演示用 SQLite，生产建议 PostgreSQL |

## 📁 项目结构

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
        ├── crypto.py         # 密码加密 / 随机生成
        ├── models.py         # 部门 / 集群 / 实例 / 统计 / 请求日志
        ├── serializers.py
        ├── services.py       # TCP 探测、密码轮换
        ├── views.py          # CRUD + 探测 + 轮换接口
        ├── urls.py
        ├── tasks.py          # Celery 定时任务
        ├── middleware.py     # 请求耗时中间件
        ├── admin.py
        └── migrations/
```

## 🚀 快速开始

### 1. 克隆项目

```bash
# GitHub
git clone https://github.com/<your-name>/dbmanager.git
# Gitee
git clone https://gitee.com/<your-name>/dbmanager.git

cd dbmanager
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env .env
# 编辑 .env，至少修改 DJANGO_SECRET_KEY 与 PASSWORD_ENCRYPTION_KEY
```

### 4. 初始化数据库

```bash
python manage.py makemigrations dbmanager
python manage.py migrate
python manage.py createsuperuser
```

### 5. 启动服务

```bash
# Web
python manage.py runserver 0.0.0.0:8000

# Celery Worker（另开终端）
celery -A config worker -l info

# Celery Beat 定时调度（另开终端）
celery -A config beat -l info
```

> 生产环境建议使用 `supervisor` / `systemd` / `docker-compose` 托管进程，`beat` 建议改用 `django-celery-beat` 或 `redbeat` 避免单点。

## 🔌 API 一览

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

## ⏰ 定时任务

| 任务名 | 调度 | 说明 |
|---|---|---|
| `dbmanager.rotate_instance_passwords` | `crontab(minute=0, hour="*/12")` | 每 12 小时轮换所有启用实例密码 |
| `dbmanager.collect_daily_instance_stats` | `crontab(minute=0, hour=0)` | 每天 00:00 按部门 + 集群统计实例数量 |

手动补跑统计：

```bash
python manage.py shell -c "from apps.dbmanager.tasks import collect_daily_instance_stats; collect_daily_instance_stats.delay('2025-01-01')"
```

## 🔒 安全说明

1. 密码明文 **永不入库**，仅以 Fernet 密文形式保存在 `Instance.password_encrypted` 字段。
2. `PASSWORD_ENCRYPTION_KEY` 必须独立于 `SECRET_KEY`，并通过环境变量或 KMS/Vault 注入。
3. 生产环境请：
   - 关闭 `DEBUG`
   - 设置 `ALLOWED_HOSTS`
   - 为 `/instances/{id}/password/` 增加二次审批与审计日志
   - 使用 HTTPS 传输
4. 密码轮换到真实数据库（`ALTER USER` / `CONFIG SET requirepass`）时，建议采用「先改远端成功 → 再落库 → 失败进补偿队列」的流程。

## 🧪 本地自测

```bash
# 触发一次密码轮换
python manage.py shell -c "from apps.dbmanager.tasks import rotate_instance_passwords; rotate_instance_passwords.delay()"

# 触发一次统计
python manage.py shell -c "from apps.dbmanager.tasks import collect_daily_instance_stats; collect_daily_instance_stats.delay()"
```

## 🗺 Roadmap

- [ ] 支持 MySQL / PostgreSQL / Redis 真实改密
- [ ] 接入 Vault / KMS 管理加密密钥
- [ ] 实例探测结果缓存与批量探测
- [ ] Prometheus 指标导出
- [ ] Docker Compose 一键部署

## 📄 License

[MIT](LICENSE)

## 🙋 贡献

欢迎提交 Issue 和 Pull Request。