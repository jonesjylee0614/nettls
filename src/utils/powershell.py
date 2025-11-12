"""
PowerShell 命令执行封装
"""
import subprocess
import json
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def run_powershell(command: str, timeout: int = 30) -> Tuple[bool, str, str]:
    """
    执行 PowerShell 命令
    
    Args:
        command: PowerShell 命令
        timeout: 超时时间（秒）
        
    Returns:
        Tuple[bool, str, str]: (是否成功, 标准输出, 标准错误)
    """
    try:
        # 使用 PowerShell 执行命令
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore'
        )
        
        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        if not success:
            logger.error(f"PowerShell 命令失败: {command}")
            logger.error(f"错误输出: {stderr}")
        
        return success, stdout, stderr
        
    except subprocess.TimeoutExpired:
        logger.error(f"PowerShell 命令超时: {command}")
        return False, "", "命令执行超时"
    except Exception as e:
        logger.error(f"执行 PowerShell 命令异常: {e}")
        return False, "", str(e)


def run_powershell_json(command: str, timeout: int = 30) -> Tuple[bool, Optional[dict], str]:
    """
    执行 PowerShell 命令并解析 JSON 输出
    
    Args:
        command: PowerShell 命令（应包含 ConvertTo-Json）
        timeout: 超时时间（秒）
        
    Returns:
        Tuple[bool, Optional[dict], str]: (是否成功, 解析后的数据, 错误信息)
    """
    success, stdout, stderr = run_powershell(command, timeout)
    
    if not success:
        return False, None, stderr
    
    try:
        # 解析 JSON
        data = json.loads(stdout) if stdout else None
        return True, data, ""
    except json.JSONDecodeError as e:
        logger.error(f"解析 JSON 失败: {e}")
        logger.error(f"输出内容: {stdout}")
        return False, None, f"JSON 解析失败: {e}"


def run_route_cmd(args: str, timeout: int = 10) -> Tuple[bool, str, str]:
    """
    执行 route 命令
    
    Args:
        args: route 命令参数
        timeout: 超时时间（秒）
        
    Returns:
        Tuple[bool, str, str]: (是否成功, 标准输出, 标准错误)
    """
    try:
        cmd = f"route {args}"
        result = subprocess.run(
            ["cmd", "/c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='gbk',  # Windows cmd 使用 GBK 编码
            errors='ignore'
        )
        
        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        if not success:
            logger.error(f"route 命令失败: {cmd}")
            logger.error(f"错误输出: {stderr}")
        
        return success, stdout, stderr
        
    except subprocess.TimeoutExpired:
        logger.error(f"route 命令超时: {args}")
        return False, "", "命令执行超时"
    except Exception as e:
        logger.error(f"执行 route 命令异常: {e}")
        return False, "", str(e)

