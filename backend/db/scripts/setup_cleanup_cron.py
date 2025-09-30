#!/usr/bin/env python3
"""
设置Session清理定时任务

这个脚本用于设置定时任务，自动清理过期的session文件。
支持cron和systemd timer两种方式。

使用方法:
    python setup_cleanup_cron.py [--method=cron|systemd] [--interval=daily|weekly]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


class CleanupScheduler:
    """清理任务调度器"""
    
    def __init__(self, method: str = 'cron', interval: str = 'daily'):
        self.method = method
        self.interval = interval
        self.script_dir = Path(__file__).parent
        self.cleanup_script = self.script_dir / 'cleanup_sessions.py'
        self.project_root = self.script_dir.parent.parent
        
    def setup_cron_job(self) -> bool:
        """设置cron定时任务"""
        try:
            # 根据间隔设置cron表达式
            if self.interval == 'daily':
                cron_time = '0 2 * * *'  # 每天凌晨2点
                description = '每天凌晨2点'
            elif self.interval == 'weekly':
                cron_time = '0 2 * * 0'  # 每周日凌晨2点
                description = '每周日凌晨2点'
            else:
                print(f"不支持的间隔: {self.interval}")
                return False
            
            # 构建cron命令
            python_path = sys.executable
            cron_command = f"{cron_time} cd {self.project_root} && {python_path} {self.cleanup_script} --days=7"
            
            print(f"设置cron任务: {description}运行session清理")
            print(f"命令: {cron_command}")
            
            # 获取当前crontab
            try:
                current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode('utf-8')
            except subprocess.CalledProcessError:
                current_crontab = ''
            
            # 检查是否已存在相同的任务
            if 'cleanup_sessions.py' in current_crontab:
                print("检测到已存在的session清理任务，将替换...")
                # 移除旧的任务
                lines = current_crontab.split('\n')
                new_lines = [line for line in lines if 'cleanup_sessions.py' not in line]
                current_crontab = '\n'.join(new_lines)
            
            # 添加新任务
            new_crontab = current_crontab.rstrip() + '\n' + cron_command + '\n'
            
            # 写入新的crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_crontab)
            
            if process.returncode == 0:
                print("✅ Cron任务设置成功")
                return True
            else:
                print("❌ Cron任务设置失败")
                return False
                
        except Exception as e:
            print(f"❌ 设置cron任务时发生错误: {str(e)}")
            return False
    
    def setup_systemd_timer(self) -> bool:
        """设置systemd定时任务"""
        try:
            service_name = 'aetherfolio-session-cleanup'
            
            # 创建service文件内容
            service_content = f"""[Unit]
Description=AetherFolio Session Cleanup
After=network.target

[Service]
Type=oneshot
User={os.getenv('USER', 'root')}
WorkingDirectory={self.project_root}
ExecStart={sys.executable} {self.cleanup_script} --days=7
StandardOutput=journal
StandardError=journal
"""
            
            # 根据间隔设置timer文件内容
            if self.interval == 'daily':
                timer_schedule = 'OnCalendar=daily'
                description = '每天'
            elif self.interval == 'weekly':
                timer_schedule = 'OnCalendar=weekly'
                description = '每周'
            else:
                print(f"不支持的间隔: {self.interval}")
                return False
            
            timer_content = f"""[Unit]
Description=AetherFolio Session Cleanup Timer
Requires={service_name}.service

[Timer]
{timer_schedule}
Persistent=true

[Install]
WantedBy=timers.target
"""
            
            print(f"设置systemd定时任务: {description}运行session清理")
            
            # 写入service和timer文件
            service_file = f'/etc/systemd/system/{service_name}.service'
            timer_file = f'/etc/systemd/system/{service_name}.timer'
            
            print(f"创建service文件: {service_file}")
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            print(f"创建timer文件: {timer_file}")
            with open(timer_file, 'w') as f:
                f.write(timer_content)
            
            # 重新加载systemd配置
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            
            # 启用并启动timer
            subprocess.run(['systemctl', 'enable', f'{service_name}.timer'], check=True)
            subprocess.run(['systemctl', 'start', f'{service_name}.timer'], check=True)
            
            print("✅ Systemd定时任务设置成功")
            return True
            
        except PermissionError:
            print("❌ 需要root权限来设置systemd定时任务")
            print("请使用sudo运行此脚本")
            return False
        except Exception as e:
            print(f"❌ 设置systemd定时任务时发生错误: {str(e)}")
            return False
    
    def remove_cron_job(self) -> bool:
        """移除cron定时任务"""
        try:
            # 获取当前crontab
            try:
                current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode('utf-8')
            except subprocess.CalledProcessError:
                print("没有找到现有的crontab")
                return True
            
            # 移除session清理任务
            lines = current_crontab.split('\n')
            new_lines = [line for line in lines if 'cleanup_sessions.py' not in line]
            
            if len(new_lines) == len(lines):
                print("没有找到session清理的cron任务")
                return True
            
            # 写入新的crontab
            new_crontab = '\n'.join(new_lines)
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_crontab)
            
            if process.returncode == 0:
                print("✅ Cron任务移除成功")
                return True
            else:
                print("❌ Cron任务移除失败")
                return False
                
        except Exception as e:
            print(f"❌ 移除cron任务时发生错误: {str(e)}")
            return False
    
    def remove_systemd_timer(self) -> bool:
        """移除systemd定时任务"""
        try:
            service_name = 'aetherfolio-session-cleanup'
            
            # 停止并禁用timer
            subprocess.run(['systemctl', 'stop', f'{service_name}.timer'], check=False)
            subprocess.run(['systemctl', 'disable', f'{service_name}.timer'], check=False)
            
            # 删除文件
            service_file = f'/etc/systemd/system/{service_name}.service'
            timer_file = f'/etc/systemd/system/{service_name}.timer'
            
            if os.path.exists(service_file):
                os.remove(service_file)
                print(f"删除service文件: {service_file}")
            
            if os.path.exists(timer_file):
                os.remove(timer_file)
                print(f"删除timer文件: {timer_file}")
            
            # 重新加载systemd配置
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            
            print("✅ Systemd定时任务移除成功")
            return True
            
        except PermissionError:
            print("❌ 需要root权限来移除systemd定时任务")
            return False
        except Exception as e:
            print(f"❌ 移除systemd定时任务时发生错误: {str(e)}")
            return False
    
    def show_status(self):
        """显示当前定时任务状态"""
        print("\n=== 定时任务状态 ===")
        
        # 检查cron任务
        try:
            current_crontab = subprocess.check_output(['crontab', '-l'], stderr=subprocess.DEVNULL).decode('utf-8')
            if 'cleanup_sessions.py' in current_crontab:
                print("✅ Cron任务: 已设置")
                for line in current_crontab.split('\n'):
                    if 'cleanup_sessions.py' in line:
                        print(f"   {line}")
            else:
                print("❌ Cron任务: 未设置")
        except subprocess.CalledProcessError:
            print("❌ Cron任务: 未设置")
        
        # 检查systemd任务
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'aetherfolio-session-cleanup.timer'],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip() == 'active':
                print("✅ Systemd定时任务: 已激活")
            else:
                print("❌ Systemd定时任务: 未激活")
        except Exception:
            print("❌ Systemd定时任务: 未设置")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='设置Session清理定时任务')
    parser.add_argument('--method', choices=['cron', 'systemd'], default='cron',
                       help='定时任务方法 (默认: cron)')
    parser.add_argument('--interval', choices=['daily', 'weekly'], default='daily',
                       help='清理间隔 (默认: daily)')
    parser.add_argument('--remove', action='store_true',
                       help='移除现有的定时任务')
    parser.add_argument('--status', action='store_true',
                       help='显示当前定时任务状态')
    
    args = parser.parse_args()
    
    scheduler = CleanupScheduler(method=args.method, interval=args.interval)
    
    if args.status:
        scheduler.show_status()
        return
    
    if args.remove:
        print(f"移除{args.method}定时任务...")
        if args.method == 'cron':
            success = scheduler.remove_cron_job()
        else:
            success = scheduler.remove_systemd_timer()
    else:
        print(f"设置{args.method}定时任务 ({args.interval})...")
        if args.method == 'cron':
            success = scheduler.setup_cron_job()
        else:
            success = scheduler.setup_systemd_timer()
    
    if success:
        print("\n操作完成！")
        if not args.remove:
            print("\n建议:")
            print("1. 运行 'python cleanup_sessions.py --stats' 查看当前统计")
            print("2. 运行 'python cleanup_sessions.py --dry-run' 测试清理脚本")
            print("3. 定期检查日志确保清理任务正常运行")
    else:
        print("\n操作失败！")
        sys.exit(1)


if __name__ == '__main__':
    main()