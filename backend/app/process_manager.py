"""
进程管理服务层
负责启动、停止、监控 Python 脚本进程
"""
import os
import sys
import psutil
import signal
import subprocess
import asyncio
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json
import time
import aiofiles

from app.config_manager import ScriptConfigData, config_manager
from app.database import get_db_context
from app.models import ScriptConfig, ScriptHistory, SystemLog
from app.logger import LogConfig, get_logger, get_script_log_path


class ProcessInfo:
    """进程信息"""
    def __init__(self, pid: int, name: str, cmdline: List[str], 
                 create_time: float, cpu_percent: float, memory_mb: float,
                 status: str):
        self.pid = pid
        self.name = name
        self.cmdline = cmdline
        self.create_time = create_time
        self.cpu_percent = cpu_percent
        self.memory_mb = memory_mb
        self.status = status

    def to_dict(self) -> Dict:
        return {
            'pid': self.pid,
            'name': self.name,
            'cmdline': ' '.join(self.cmdline) if self.cmdline else '',
            'create_time': datetime.fromtimestamp(self.create_time).isoformat() if self.create_time else None,
            'cpu_percent': round(self.cpu_percent, 2),
            'memory_mb': round(self.memory_mb, 2),
            'status': self.status,
        }


class ProcessManager:
    """进程管理器"""

    # 当前运行的进程记录 {script_name: {'process': Popen, 'log_file': path}}
    running_processes: Dict[str, Dict] = {}

    def __init__(self):
        self.self_pid = os.getpid()
        self.logger = get_logger('process_manager')

    def get_python_processes(self) -> List[ProcessInfo]:
        """获取所有正在运行的 Python 进程"""
        processes = []
        
        # 获取配置文件中所有脚本
        config_all_scripts_dict = config_manager.get_all_configs()
        config_all_scripts = []
        for k, v in config_all_scripts_dict.items():
            config_all_scripts.append(v.to_dict().get("script_path"))
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 
                                          'cpu_percent', 'memory_info', 'status']):
            try:
                # 检查是否是 Python 进程
                name = proc.info['name'].lower()
                
                if 'python' in name:
                    cmdline = proc.info['cmdline'] or []
                    
                    # 统计配置文件中正在运行的进程
                    for config_script_path in config_all_scripts:
                        if config_script_path in cmdline:
                    
                            cpu = proc.cpu_percent(interval=0.1)
                            memory = proc.info['memory_info'].rss / (1024 * 1024)  # MB
                            
                            process_info = ProcessInfo(
                                pid=proc.info['pid'],
                                name=proc.info['name'],
                                cmdline=cmdline,
                                create_time=proc.info['create_time'],
                                cpu_percent=cpu,
                                memory_mb=memory,
                                status=proc.info['status']
                            )
                            processes.append(process_info)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return processes

    def get_process_by_pid(self, pid: int) -> Optional[ProcessInfo]:
        """根据 PID 获取进程信息"""
        try:
            proc = psutil.Process(pid)
            
            # 检查是否是 Python 进程
            name = proc.name().lower()
            if 'python' not in name:
                return None
            
            # 跳过自身
            if pid == self.self_pid:
                return None
            
            cmdline = proc.cmdline() or []
            if any('uvicorn' in cmd or 'gunicorn' in cmd for cmd in cmdline):
                return None
            
            cpu = proc.cpu_percent(interval=0.1)
            memory = proc.memory_info().rss / (1024 * 1024)
            
            return ProcessInfo(
                pid=pid,
                name=proc.name(),
                cmd=cmdline,
                create_time=proc.create_time(),
                cpu_percent=cpu,
                memory_mb=memory,
                status=proc.status()
            )
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

    def kill_process(self, pid: int, force: bool = False) -> Tuple[bool, str]:
        """
        终止指定进程
        :param pid: 进程ID
        :param force: 是否强制终止（SIGKILL）
        :return: (是否成功, 消息)
        """
        # 安全检查：不允许终止自身
        if pid == self.self_pid:
            return False, "不能终止 Web 管理服务进程"
        
        try:
            proc = psutil.Process(pid)
            
            # 检查是否是 Python 进程
            if 'python' not in proc.name().lower():
                return False, "只能终止 Python 进程"
            
            # 检查是否是 uvicorn 进程
            cmdline = proc.cmdline() or []
            if any('uvicorn' in cmd or 'gunicorn' in cmd for cmd in cmdline):
                return False, "不能终止 Web 服务相关进程"
            
            # 发送信号
            if force:
                proc.kill()  # SIGKILL
                sig_name = "SIGKILL"
            else:
                proc.terminate()  # SIGTERM
                sig_name = "SIGTERM"
            
            # 等待进程结束
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                if not force:
                    # 如果正常终止超时，强制终止
                    proc.kill()
                    proc.wait(timeout=3)
            
            # 记录日志
            self._log_action('kill_process', f'PID:{pid}', f'使用 {sig_name} 终止进程')
            
            return True, f"进程 {pid} 已终止"
            
        except psutil.NoSuchProcess:
            return False, f"进程 {pid} 不存在"
        except psutil.AccessDenied:
            return False, f"没有权限终止进程 {pid}"
        except Exception as e:
            return False, f"终止进程失败: {str(e)}"

    def kill_multiple_processes(self, pids: List[int]) -> Dict[int, Tuple[bool, str]]:
        """批量终止进程"""
        results = {}
        for pid in pids:
            results[pid] = self.kill_process(pid)
        return results

    def _start_script_internal(
        self, script_path: str, script_name: str, 
        working_dir: str = None, env_vars: Dict = None,
        python_path: str = None, timeout: int = 3600,
        schedule_type: str = 'manual',
        max_retries: int = 3, retry_delay: int = 60, retry_count: int = 0
    ) -> Tuple[bool, str, Optional[int]]:
        """
        内部方法：启动脚本的核心逻辑
        :param schedule_type: 调度类型 (manual/cron/interval)
        :return: (是否成功, 消息, 进程ID)
        """
        # 检查脚本是否存在
        if not os.path.isfile(script_path):
            return False, f"脚本文件不存在: {script_path}", None
        
        # 检查是否已在运行
        if script_name in self.running_processes:
            proc_info = self.running_processes[script_name]
            if proc_info.get('process') and proc_info['process'].poll() is None:
                return False, f"脚本 {script_name} 已在运行中", None
        
        # 准备环境变量
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # 准备工作目录
        cwd = working_dir or os.path.dirname(script_path)
        
        # 准备 Python 解释器
        python = python_path or sys.executable
        
        # 准备日志文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"{timestamp}.log"
        script_log_dir = LogConfig.SCRIPT_LOG_DIR / script_name
        script_log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(script_log_dir / log_filename)
        
        try:
            # 启动进程（使用 PIPE 捕获输出，以便异步写入日志）
            process = subprocess.Popen(
                [python, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env,
                start_new_session=True  # 创建新的进程组
            )
            
            # 启动异步日志写入任务
            self._start_async_log_writer(process, log_file)
            
            # 记录运行信息
            self.running_processes[script_name] = {
                'process': process,
                'log_file': log_file,
                'start_time': datetime.now(),
                'timeout': timeout,
                'schedule_type': schedule_type
            }
            
            # 创建历史记录
            with get_db_context() as db:
                history = ScriptHistory(
                    script_name=script_name,
                    script_path=script_path,
                    pid=process.pid,
                    status='running',
                    log_file=log_file
                )
                db.add(history)
                db.commit()
                history_id = history.id
            
            # 更新配置状态
            with get_db_context() as db:
                config = db.query(ScriptConfig).filter(
                    ScriptConfig.name == script_name
                ).first()
                if config:
                    config.current_pid = process.pid
                    config.status = 'running'
                    config.last_run_time = datetime.now()
                    db.commit()
            
            # 启动监控线程
            self._start_monitor_thread(
                script_name=script_name, process=process, 
                script_path=script_path, working_dir=working_dir, env_vars=env_vars,
                python_path=python_path, schedule_type=schedule_type,
                history_id=history_id, timeout=timeout, 
                max_retries=max_retries, retry_delay=retry_delay, retry_count=retry_count
            )
            
            # 记录日志
            self._log_action('start_script', script_name, 
                           f'启动脚本 [{schedule_type}]，PID: {process.pid}')
            
            return True, f"脚本 {script_name} 已启动，PID: {process.pid}", process.pid
            
        except Exception as e:
            return False, f"启动脚本失败: {str(e)}", None

    def auto_start_scripts(self):
        """
        启动自启动的脚本
        """
        with get_db_context() as db:
            scripts = db.query(ScriptConfig).filter(
                ScriptConfig.schedule_type == "manual",
                ScriptConfig.enabled  == True,
                ScriptConfig.auto_start == True
            ).all()
            for script in scripts:
                env_vars = eval(script.env_vars) if script.env_vars else None
                self.start_manual_script(
                    script_name=script.name,
                    script_path=script.script_path,
                    working_dir=script.working_dir,
                    env_vars=env_vars,
                    python_path=script.python_path,
                    timeout=script.timeout,
                    max_retries=script.max_retries,
                    retry_delay=script.retry_delay
                )
                
            self.logger.info(f"已加载 {len(scripts)} 个自启动的非定时任务")


    def start_manual_script(
        self, script_path: str, script_name: str, 
        working_dir: str = None, env_vars: Dict = None,
        python_path: str = None, timeout: int = 3600,
        max_retries: int = 3, retry_delay: int = 60, retry_count: int = 0
    ) -> Tuple[bool, str, Optional[int]]:
        """
        手动启动脚本
        """
        return self._start_script_internal(
            script_path=script_path,
            script_name=script_name,
            working_dir=working_dir,
            env_vars=env_vars,
            python_path=python_path,
            timeout=timeout,
            schedule_type='manual',
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_count=retry_count
        )
    
    def start_scheduled_script(
        self, script_path: str, script_name: str,
        working_dir: str = None, env_vars: Dict = None,
        python_path: str = None, timeout: int = 3600,
        schedule_type: str = 'cron',
        max_retries: int = 3, retry_delay: int = 60, retry_count: int = 0
    ) -> Tuple[bool, str, Optional[int]]:
        """
        定时任务启动脚本（由调度器调用）
        :param schedule_type: 'cron' 或 'interval'
        """
        return self._start_script_internal(
            script_path=script_path,
            script_name=script_name,
            working_dir=working_dir,
            env_vars=env_vars,
            python_path=python_path,
            timeout=timeout,
            schedule_type=schedule_type,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_count=retry_count
        )
    
    def stop_script(self, script_name: str) -> Tuple[bool, str]:
        """停止由本系统启动的脚本"""
        if script_name not in self.running_processes:
            return False, f"脚本 {script_name} 未在运行中"
        
        proc_info = self.running_processes[script_name]
        process = proc_info.get('process')
        
        if not process or process.poll() is not None:
            # 进程已结束，清理记录
            del self.running_processes[script_name]
            return False, f"脚本 {script_name} 进程已结束"
        
        try:
            # 获取进程组ID，终止整个进程组
            pgid = os.getpgid(process.pid)
            os.killpg(pgid, signal.SIGTERM)
            
            # 等待结束
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
                process.wait(timeout=3)
            
            del self.running_processes[script_name]
            
            # 记录日志
            self._log_action('stop_script', script_name, '停止脚本')
            
            return True, f"脚本 {script_name} 已停止"
            
        except Exception as e:
            return False, f"停止脚本失败: {str(e)}"

    async def get_script_log(self, script_name: str, lines: int = 100) -> Tuple[bool, str]:
        """获取脚本日志"""
        if script_name not in self.running_processes:
            # 查询历史记录获取最新日志
            with get_db_context() as db:
                history = db.query(ScriptHistory).filter(
                    ScriptHistory.script_name == script_name
                ).order_by(ScriptHistory.start_time.desc()).first()
                
                if history and history.log_file:
                    log_file = history.log_file
                else:
                    return False, f"未找到脚本 {script_name} 的日志"
        else:
            log_file = self.running_processes[script_name].get('log_file')
        
        if not log_file or not os.path.exists(log_file):
            return False, f"日志文件不存在"
        
        try:
            # 采用异步io的方式
            async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                all_lines = content.splitlines(keepends=True)
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                return True, ''.join(last_lines)
    
        except Exception as e:
            return False, f"读取日志失败: {str(e)}"

    def get_script_history(self, script_name: str, limit: int = 20) -> List[Dict]:
        """获取脚本运行历史"""
        with get_db_context() as db:
            histories = db.query(ScriptHistory).filter(
                ScriptHistory.script_name == script_name
            ).order_by(ScriptHistory.start_time.desc()).limit(limit).all()
            
            return [{
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
            } for h in histories]

    def _start_async_log_writer(self, process: subprocess.Popen, log_file: str):
        """
        启动异步日志写入任务
        使用后台线程运行异步事件循环，持续从进程管道读取输出并异步写入文件
        """
        def run_async_writer():
            """在线程中运行异步日志写入"""
            asyncio.run(self._async_log_writer(process, log_file))
        
        thread = threading.Thread(target=run_async_writer, daemon=True)
        thread.start()

    async def _async_log_writer(self, process: subprocess.Popen, log_file: str):
        """
        异步日志写入协程
        从进程 stdout 管道读取数据并异步写入文件
        """
        try:
            async with aiofiles.open(log_file, 'w', encoding='utf-8') as f:
                # 使用异步方式读取管道
                # 由于 process.stdout 是同步文件对象，我们需要在线程池中执行读取
                loop = asyncio.get_event_loop()
                
                while True:
                    # 在线程池中执行同步读取，避免阻塞事件循环
                    line = await loop.run_in_executor(None, process.stdout.readline)
                    
                    if not line:
                        # 检查进程是否已结束
                        if process.poll() is not None:
                            break
                        continue
                    
                    # 异步写入文件
                    await f.write(line.decode('utf-8', errors='replace'))
                    # 定期刷新，确保日志实时可见
                    await f.flush()
                    
        except Exception as e:
            self.logger.error(f"异步日志写入异常: {e}")

    def _start_monitor_thread(
        self, script_name: str, process: subprocess.Popen, 
        script_path: str, working_dir: str = None, env_vars: Dict = None,
        python_path: str = None, schedule_type: str = 'manual',
        history_id: int = None, timeout: int = 3600,
        max_retries: int = 3, retry_delay: int = 60, retry_count: int = 0
    ):
        """启动进程监控线程"""
        def monitor():
            # 创建超时时间
            start_time = datetime.now()
            try:
                while True:
                    return_code = process.poll()
                    if return_code is not None:
                        # 进程已结束
                        break
                    
                    end_time = datetime.now()
                    elapsed = (end_time - start_time).total_seconds()

                    if elapsed > timeout:
                        # 超时终止
                        self.logger.warning(f"脚本 {script_name} 运行超时 ({timeout}秒)，正在终止...")
                        _, message = self.kill_process(process.pid)
                        self.logger.warning(f"脚本 {script_name} {message}")

                        # 超时重试
                        if retry_count < max_retries:
                            self.logger.info(f"脚本 {script_name} 将在 {retry_delay} 秒后重试 ({retry_count + 1}/{max_retries})")
                            time.sleep(retry_delay)

                            self._start_script_internal(
                                script_path=script_path, script_name=script_name,
                                working_dir=working_dir, env_vars=env_vars,
                                python_path=python_path, timeout=timeout,
                                schedule_type=schedule_type,
                                max_retries=max_retries, retry_delay=retry_delay, retry_count=retry_count + 1
                            )
                        
                        self._update_history_status(
                            history_id=history_id, 
                            script_name=script_name,
                            end_time=end_time,
                            exit_code=None,
                            duration=int(elapsed),
                            status="timeout",
                            retry_count=retry_count
                        )
                        return

                    time.sleep(1)
            
            
                # 正常结束处理 
                end_time = datetime.now()
                exit_code = process.returncode
                duration = int((end_time - start_time).total_seconds())
                
                self._update_history_status(
                    history_id=history_id,
                    script_name=script_name,
                    end_time=end_time,
                    exit_code=exit_code,
                    duration=duration,
                    status='completed' if exit_code == 0 else 'failed',
                )
                
                
            except Exception as e:
                self.logger.error(f"监控线程异常: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    
    def _update_history_status(
        self, history_id: int, end_time, script_name: str, 
        exit_code: int, duration: int, 
        status: str, retry_count: int = 0,
    ):
        """更新历史记录"""
        
        # 更新历史记录
        with get_db_context() as db:
            history = db.query(ScriptHistory).filter(
                ScriptHistory.id == history_id
            ).first()
            
            if history:
                history.end_time = end_time
                history.exit_code = exit_code
                history.duration = duration
                history.status = status
                history.retry_count = retry_count
                # 读取错误信息
                if exit_code != 0 and history.log_file:
                    try:
                        with open(history.log_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 取最后 500 字符作为错误信息
                            history.error_message = content[-500:] if len(content) > 500 else content
                    except:
                        pass
                
                db.commit()
        
        # 更新配置状态
        with get_db_context() as db:
            config = db.query(ScriptConfig).filter(
                ScriptConfig.name == script_name
            ).first()
            if config:
                config.current_pid = None
                config.status = 'stopped'
                db.commit()
        
        # 清理运行记录
        if script_name in self.running_processes:
            del self.running_processes[script_name]
    
    def _log_action(self, action: str, target: str, message: str, level: str = 'INFO'):
        """记录系统日志"""
        try:
            with get_db_context() as db:
                log = SystemLog(
                    level=level,
                    module='process_manager',
                    action=action,
                    target=target,
                    message=message
                )
                db.add(log)
                db.commit()
        except Exception as e:
            self.logger.error(f"记录日志失败: {e}")


# 全局进程管理器实例
process_manager = ProcessManager()