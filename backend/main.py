"""
Python 脚本管理器 - 主入口
基于 FastAPI 的后台管理系统
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

from app.database import init_db
from app.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    init_db()
    print("=" * 50)
    print("Python 脚本管理器已启动")
    print("访问地址: http://localhost:8900")
    print("API 文档: http://localhost:8900/docs")
    print("=" * 50)
    
    yield
    
    # 关闭时清理
    print("应用正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="Python 脚本管理器",
    description="""
## 功能概述

一个基于 FastAPI 的 Python 脚本后台管理系统，提供以下功能：

### 核心功能
1. **进程监控** - 实时检测主机上运行的 Python 进程
2. **进程管理** - 安全终止一个或多个 Python 进程（保护自身进程）
3. **脚本配置** - 通过 YAML 文件管理脚本配置
4. **日志查看** - 实时查看脚本输出和错误日志
5. **运行历史** - 记录脚本执行历史和状态

### 技术栈
- FastAPI + Uvicorn (Web 框架)
- SQLAlchemy + SQLite (数据持久化)
- psutil (进程管理)
- PyYAML (配置管理)
- Vue3 + Element Plus (前端界面)

### 后期扩展
- Redis + Celery + Flower 分布式任务调度
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(router)

# 前端静态文件目录
frontend_dist = os.path.join(os.path.dirname(__file__), 'frontend', 'dist')

if os.path.exists(frontend_dist):
    # 挂载静态资源目录
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, 'assets')), name="assets")
    
    # 处理前端路由 - 返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """处理前端 SPA 路由"""
        # API 路由由 router 处理，这里只处理前端路由
        if full_path.startswith("api/") or full_path == "docs" or full_path == "redoc":
            return None
        return FileResponse(os.path.join(frontend_dist, 'index.html'))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8900,
        reload=True,
        log_level="info"
    )