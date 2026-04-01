"""
API 路由层
提供 RESTful API 接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database import get_db_context
from app.models import ScriptConfig, ScriptHistory, SystemLog
from app.config_manager import config_manager, ScriptConfigData
from app.process_manager import process_manager

router = APIRouter()


# ============== Pydantic 模型 ==============

class ScriptConfigCreate(BaseModel):
    """创建脚本配置"""
    name: str
    script_path: str
    description: str = ""
    schedule: Optional[str] = None
    schedule_type: str = "manual"
    interval_seconds: Optional[int] = None
    max_retries: int = 3
    retry_delay: int = 60
    timeout: int = 3600
    working_dir: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    python_path: Optional[str] = None
    enabled: bool = True
    auto_start: bool = False


class ScriptConfigUpdate(BaseModel):
    """更新脚本配置"""
    description: Optional[str] = None
    schedule: Optional[str] = None
    schedule_type: Optional[str] = None
    interval_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    retry_delay: Optional[int] = None
    timeout: Optional[int] = None
    working_dir: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    python_path: Optional[str] = None
    enabled: Optional[bool] = None
    auto_start: Optional[bool] = None


class KillProcessRequest(BaseModel):
    """终止进程请求"""
    pids: List[int]
    force: bool = False


# ============== 进程管理 API ==============

@router.get("/api/processes")
async def list_python_processes():
    """
    获取所有正在运行的 Python 进程
    
    返回当前主机上所有 Python 进程的列表，包括 PID、命令行、CPU 使用率、内存使用等信息。
    """
    processes = process_manager.get_python_processes()
    return {
        "success": True,
        "data": [p.to_dict() for p in processes],
        "count": len(processes)
    }


@router.get("/api/processes/{pid}")
async def get_process_detail(pid: int):
    """
    获取指定进程详情
    
    - **pid**: 进程ID
    """
    process = process_manager.get_process_by_pid(pid)
    if not process:
        raise HTTPException(status_code=404, detail="进程不存在或非 Python 进程")
    
    return {
        "success": True,
        "data": process.to_dict()
    }


@router.post("/api/processes/kill")
async def kill_processes(request: KillProcessRequest):
    """
    终止一个或多个进程
    
    - **pids**: 要终止的进程ID列表
    - **force**: 是否强制终止（使用 SIGKILL）
    
    注意：无法终止 Web 管理服务自身的进程
    """
    results = process_manager.kill_multiple_processes(request.pids)
    
    success_count = sum(1 for r in results.values() if r[0])
    fail_count = len(results) - success_count
    
    return {
        "success": True,
        "message": f"成功终止 {success_count} 个进程，失败 {fail_count} 个",
        "results": {str(pid): {"success": r[0], "message": r[1]} for pid, r in results.items()}
    }


@router.delete("/api/processes/{pid}")
async def kill_single_process(pid: int, force: bool = Query(False)):
    """
    终止单个进程
    
    - **pid**: 进程ID
    - **force**: 是否强制终止
    """
    success, message = process_manager.kill_process(pid, force)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message
    }


# ============== 脚本配置 API ==============

@router.get("/api/scripts")
async def list_script_configs():
    """
    获取所有脚本配置
    
    返回 YAML 配置文件中定义的所有脚本配置信息。
    """
    # 从数据库获取配置
    with get_db_context() as db:
        configs = db.query(ScriptConfig).all()
        
        # 同步 YAML 配置
        yaml_configs = config_manager.get_all_configs()
        
        # 合并数据
        result = []
        db_names = {c.name for c in configs}
        
        for config in configs:
            result.append({
                'id': config.id,
                'name': config.name,
                'script_path': config.script_path,
                'description': config.description,
                'schedule': config.schedule,
                'schedule_type': config.schedule_type,
                'interval_seconds': config.interval_seconds,
                'max_retries': config.max_retries,
                'retry_delay': config.retry_delay,
                'timeout': config.timeout,
                'working_dir': config.working_dir,
                'enabled': config.enabled,
                'auto_start': config.auto_start,
                'current_pid': config.current_pid,
                'status': config.status,
                'last_run_time': config.last_run_time.isoformat() if config.last_run_time else None,
                'next_run_time': config.next_run_time.isoformat() if config.next_run_time else None,
            })
        
        # 添加 YAML 中有但数据库中没有的配置
        for name, yaml_config in yaml_configs.items():
            if name not in db_names:
                result.append({
                    'id': None,
                    'name': yaml_config.name,
                    'script_path': yaml_config.script_path,
                    'description': yaml_config.description,
                    'schedule': yaml_config.schedule,
                    'schedule_type': yaml_config.schedule_type,
                    'interval_seconds': yaml_config.interval_seconds,
                    'max_retries': yaml_config.max_retries,
                    'retry_delay': yaml_config.retry_delay,
                    'timeout': yaml_config.timeout,
                    'working_dir': yaml_config.working_dir,
                    'enabled': yaml_config.enabled,
                    'auto_start': yaml_config.auto_start,
                    'current_pid': None,
                    'status': 'stopped',
                    'last_run_time': None,
                    'next_run_time': None,
                })
        
        return {
            "success": True,
            "data": result,
            "count": len(result)
        }


@router.post("/api/scripts")
async def create_script_config(config: ScriptConfigCreate):
    """
    创建新的脚本配置
    
    添加配置到 YAML 文件并同步到数据库。
    """
    # 验证配置
    config_data = ScriptConfigData(**config.model_dump())
    errors = config_manager.validate_config(config_data)
    
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    # 添加到 YAML
    if not config_manager.add_config(config_data):
        raise HTTPException(status_code=400, detail="脚本名称已存在")
    
    # 同步到数据库
    with get_db_context() as db:
        db_config = ScriptConfig(
            name=config.name,
            script_path=config.script_path,
            description=config.description,
            schedule=config.schedule,
            schedule_type=config.schedule_type,
            interval_seconds=config.interval_seconds,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
            timeout=config.timeout,
            working_dir=config.working_dir,
            env_vars=str(config.env_vars) if config.env_vars else None,
            python_path=config.python_path,
            enabled=config.enabled,
            auto_start=config.auto_start,
            status='stopped'
        )
        db.add(db_config)
        db.commit()
    
    return {
        "success": True,
        "message": f"脚本配置 {config.name} 创建成功"
    }


@router.put("/api/scripts/{script_name}")
async def update_script_config(script_name: str, config: ScriptConfigUpdate):
    """
    更新脚本配置
    
    - **script_name**: 脚本名称
    """
    # 更新 YAML
    update_data = {k: v for k, v in config.model_dump().items() if v is not None}
    
    if not config_manager.update_config(script_name, **update_data):
        raise HTTPException(status_code=404, detail="脚本配置不存在")
    
    # 同步到数据库
    with get_db_context() as db:
        db_config = db.query(ScriptConfig).filter(
            ScriptConfig.name == script_name
        ).first()
        
        if db_config:
            for key, value in update_data.items():
                if key == 'env_vars' and value:
                    setattr(db_config, key, str(value))
                elif hasattr(db_config, key):
                    setattr(db_config, key, value)
            db.commit()
    
    return {
        "success": True,
        "message": f"脚本配置 {script_name} 更新成功"
    }


@router.delete("/api/scripts/{script_name}")
async def delete_script_config(script_name: str):
    """
    删除脚本配置
    
    - **script_name**: 脚本名称
    """
    if not config_manager.remove_config(script_name):
        raise HTTPException(status_code=404, detail="脚本配置不存在")
    
    # 同步到数据库
    with get_db_context() as db:
        db_config = db.query(ScriptConfig).filter(
            ScriptConfig.name == script_name
        ).first()
        
        if db_config:
            db.delete(db_config)
            db.commit()
    
    return {
        "success": True,
        "message": f"脚本配置 {script_name} 删除成功"
    }


@router.post("/api/scripts/reload")
async def reload_script_configs():
    """
    重新加载 YAML 配置文件
    
    从磁盘重新读取配置文件并同步到数据库。
    """
    config_manager.reload_config()
    
    # 同步到数据库
    yaml_configs = config_manager.get_all_configs()

    with get_db_context() as db:
        # 获取数据库中的所有配置
        db_configs = db.query(ScriptConfig).all()
        db_names = {c.name: c for c in db_configs}
        
        # 添加新配置
        for name, yaml_config in yaml_configs.items():
            if not db_names.get(name):
                new_config = ScriptConfig(
                    name=yaml_config.name,
                    script_path=yaml_config.script_path,
                    description=yaml_config.description,
                    schedule=yaml_config.schedule,
                    schedule_type=yaml_config.schedule_type,
                    interval_seconds=yaml_config.interval_seconds,
                    max_retries=yaml_config.max_retries,
                    retry_delay=yaml_config.retry_delay,
                    timeout=yaml_config.timeout,
                    working_dir=yaml_config.working_dir,
                    env_vars=str(yaml_config.env_vars) if yaml_config.env_vars else None,
                    python_path=yaml_config.python_path,
                    enabled=yaml_config.enabled,
                    auto_start=yaml_config.auto_start,
                    status='stopped'
                )
                db.add(new_config)
            else:
                # print(yaml_config)
                old_config = db_names[name]
                for key, value in yaml_config.to_dict().items():
                    if key == "name":
                        continue
                    elif key == 'env_vars' and value:
                        setattr(old_config, key, str(value))
                    elif hasattr(old_config, key):
                        setattr(old_config, key, value)
                        
        for db_config in db_configs:
            if not yaml_configs.get(db_config.name):
                db.delete(db_config)
                 
        db.commit()
    
    return {
        "success": True,
        "message": f"配置重新加载完成，共 {len(yaml_configs)} 个脚本配置"
    }


# ============== 脚本执行 API ==============

@router.post("/api/scripts/{script_name}/start")
async def start_script(script_name: str):
    """
    启动脚本
    
    - **script_name**: 脚本名称
    """
    # 获取配置
    with get_db_context() as db:
        config = db.query(ScriptConfig).filter(
            ScriptConfig.name == script_name
        ).first()
        
        if not config:
            # 从 YAML 获取
            yaml_config = config_manager.get_config(script_name)
            if not yaml_config:
                raise HTTPException(status_code=404, detail="脚本配置不存在")
            
            script_path = yaml_config.script_path
            working_dir = yaml_config.working_dir
            env_vars = yaml_config.env_vars
            python_path = yaml_config.python_path
            timeout = yaml_config.timeout
        else:
            script_path = config.script_path
            working_dir = config.working_dir
            env_vars = eval(config.env_vars) if config.env_vars else None
            python_path = config.python_path
            timeout = config.timeout
    
    success, message, pid = process_manager.start_script(
        script_path=script_path,
        script_name=script_name,
        working_dir=working_dir,
        env_vars=env_vars,
        python_path=python_path,
        timeout=timeout
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message,
        "pid": pid
    }


@router.post("/api/scripts/{script_name}/stop")
async def stop_script(script_name: str):
    """
    停止脚本
    
    - **script_name**: 脚本名称
    """
    success, message = process_manager.stop_script(script_name)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message
    }


@router.get("/api/scripts/{script_name}/log")
async def get_script_log(script_name: str, lines: int = Query(100, ge=1, le=1000)):
    """
    获取脚本日志
    
    - **script_name**: 脚本名称
    - **lines**: 返回的日志行数（默认 100，最大 1000）
    """
    success, content = await process_manager.get_script_log(script_name, lines)
    
    if not success:
        raise HTTPException(status_code=404, detail=content)
    
    return {
        "success": True,
        "script_name": script_name,
        "log_content": content
    }


@router.get("/api/scripts/{script_name}/history")
async def get_script_history(script_name: str, limit: int = Query(20, ge=1, le=100)):
    """
    获取脚本运行历史
    
    - **script_name**: 脚本名称
    - **limit**: 返回记录数量
    """
    history = process_manager.get_script_history(script_name, limit)
    
    return {
        "success": True,
        "script_name": script_name,
        "data": history,
        "count": len(history)
    }


# ============== 历史记录 API ==============

@router.get("/api/history")
async def list_all_history(
    script_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    获取所有运行历史
    
    - **script_name**: 按脚本名称筛选
    - **status**: 按状态筛选（running/completed/failed/stopped）
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    with get_db_context() as db:
        query = db.query(ScriptHistory)
        
        if script_name:
            query = query.filter(ScriptHistory.script_name == script_name)
        
        if status:
            query = query.filter(ScriptHistory.status == status)
        
        total = query.count()
        histories = query.order_by(
            ScriptHistory.start_time.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            "success": True,
            "data": [{
                'id': h.id,
                'script_name': h.script_name,
                'pid': h.pid,
                'start_time': h.start_time.isoformat() if h.start_time else None,
                'end_time': h.end_time.isoformat() if h.end_time else None,
                'duration': h.duration,
                'exit_code': h.exit_code,
                'status': h.status,
                'retry_count': h.retry_count,
                'error_message': h.error_message,
            } for h in histories],
            "total": total,
            "limit": limit,
            "offset": offset
        }


# ============== 系统日志 API ==============

@router.get("/api/system-logs")
async def list_system_logs(
    level: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    获取系统操作日志
    
    - **level**: 按日志级别筛选（INFO/WARNING/ERROR）
    - **action**: 按操作类型筛选
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    with get_db_context() as db:
        query = db.query(SystemLog)
        
        if level:
            query = query.filter(SystemLog.level == level)
        
        if action:
            query = query.filter(SystemLog.action == action)
        
        total = query.count()
        logs = query.order_by(
            SystemLog.timestamp.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            "success": True,
            "data": [{
                'id': l.id,
                'timestamp': l.timestamp.isoformat() if l.timestamp else None,
                'level': l.level,
                'module': l.module,
                'action': l.action,
                'target': l.target,
                'message': l.message,
            } for l in logs],
            "total": total,
            "limit": limit,
            "offset": offset
        }


# ============== 统计 API ==============

@router.get("/api/stats")
async def get_statistics():
    """
    获取系统统计数据
    """
    with get_db_context() as db:
        # 获取当前进程数
        python_processes = process_manager.get_python_processes()

        # 同步数据库 - 检查 running 状态的脚本是否真的在运行
        running_scripts = db.query(ScriptConfig).filter(
            ScriptConfig.status == 'running'
        ).all()
        for script in running_scripts:
            # 检查脚本进程是否还在运行
            is_running = any(
                script.script_path in process.cmdline
                for process in python_processes
            )
            if not is_running:
                script.status = 'stopped'
                script.current_pid = None
                
        db.commit()

        total_scripts_count = db.query(ScriptConfig).count()
        running_scripts_count = db.query(ScriptConfig).filter(
            ScriptConfig.status == 'running'
        ).count()
        today_start_count = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_runs_count = db.query(ScriptHistory).filter(
            ScriptHistory.start_time >= today_start_count
        ).count()
        
        today_failed_count = db.query(ScriptHistory).filter(
            ScriptHistory.start_time >= today_start_count,
            ScriptHistory.status == 'failed'
        ).count()
    

    
    return {
        "success": True,
        "data": {
            "total_scripts": total_scripts_count,
            "running_scripts": running_scripts_count,
            "python_processes": len(python_processes),
            "today_runs": today_runs_count,
            "today_failed": today_failed_count,
        }
    }