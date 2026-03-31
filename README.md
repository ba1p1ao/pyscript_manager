# Python 脚本管理器

一个基于 FastAPI 的 Python 脚本后台管理系统，提供进程监控、脚本配置、日志查看等功能。

## 功能特性

### 核心功能

| 功能 | 描述 |
|------|------|
| 进程监控 | 实时检测 YAML 文件文件上所有运行的 Python 进程 |
| 进程管理 | 安全终止一个或多个 Python 进程（自动保护自身 Web 进程） |
| 脚本配置 | 通过 YAML 文件管理脚本，支持路径、调度、重试等配置 |
| 日志查看 | 实时查看脚本输出和错误日志，支持自动刷新 |
| 运行历史 | 记录脚本执行历史，包括状态、时长、错误信息等 |
| 系统日志 | 记录所有操作日志，便于审计和问题排查 |

### 调度类型

- **手动运行 (manual)**: 通过界面或 API 手动触发
- **定时运行 (cron)**: 使用 Cron 表达式定时执行
- **间隔运行 (interval)**: 按固定时间间隔循环执行

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 数据库 | SQLAlchemy + SQLite |
| 进程管理 | psutil |
| 配置管理 | PyYAML |
| 前端框架 | Vue 3 + Vite |
| UI 组件库 | Element Plus |
| 状态管理 | Pinia |
| 路由管理 | Vue Router |

## 项目结构

```
pyscript_mananger/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口 (已移至根目录)
│   ├── models.py            # 数据库模型定义
│   ├── database.py          # 数据库配置
│   ├── api.py               # API 路由层
│   ├── config_manager.py    # YAML 配置管理
│   └── process_manager.py   # 进程管理服务
├── frontend/                # Vue3 前端项目
│   ├── src/
│   │   ├── api/             # API 请求封装
│   │   ├── assets/          # 静态资源
│   │   ├── components/      # 公共组件
│   │   ├── router/          # 路由配置
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── views/           # 页面组件
│   │   │   ├── Dashboard.vue      # 仪表盘
│   │   │   ├── Processes.vue      # 进程管理
│   │   │   ├── Scripts.vue        # 脚本配置
│   │   │   ├── ScriptDetail.vue   # 脚本详情
│   │   │   ├── History.vue        # 运行历史
│   │   │   └── SystemLogs.vue     # 系统日志
│   │   ├── App.vue          # 根组件
│   │   └── main.js          # 入口文件
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── config/
│   └── scripts.yaml         # 脚本配置文件
├── data/
│   └── pyscript_manager.db  # SQLite 数据库
├── logs/                    # 脚本运行日志
├── main.py                  # FastAPI 主入口
├── requirements.txt         # Python 依赖包
└── README.md
```

## 快速开始

### 1. 安装后端依赖

```bash
cd pyscript_mananger
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
# 或使用 pnpm/yarn
# pnpm install
# yarn install
```

### 3. 配置脚本

编辑 `config/scripts.yaml` 文件，添加要管理的脚本：

```yaml
scripts:
  - name: my_script
    script_path: /path/to/your/script.py
    description: 我的脚本
    schedule_type: manual
    max_retries: 3
    retry_delay: 60
    timeout: 3600
    enabled: true
    auto_start: false
```

### 4. 开发模式启动

**启动后端服务：**
```bash
python main.py
```

**启动前端开发服务器：**
```bash
cd frontend
npm run dev
```

访问地址：
- 前端开发服务器: http://localhost:3000
- 后端 API: http://localhost:8900
- API 文档: http://localhost:8900/docs

### 5. 生产模式部署

**构建前端：**
```bash
cd frontend
npm run build
```

**启动后端（自动服务前端静态文件）：**
```bash
python main.py
```

访问地址：http://localhost:8900

## API 接口

### 进程管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/processes` | 获取所有 Python 进程 |
| GET | `/api/processes/{pid}` | 获取进程详情 |
| DELETE | `/api/processes/{pid}` | 终止单个进程 |
| POST | `/api/processes/kill` | 批量终止进程 |

### 脚本配置

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/scripts` | 获取所有脚本配置 |
| POST | `/api/scripts` | 创建脚本配置 |
| PUT | `/api/scripts/{name}` | 更新脚本配置 |
| DELETE | `/api/scripts/{name}` | 删除脚本配置 |
| POST | `/api/scripts/reload` | 重载 YAML 配置 |

### 脚本执行

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/scripts/{name}/start` | 启动脚本 |
| POST | `/api/scripts/{name}/stop` | 停止脚本 |
| GET | `/api/scripts/{name}/log` | 获取脚本日志 |
| GET | `/api/scripts/{name}/history` | 获取运行历史 |

### 历史记录

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/history` | 获取所有运行历史 |
| GET | `/api/stats` | 获取统计数据 |

### 系统日志

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/system-logs` | 获取系统操作日志 |

## YAML 配置说明

```yaml
scripts:
  - name: script_name           # 脚本名称（唯一标识）
    script_path: /path/to/script.py  # 脚本绝对路径
    
    # 运行配置
    schedule_type: manual       # 调度类型: manual/cron/interval
    schedule: "0 2 * * *"       # Cron 表达式（schedule_type=cron 时）
    interval_seconds: 300       # 间隔秒数（schedule_type=interval 时）
    max_retries: 3              # 最大重试次数
    retry_delay: 60             # 重试间隔（秒）
    timeout: 3600               # 超时时间（秒）
    
    # 运行环境
    working_dir: /work/dir      # 工作目录
    env_vars:                   # 环境变量
      DEBUG: "false"
      LOG_LEVEL: "INFO"
    python_path: /usr/bin/python3  # Python 解释器
    
    # 状态控制
    enabled: true               # 是否启用
    auto_start: false           # 是否自动启动
    description: 脚本描述       # 描述信息
```

## 数据库模型

### ScriptConfig (脚本配置表)

存储脚本配置信息，与 YAML 文件同步。

| 字段 | 类型 | 描述 |
|------|------|------|
| id | Integer | 主键 |
| name | String | 脚本名称 |
| script_path | String | 脚本路径 |
| schedule_type | String | 调度类型 |
| max_retries | Integer | 最大重试次数 |
| status | String | 当前状态 |
| current_pid | Integer | 当前运行进程ID |

### ScriptHistory (运行历史表)

记录每次脚本执行的详细信息。

| 字段 | 类型 | 描述 |
|------|------|------|
| id | Integer | 主键 |
| script_name | String | 脚本名称 |
| pid | Integer | 进程ID |
| start_time | DateTime | 开始时间 |
| end_time | DateTime | 结束时间 |
| status | String | 执行状态 |
| exit_code | Integer | 退出码 |
| error_message | Text | 错误信息 |

### SystemLog (系统日志表)

记录系统操作日志。

| 字段 | 类型 | 描述 |
|------|------|------|
| id | Integer | 主键 |
| timestamp | DateTime | 时间戳 |
| level | String | 日志级别 |
| action | String | 操作类型 |
| target | String | 操作目标 |
| message | Text | 详细信息 |

## 后期扩展：Celery 分布式任务

当脚本数量增多时，可将脚本执行封装为 Celery 任务，实现分布式调度和管理。

### 架构设计

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│    Redis    │◀────│   Celery    │
│   Web API   │     │   Broker    │     │   Worker    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Flower    │
                    │  监控界面   │
                    └─────────────┘
```

### 迁移方案

1. **添加 Celery 配置** (`app/celery_app.py`):

```python
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    'pyscript_manager',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

@celery_app.task(bind=True, max_retries=3)
def run_script_task(self, script_name: str):
    """执行脚本的 Celery 任务"""
    # 脚本执行逻辑
    pass
```

2. **定义定时任务**:

```python
celery_app.conf.beat_schedule = {
    'daily-backup': {
        'task': 'app.celery_app.run_script_task',
        'schedule': crontab(hour=2, minute=0),
        'args': ('backup_script',)
    },
}
```

3. **启动服务**:

```bash
# 启动 Celery Worker
celery -A app.celery_app worker --loglevel=info

# 启动 Celery Beat (定时任务调度)
celery -A app.celery_app beat --loglevel=info

# 启动 Flower (监控界面)
celery -A app.celery_app flower --port=5555
```

### Flower 监控

Flower 提供实时监控界面：
- 查看任务执行状态
- 监控 Worker 状态
- 手动触发任务
- 查看任务历史

访问地址: http://localhost:5555

## 安全注意事项

1. **进程保护**: 系统自动保护自身 Web 进程，无法通过界面终止
2. **路径验证**: 只接受绝对路径，防止路径遍历攻击
3. **权限控制**: 仅能终止 Python 进程，避免误杀系统服务
4. **超时保护**: 脚本执行有超时限制，防止资源耗尽

