"""
验证管理模块 - 负责路由验证和连通性测试
"""
import logging
from typing import List, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime
from utils.powershell import run_route_cmd, run_powershell

logger = logging.getLogger(__name__)


@dataclass
class VerifyResult:
    """验证结果"""
    target: str  # 目标地址
    hit: bool  # 是否命中路由
    interface: str  # 出接口
    gateway: str  # 下一跳
    trace_success: bool = False  # TraceRoute是否成功
    first_hop: str = ""  # 首跳IP
    latency_ms: int = 0  # 延迟(毫秒)
    error: str = ""  # 错误信息
    log: str = ""  # 详细日志


class VerifyManager:
    """验证管理器"""
    
    def __init__(self):
        pass
    
    def verify_route(self, target: str, do_trace: bool = False) -> VerifyResult:
        """
        验证单条路由
        
        Args:
            target: 目标IP
            do_trace: 是否执行TraceRoute
            
        Returns:
            VerifyResult: 验证结果
        """
        result = VerifyResult(target=target, hit=False, interface="", gateway="")
        
        try:
            # 第一步: route print 检查命中
            hit, interface, gateway, log = self._check_route_hit(target)
            
            result.hit = hit
            result.interface = interface
            result.gateway = gateway
            result.log = log
            
            if not hit:
                result.error = "未命中任何路由"
                return result
            
            # 第二步: TraceRoute(可选)
            if do_trace:
                trace_success, first_hop, latency, trace_log = self._trace_route(target)
                
                result.trace_success = trace_success
                result.first_hop = first_hop
                result.latency_ms = latency
                result.log += f"\n\n{trace_log}"
                
                if not trace_success:
                    result.error = "TraceRoute 失败"
            
            return result
            
        except Exception as e:
            logger.error(f"验证路由异常: {target}, {e}")
            result.error = str(e)
            return result
    
    def _check_route_hit(self, target: str) -> Tuple[bool, str, str, str]:
        """
        检查路由是否命中
        
        Args:
            target: 目标IP
            
        Returns:
            Tuple[bool, str, str, str]: (是否命中, 接口, 网关, 日志)
        """
        try:
            # 提取 IP 部分
            target_ip = target.split('/')[0] if '/' in target else target
            
            # 执行 route print
            success, stdout, stderr = run_route_cmd(f"print {target_ip}")
            
            if not success:
                return False, "", "", stderr
            
            # 解析输出,查找匹配的路由条目
            # 输出示例:
            # ===========================================================================
            # Active Routes:
            # Network Destination        Netmask          Gateway       Interface  Metric
            #       192.168.1.0    255.255.255.0     On-link      192.168.1.100    281
            # ===========================================================================
            
            lines = stdout.split('\n')
            
            # 查找包含目标IP的行
            for i, line in enumerate(lines):
                if target_ip in line and 'Network Destination' not in line:
                    # 尝试解析这一行
                    parts = line.split()
                    if len(parts) >= 4:
                        gateway = parts[2] if parts[2] != 'On-link' else parts[3]
                        interface = parts[3] if len(parts) > 3 else ""
                        
                        return True, interface, gateway, stdout
            
            return False, "", "", stdout
            
        except Exception as e:
            logger.error(f"检查路由命中异常: {e}")
            return False, "", "", str(e)
    
    def _trace_route(self, target: str, timeout_ms: int = 1500) -> Tuple[bool, str, int, str]:
        """
        执行 TraceRoute
        
        Args:
            target: 目标IP
            timeout_ms: 超时时间(毫秒)
            
        Returns:
            Tuple[bool, str, int, str]: (是否成功, 首跳IP, 延迟ms, 日志)
        """
        try:
            # 提取 IP 部分
            target_ip = target.split('/')[0] if '/' in target else target
            
            # 使用 Test-NetConnection 进行TraceRoute
            # 注意: 这个命令比较慢,可能需要几秒钟
            command = f"Test-NetConnection {target_ip} -TraceRoute -WarningAction SilentlyContinue"
            
            success, stdout, stderr = run_powershell(command, timeout=10)
            
            if not success:
                return False, "", 0, stderr
            
            # 解析输出
            # 输出示例:
            # ComputerName           : 8.8.8.8
            # RemoteAddress          : 8.8.8.8
            # InterfaceAlias         : Ethernet
            # SourceAddress          : 192.168.1.100
            # PingSucceeded          : True
            # PingReplyDetails (RTT) : 20 ms
            # TraceRoute             : 192.168.1.1
            #                          ...
            
            first_hop = ""
            latency = 0
            
            lines = stdout.split('\n')
            trace_started = False
            
            for line in lines:
                line = line.strip()
                
                # 查找延迟信息
                if 'PingReplyDetails' in line or 'RTT' in line:
                    # 提取数字
                    import re
                    match = re.search(r'(\d+)\s*ms', line)
                    if match:
                        latency = int(match.group(1))
                
                # 查找 TraceRoute 部分
                if 'TraceRoute' in line:
                    trace_started = True
                    # 可能在同一行就有第一跳
                    parts = line.split(':')
                    if len(parts) > 1 and parts[1].strip():
                        first_hop = parts[1].strip()
                    continue
                
                # 如果已经开始TraceRoute部分,获取第一跳
                if trace_started and not first_hop and line:
                    first_hop = line
                    break
            
            return True, first_hop, latency, stdout
            
        except Exception as e:
            logger.error(f"TraceRoute 异常: {e}")
            return False, "", 0, str(e)
    
    def verify_routes_batch(self, targets: List[str], do_trace: bool = False) -> List[VerifyResult]:
        """
        批量验证路由
        
        Args:
            targets: 目标IP列表
            do_trace: 是否执行TraceRoute
            
        Returns:
            List[VerifyResult]: 验证结果列表
        """
        results = []
        
        for target in targets:
            logger.info(f"验证路由: {target}")
            result = self.verify_route(target, do_trace)
            results.append(result)
        
        return results

