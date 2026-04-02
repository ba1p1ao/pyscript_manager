"""
调度服务层
使用 APScheduler 实现 Cron 和 Interval 定时任务调度
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError

from app.database import get_db_context
from app.models import ScriptConfig
from app.process_manager import process_manager
from app.logger import get_logger


class SchedulerService:
    """调度服务 - 管理 Cron 和 Interval 定时任务"""
    
    def __init__(self):
        # 创建异步调度器（适合 FastAPI）
        self.scheduler = AsyncIOScheduler()
        self._started = False
        self.logger = get_logger('scheduler')
    
    def start(self):
        """启动调度器"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            self.logger.info("调度器已启动")
            
            # 先清理无效的调度任务（数据库中不存在的）
            self._cleanup_invalid_jobs()
            
            # 从数据库加载所有定时任务
            self.load_scheduled_scripts()
    
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            self.logger.info("调度器已关闭")
    
    def _cleanup_invalid_jobs(self):
        """清理无效的调度任务（数据库中已被删除的脚本）"""
        with get_db_context() as db:
            # 获取数据库中所有脚本名称
            db_scripts = db.query(ScriptConfig.name).all()
            valid_names = {s.name for s in db_scripts}
        
        # 获取当前调度器中的所有任务
        current_jobs = self.scheduler.get_jobs()
        removed_count = 0
        
        for job in current_jobs:
            # 任务 ID 格式为 "script_{script_name}"
            if job.id.startswith('script_'):
                script_name = job.id[7:]  # 移除 "script_" 前缀
                if script_name not in valid_names:
                    self.remove_job(script_name)
                    removed_count += 1
                    self.logger.info(f"清理无效任务: {script_name}")
        
        if removed_count > 0:
            self.logger.info(f"共清理 {removed_count} 个无效任务")
    
    def load_scheduled_scripts(self):
        """从数据库加载所有定时任务（cron 和 interval）"""
        with get_db_context() as db:
            # 查询所有自启动的非 manual 类型的脚本
            scripts = db.query(ScriptConfig).filter(
                ScriptConfig.auto_start == True,
                ScriptConfig.enabled == True,
                ScriptConfig.schedule_type.in_(['cron', 'interval'])
            ).all()
            
            for script in scripts:
                self.add_job(
                    script_name=script.name,
                    schedule_type=script.schedule_type,
                    schedule=script.schedule,
                    interval_seconds=script.interval_seconds
                )
                
            self.logger.info(f"已加载 {len(scripts)} 个定时任务")
    
    def add_job(self, script_name: str, schedule_type: str, 
                schedule: Optional[str] = None, 
                interval_seconds: Optional[int] = None) -> bool:
        """
        添加定时任务
        
        :param script_name: 脚本名称
        :param schedule_type: 调度类型 (cron / interval)
        :param schedule: Cron 表达式（如 "0 8 * * *" 表示每天 8 点）
        :param interval_seconds: 间隔秒数
        :return: 是否成功
        """
        try:
            # 如果任务已存在，先移除
            self.remove_job(script_name)
            
            if schedule_type == 'cron':
                if not schedule:
                    self.logger.warning(f"Cron 任务 {script_name} 缺少 cron 表达式")
                    return False
                
                # 解析 cron 表达式
                # 支持格式: "分 时 日 月 周" 或 "hour=8, minute=0"
                trigger = self._parse_cron_expression(schedule)
                if not trigger:
                    self.logger.error(f"Cron 表达式解析失败: {schedule}")
                    return False
                
                self.scheduler.add_job(
                    func=self._execute_script,
                    trigger=trigger,
                    id=f"script_{script_name}",
                    args=[script_name],
                    name=script_name,
                    misfire_grace_time=60,  # 错过执行时间的容忍秒数
                    coalesce=True,          # 合并错过的多次执行
                    max_instances=1         # 同一任务最多同时运行 1 个实例
                )
                
                # 更新下次执行时间
                self._update_next_run_time(script_name)
                
                self.logger.info(f"已添加 Cron 任务: {script_name} ({schedule})")
                return True
                
            elif schedule_type == 'interval':
                if not interval_seconds or interval_seconds <= 0:
                    self.logger.warning(f"Interval 任务 {script_name} 缺少有效的间隔时间")
                    return False
                
                self.scheduler.add_job(
                    func=self._execute_script,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id=f"script_{script_name}",
                    args=[script_name],
                    name=script_name,
                    misfire_grace_time=60,
                    coalesce=True,
                    max_instances=1
                )
                
                # 更新下次执行时间
                self._update_next_run_time(script_name)
                
                self.logger.info(f"已添加 Interval 任务: {script_name} (每 {interval_seconds} 秒)")
                return True
                
            else:
                self.logger.warning(f"不支持的调度类型: {schedule_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"添加任务失败: {e}")
            return False
    
    def remove_job(self, script_name: str) -> bool:
        """移除定时任务"""
        try:
            job_id = f"script_{script_name}"
            self.scheduler.remove_job(job_id)
            self.logger.info(f"已移除任务: {script_name}")
            return True
        except JobLookupError:
            # 任务不存在，忽略
            return True
        except Exception as e:
            self.logger.error(f"移除任务失败: {e}")
            return False
    
    def pause_job(self, script_name: str) -> bool:
        """暂停定时任务"""
        try:
            job_id = f"script_{script_name}"
            self.scheduler.pause_job(job_id)
            self.logger.info(f"已暂停任务: {script_name}")
            return True
        except JobLookupError:
            self.logger.warning(f"任务不存在: {script_name}")
            return False
        except Exception as e:
            self.logger.error(f"暂停任务失败: {e}")
            return False
    
    def resume_job(self, script_name: str) -> bool:
        """恢复定时任务"""
        try:
            job_id = f"script_{script_name}"
            self.scheduler.resume_job(job_id)
            self.logger.info(f"已恢复任务: {script_name}")
            return True
        except JobLookupError:
            self.logger.warning(f"任务不存在: {script_name}")
            return False
        except Exception as e:
            self.logger.error(f"恢复任务失败: {e}")
            return False
    
    def get_job_info(self, script_name: str) -> Optional[Dict]:
        """获取任务信息"""
        try:
            job_id = f"script_{script_name}"
            job = self.scheduler.get_job(job_id)
            
            if job:
                return {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                }
            return None
        except Exception as e:
            self.logger.error(f"获取任务信息失败: {e}")
            return None
    
    def get_all_jobs(self) -> List[Dict]:
        """获取所有定时任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
            })
        return jobs
    
    async def _execute_script(self, script_name: str):
        """
        执行脚本（由调度器调用）
        注意：这是异步方法，会在调度器的事件循环中执行
        """
        self.logger.info(f"触发执行: {script_name} at {datetime.now()}")
        
        try:
            # 获取脚本配置
            with get_db_context() as db:
                config = db.query(ScriptConfig).filter(
                    ScriptConfig.name == script_name
                ).first()
                
                if not config:
                    self.logger.warning(f"脚本配置不存在: {script_name}")
                    return
                
                # 检查是否启用
                if not config.enabled:
                    self.logger.info(f"脚本已禁用，跳过执行: {script_name}")
                    return
                
                # 检查是否已在运行（防止重复执行）
                if config.status == 'running':
                    self.logger.info(f"脚本正在运行，跳过执行: {script_name}")
                    return
                
                # 获取配置参数
                script_path = config.script_path
                working_dir = config.working_dir
                env_vars = eval(config.env_vars) if config.env_vars else None
                python_path = config.python_path
                timeout = config.timeout
                schedule_type = config.schedule_type
            
            # 调用进程管理器启动脚本
            success, message, pid = process_manager.start_scheduled_script(
                script_path=script_path,
                script_name=script_name,
                working_dir=working_dir,
                env_vars=env_vars,
                python_path=python_path,
                timeout=timeout,
                schedule_type=schedule_type  # 或从配置获取
            )
            
            if success:
                self.logger.info(f"脚本启动成功: {script_name}, PID: {pid}")
            else:
                self.logger.error(f"脚本启动失败: {script_name}, {message}")
                
            # 更新下次执行时间
            self._update_next_run_time(script_name)
            
        except Exception as e:
            self.logger.error(f"执行脚本异常: {e}")
    
    def _parse_cron_expression(self, schedule: str) -> Optional[CronTrigger]:
        """
        解析 Cron 表达式
        
        支持两种格式：
        1. 标准 5 字段: "分 时 日 月 周" (如 "0 8 * * *" 表示每天 8:00)
        2. 关键字参数: "hour=8, minute=0"
        """
        try:
            # 尝试解析关键字参数格式
            if '=' in schedule:
                kwargs = {}
                for part in schedule.split(','):
                    key, value = part.strip().split('=')
                    kwargs[key.strip()] = int(value.strip())
                return CronTrigger(**kwargs)
            
            # 解析标准 5 字段格式
            parts = schedule.strip().split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                return CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                )
            
            self.logger.warning(f"无效的 Cron 表达式格式: {schedule}")
            return None
            
        except Exception as e:
            self.logger.error(f"解析 Cron 表达式异常: {e}")
            return None
    
    def _update_next_run_time(self, script_name: str):
        """更新脚本的下次执行时间"""
        try:
            job_info = self.get_job_info(script_name)
            if job_info and job_info.get('next_run_time'):
                with get_db_context() as db:
                    config = db.query(ScriptConfig).filter(
                        ScriptConfig.name == script_name
                    ).first()
                    
                    if config:
                        from datetime import datetime
                        # 解析 ISO 格式时间
                        next_run = datetime.fromisoformat(
                            job_info['next_run_time'].replace('Z', '+00:00')
                        )
                        config.next_run_time = next_run.replace(tzinfo=None)
                        db.commit()
        except Exception as e:
            self.logger.error(f"更新下次执行时间失败: {e}")


# 全局调度服务实例
scheduler_service = SchedulerService()
