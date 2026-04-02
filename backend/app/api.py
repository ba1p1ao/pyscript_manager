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
from app.scheduler_service import scheduler_service
from app.log_cleaner import log_cleaner
from app.logger import LogConfig

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
        
        # 统计定时任务总数
        scheduled_total = sum(1 for s in result if s['schedule_type'] in ['cron', 'interval'])
        
        return {
            "success": True,
            "data": result,
            "count": len(result),
            "scheduled_total": scheduled_total
        }


@router.post("/api/scripts")
async def create_script_config(config: ScriptConfigCreate):
    """
    创建新的脚本配置
    
    添加配置到 YAML 文件并同步到数据库。
    如果是 cron 或 interval 类型，自动添加调度任务。
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
    
    # 如果是 cron 或 interval 类型且已启用，添加调度任务
    if config.enabled and config.schedule_type in ['cron', 'interval']:
        scheduler_service.add_job(
            script_name=config.name,
            schedule_type=config.schedule_type,
            schedule=config.schedule,
            interval_seconds=config.interval_seconds
        )
    
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
    
    # 同步到数据库并处理调度任务
    with get_db_context() as db:
        db_config = db.query(ScriptConfig).filter(
            ScriptConfig.name == script_name
        ).first()
        
        if db_config:
            old_schedule_type = db_config.schedule_type
            old_enabled = db_config.enabled
            
            for key, value in update_data.items():
                if key == 'env_vars' and value:
                    setattr(db_config, key, str(value))
                elif hasattr(db_config, key):
                    setattr(db_config, key, value)
            db.commit()
            
            # 处理调度任务变更
            new_schedule_type = update_data.get('schedule_type', old_schedule_type)
            new_enabled = update_data.get('enabled', old_enabled)
            
            # 如果调度类型或启用状态改变，需要重新管理调度任务
            if 'schedule_type' in update_data or 'enabled' in update_data or 'schedule' in update_data or 'interval_seconds' in update_data:
                # 先移除旧的调度任务
                scheduler_service.remove_job(script_name)
                
                # 如果是 cron 或 interval 且已启用，添加新的调度任务
                if new_enabled and new_schedule_type in ['cron', 'interval']:
                    scheduler_service.add_job(
                        script_name=script_name,
                        schedule_type=new_schedule_type,
                        schedule=db_config.schedule,
                        interval_seconds=db_config.interval_seconds
                    )
    
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
    
    # 移除调度任务（如果存在）
    scheduler_service.remove_job(script_name)
    
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
    
    从磁盘重新读取配置文件并同步到数据库，同时重新加载调度任务。
    """
    
    yaml_configs = config_manager.sync_config()
    
    # 重新加载调度任务
    scheduler_service.load_scheduled_scripts()
    
    return {
        "success": True,
        "message": f"配置重新加载完成，共 {len(yaml_configs)} 个脚本配置"
    }


# ============== 脚本执行 API ==============

@router.post("/api/scripts/{script_name}/start")
async def start_script(script_name: str):
    """
    启动脚本
    
    - manual: 立即执行一次
    - cron/interval: 添加到调度器，按计划执行
    
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
            schedule_type = yaml_config.schedule_type
            schedule = yaml_config.schedule
            interval_seconds = yaml_config.interval_seconds
            enabled = yaml_config.enabled
            auto_start = yaml_config.auto_start
        else:
            script_path = config.script_path
            working_dir = config.working_dir
            env_vars = eval(config.env_vars) if config.env_vars else None
            python_path = config.python_path
            timeout = config.timeout
            schedule_type = config.schedule_type
            schedule = config.schedule
            interval_seconds = config.interval_seconds
            enabled = config.enabled
            auto_start = config.auto_start
    
    if schedule_type == 'manual':
        # manual 类型：立即执行一次
        success, message, pid = process_manager.start_manual_script(
            script_path=script_path,
            script_name=script_name,
            working_dir=working_dir,
            env_vars=env_vars,
            python_path=python_path,
            timeout=timeout,
        )
    else:
        # cron/interval 类型：添加到调度器
        if not enabled:
            message = f"定时任务 {script_name} 未被启用"
            pid = None
        else:
            # 先启用脚本
            with get_db_context() as db:
                db_config = db.query(ScriptConfig).filter(
                    ScriptConfig.name == script_name
                ).first()
                if db_config:
                    db_config.enabled = True
                    db.commit()
        
            success = scheduler_service.add_job(
                script_name=script_name,
                schedule_type=schedule_type,
                schedule=schedule,
                interval_seconds=interval_seconds
            )
        
            if success:
                message = f"定时任务 {script_name} 已启动"
                pid = None
            else:
                raise HTTPException(status_code=400, detail="启动调度任务失败")
    
    return {
        "success": True,
        "message": message,
        "pid": pid,
        "schedule_type": schedule_type
    }


@router.post("/api/scripts/{script_name}/stop")
async def stop_script(script_name: str):
    """
    停止脚本
    
    - manual: 终止正在运行的进程
    - cron/interval: 从调度器移除，停止定时任务
    
    - **script_name**: 脚本名称
    """
    # 获取脚本类型
    with get_db_context() as db:
        config = db.query(ScriptConfig).filter(
            ScriptConfig.name == script_name
        ).first()
        
        if config:
            schedule_type = config.schedule_type
            # 更新为禁用状态
            config.enabled = False
            db.commit()
        else:
            yaml_config = config_manager.get_config(script_name)
            schedule_type = yaml_config.schedule_type if yaml_config else 'manual'
    
    if schedule_type == 'manual':
        # manual 类型：终止进程
        success, message = process_manager.stop_script(script_name)
    else:
        # cron/interval 类型：从调度器移除
        success = scheduler_service.remove_job(script_name)
        if success:
            message = f"定时任务 {script_name} 已停止"
        else:
            message = f"停止定时任务失败"
    
    return {
        "success": success,
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
        
        # 定时任务统计
        scheduled_total = db.query(ScriptConfig).filter(
            ScriptConfig.schedule_type.in_(['cron', 'interval'])
        ).count()
        scheduled_active = db.query(ScriptConfig).filter(
            ScriptConfig.schedule_type.in_(['cron', 'interval']),
            ScriptConfig.enabled == True
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
            "scheduled_total": scheduled_total,
            "scheduled_active": scheduled_active,
            "today_runs": today_runs_count,
            "today_failed": today_failed_count,
        }
    }


# ============== 定时任务 API ==============

@router.get("/api/scheduled")
async def list_scheduled_tasks():
    """
    获取所有定时任务列表
    
    返回所有 cron 和 interval 类型的脚本及其调度状态。
    """
    with get_db_context() as db:
        scripts = db.query(ScriptConfig).filter(
            ScriptConfig.schedule_type.in_(['cron', 'interval'])
        ).all()
        
        # 获取调度器中的任务状态
        scheduler_jobs = scheduler_service.get_all_jobs()
        job_map = {j['id']: j for j in scheduler_jobs}
        
        result = []
        for script in scripts:
            job_id = f"script_{script.name}"
            job_info = job_map.get(job_id)
            
            result.append({
                'id': script.id,
                'name': script.name,
                'script_path': script.script_path,
                'description': script.description,
                'schedule_type': script.schedule_type,
                'schedule': script.schedule,
                'interval_seconds': script.interval_seconds,
                'enabled': script.enabled,
                'status': script.status,
                'next_run_time': job_info['next_run_time'] if job_info and job_info.get('next_run_time') else None,
                'last_run_time': script.last_run_time.isoformat() if script.last_run_time else None,
            })
        
        return {
            "success": True,
            "data": result,
            "count": len(result)
        }


# ============== 日志管理 API ==============

class LogConfigUpdate(BaseModel):
    """日志配置更新"""
    script_retention_days: Optional[int] = None
    history_retention_count: Optional[int] = None
    system_log_retention_days: Optional[int] = None
    archive_after_days: Optional[int] = None
    archive_retention_days: Optional[int] = None


@router.get("/api/logs/stats")
async def get_log_stats():
    """
    获取日志统计信息
    
    返回各类日志文件的大小、数量等信息。
    """
    stats = log_cleaner.get_log_stats()
    
    return {
        "success": True,
        "data": stats
    }


@router.post("/api/logs/clean")
async def clean_logs(
    clean_scripts: bool = Query(True, description="是否清理脚本日志"),
    clean_history: bool = Query(True, description="是否清理历史记录"),
    clean_system_logs: bool = Query(True, description="是否清理系统日志"),
    archive: bool = Query(True, description="是否归档旧日志")
):
    """
    手动触发日志清理
    
    - **clean_scripts**: 是否清理脚本日志文件
    - **clean_history**: 是否清理数据库历史记录
    - **clean_system_logs**: 是否清理系统日志
    - **archive**: 是否归档旧日志
    """
    results = {
        'script_logs_deleted': 0,
        'script_logs_freed_mb': 0,
        'archives_created': 0,
        'archives_deleted': 0,
        'history_deleted': 0,
        'system_logs_deleted': 0,
    }
    
    try:
        # 1. 归档旧日志
        if archive:
            results['archives_created'] = log_cleaner.archive_old_logs()
            results['archives_deleted'] = log_cleaner.clean_old_archives()
        
        # 2. 清理过期日志
        if clean_scripts:
            deleted, freed = log_cleaner.clean_script_logs()
            results['script_logs_deleted'] = deleted
            results['script_logs_freed_mb'] = freed
        
        # 3. 清理数据库历史
        if clean_history:
            results['history_deleted'] = log_cleaner.clean_database_history()
        
        # 4. 清理系统日志
        if clean_system_logs:
            results['system_logs_deleted'] = log_cleaner.clean_system_logs()
        
        return {
            "success": True,
            "message": "日志清理完成",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"日志清理失败: {str(e)}")


@router.get("/api/logs/config")
async def get_log_config():
    """
    获取日志配置
    """
    return {
        "success": True,
        "data": {
            "script_retention_days": LogConfig.SCRIPT_RETENTION_DAYS,
            "script_max_files": LogConfig.SCRIPT_MAX_FILES_PER_SCRIPT,
            "history_retention_count": LogConfig.HISTORY_RETENTION_COUNT,
            "system_log_retention_days": LogConfig.SYSTEM_LOG_RETENTION_DAYS,
            "archive_after_days": LogConfig.ARCHIVE_AFTER_DAYS,
            "archive_retention_days": LogConfig.ARCHIVE_RETENTION_DAYS,
            "app_max_bytes": LogConfig.APP_MAX_BYTES,
            "app_backup_count": LogConfig.APP_BACKUP_COUNT,
            "log_dirs": {
                "app": str(LogConfig.APP_LOG_DIR),
                "scripts": str(LogConfig.SCRIPT_LOG_DIR),
                "archive": str(LogConfig.ARCHIVE_DIR),
            }
        }
    }


@router.put("/api/logs/config")
async def update_log_config(config: LogConfigUpdate):
    """
    更新日志配置
    
    注意：更新配置后，下次清理任务将使用新配置。
    配置不会持久化，重启后恢复默认值。
    """
    if config.script_retention_days is not None:
        if config.script_retention_days < 1:
            raise HTTPException(status_code=400, detail="保留天数不能小于 1")
        LogConfig.SCRIPT_RETENTION_DAYS = config.script_retention_days
    
    if config.history_retention_count is not None:
        if config.history_retention_count < 10:
            raise HTTPException(status_code=400, detail="历史记录保留数不能小于 10")
        LogConfig.HISTORY_RETENTION_COUNT = config.history_retention_count
    
    if config.system_log_retention_days is not None:
        if config.system_log_retention_days < 1:
            raise HTTPException(status_code=400, detail="系统日志保留天数不能小于 1")
        LogConfig.SYSTEM_LOG_RETENTION_DAYS = config.system_log_retention_days
    
    if config.archive_after_days is not None:
        if config.archive_after_days < 1:
            raise HTTPException(status_code=400, detail="归档天数不能小于 1")
        LogConfig.ARCHIVE_AFTER_DAYS = config.archive_after_days
    
    if config.archive_retention_days is not None:
        if config.archive_retention_days < 1:
            raise HTTPException(status_code=400, detail="归档保留天数不能小于 1")
        LogConfig.ARCHIVE_RETENTION_DAYS = config.archive_retention_days
    
    return {
        "success": True,
        "message": "日志配置已更新"
    }