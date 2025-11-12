"""
Apply 管理模块 - 负责生成 Diff 和执行路由应用
"""
import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from core.route_manager import Route, RouteManager
from core.interface_manager import InterfaceManager

logger = logging.getLogger(__name__)


@dataclass
class DiffItem:
    """Diff 条目"""
    action: str  # add / change / delete / skip
    route: Route  # 路由对象
    old_route: dict = None  # 旧路由信息(仅 change/delete 有效)
    reason: str = ""  # 说明


class ApplyManager:
    """Apply 管理器"""
    
    def __init__(self, route_manager: RouteManager, interface_manager: InterfaceManager):
        self.route_manager = route_manager
        self.interface_manager = interface_manager
        
        # 执行历史
        self.execution_history: List[dict] = []
    
    def generate_diff(self, config_routes: List[Route]) -> Tuple[List[DiffItem], str]:
        """
        生成 Diff 清单
        
        Args:
            config_routes: 配置中的路由列表
            
        Returns:
            Tuple[List[DiffItem], str]: (Diff列表, 错误信息)
        """
        try:
            diff_items = []
            
            # 刷新系统路由
            if not self.route_manager.refresh_system_routes():
                return [], "刷新系统路由失败"
            
            system_routes = self.route_manager.get_system_routes()
            
            # 构建系统路由映射表 {目标前缀: 路由信息}
            system_routes_map = {}
            for sys_route in system_routes:
                dest_prefix = sys_route.get('DestinationPrefix', '')
                if dest_prefix:
                    system_routes_map[dest_prefix] = sys_route
            
            # 遍历配置路由
            for route in config_routes:
                # 跳过未启用的路由
                if not route.enabled:
                    diff_items.append(DiffItem(
                        action="skip",
                        route=route,
                        reason="路由未启用"
                    ))
                    continue
                
                # 解析接口
                interface = self.interface_manager.get_interface_by_name(route.interface_name)
                if not interface:
                    diff_items.append(DiffItem(
                        action="skip",
                        route=route,
                        reason=f"接口不存在: {route.interface_name}"
                    ))
                    continue
                
                # 更新路由的 ifIndex
                route.if_index = interface.if_index
                
                # 获取目标前缀
                dest_prefix = route.get_destination_prefix()
                
                # 检查系统中是否存在
                if dest_prefix in system_routes_map:
                    sys_route = system_routes_map[dest_prefix]
                    
                    # 比较路由参数
                    sys_gateway = sys_route.get('NextHop', '')
                    sys_metric = sys_route.get('RouteMetric', 0)
                    sys_if_index = sys_route.get('ifIndex', 0)
                    
                    # 判断是否需要修改
                    if (sys_gateway != route.gateway or 
                        sys_metric != route.metric or 
                        sys_if_index != route.if_index):
                        diff_items.append(DiffItem(
                            action="change",
                            route=route,
                            old_route=sys_route,
                            reason=f"修改参数: 网关/Metric/接口"
                        ))
                    else:
                        diff_items.append(DiffItem(
                            action="skip",
                            route=route,
                            reason="路由已存在且参数一致"
                        ))
                else:
                    # 需要新增
                    diff_items.append(DiffItem(
                        action="add",
                        route=route,
                        reason="新增路由"
                    ))
            
            # 检查需要删除的路由(系统中有但配置中没有的永久路由)
            config_targets = set([r.get_destination_prefix() for r in config_routes if r.enabled])
            for dest_prefix, sys_route in system_routes_map.items():
                # 只处理永久路由(Protocol 为 NetMgmt)
                protocol = sys_route.get('Protocol', '')
                if protocol != 'NetMgmt':
                    continue
                
                if dest_prefix not in config_targets:
                    # 这是一个需要删除的路由
                    # 创建临时路由对象用于显示
                    temp_route = Route(
                        enabled=False,
                        target=dest_prefix.split('/')[0] if '/' in dest_prefix else dest_prefix,
                        prefix_length=int(dest_prefix.split('/')[1]) if '/' in dest_prefix else 32,
                        gateway=sys_route.get('NextHop', ''),
                        interface_name="",
                        metric=sys_route.get('RouteMetric', 0),
                        desc="系统中的永久路由(未在配置中)"
                    )
                    
                    diff_items.append(DiffItem(
                        action="delete",
                        route=temp_route,
                        old_route=sys_route,
                        reason="配置中未包含此永久路由"
                    ))
            
            logger.info(f"生成 Diff 完成: 共 {len(diff_items)} 项")
            return diff_items, ""
            
        except Exception as e:
            logger.error(f"生成 Diff 异常: {e}")
            return [], str(e)
    
    def execute_diff(self, diff_items: List[DiffItem]) -> Tuple[bool, List[dict]]:
        """
        执行 Diff 计划
        
        Args:
            diff_items: Diff 列表
            
        Returns:
            Tuple[bool, List[dict]]: (是否全部成功, 执行结果列表)
        """
        results = []
        all_success = True
        
        # 记录执行前的状态(用于回滚)
        rollback_actions = []
        
        try:
            # 第一步: 删除冲突路由
            for item in diff_items:
                if item.action == "delete":
                    success, error = self.route_manager.delete_route(item.route.target)
                    
                    result = {
                        "action": "delete",
                        "target": item.route.get_destination_prefix(),
                        "success": success,
                        "error": error,
                        "time": datetime.now().isoformat()
                    }
                    results.append(result)
                    
                    if not success:
                        all_success = False
                        logger.error(f"删除路由失败: {item.route.target}, {error}")
                        break
                    else:
                        # 记录回滚操作(重新添加)
                        rollback_actions.append(("add", item.route, item.old_route))
            
            # 如果删除阶段失败,直接返回
            if not all_success:
                return False, results
            
            # 第二步: 修改现有路由
            for item in diff_items:
                if item.action == "change":
                    success, error = self.route_manager.change_route(item.route, item.route.if_index)
                    
                    result = {
                        "action": "change",
                        "target": item.route.get_destination_prefix(),
                        "success": success,
                        "error": error,
                        "time": datetime.now().isoformat()
                    }
                    results.append(result)
                    
                    if not success:
                        all_success = False
                        logger.error(f"修改路由失败: {item.route.target}, {error}")
                        # 开始回滚
                        self._rollback(rollback_actions)
                        return False, results
                    else:
                        # 记录回滚操作
                        rollback_actions.append(("change", item.route, item.old_route))
            
            # 第三步: 添加新路由
            for item in diff_items:
                if item.action == "add":
                    success, error = self.route_manager.add_route(item.route, item.route.if_index)
                    
                    result = {
                        "action": "add",
                        "target": item.route.get_destination_prefix(),
                        "success": success,
                        "error": error,
                        "time": datetime.now().isoformat()
                    }
                    results.append(result)
                    
                    if not success:
                        all_success = False
                        logger.error(f"添加路由失败: {item.route.target}, {error}")
                        # 开始回滚
                        self._rollback(rollback_actions)
                        return False, results
                    else:
                        # 记录回滚操作
                        rollback_actions.append(("delete", item.route, None))
            
            # 记录执行历史
            self.execution_history.append({
                "time": datetime.now().isoformat(),
                "total": len(diff_items),
                "success": all_success,
                "results": results,
                "rollback_actions": rollback_actions
            })
            
            return all_success, results
            
        except Exception as e:
            logger.error(f"执行 Diff 异常: {e}")
            # 尝试回滚
            self._rollback(rollback_actions)
            return False, results
    
    def _rollback(self, rollback_actions: List[Tuple]):
        """
        回滚操作
        
        Args:
            rollback_actions: 回滚操作列表
        """
        logger.warning("开始回滚...")
        
        # 按 LIFO 顺序执行回滚
        for action_type, route, old_route in reversed(rollback_actions):
            try:
                if action_type == "delete":
                    # 之前是 add,现在需要 delete
                    success, error = self.route_manager.delete_route(route.target)
                    if success:
                        logger.info(f"回滚: 删除路由 {route.target}")
                    else:
                        logger.error(f"回滚失败: 删除路由 {route.target}, {error}")
                
                elif action_type == "add":
                    # 之前是 delete,现在需要 add
                    if old_route:
                        # 使用旧路由信息重新添加
                        temp_route = Route(
                            enabled=True,
                            target=route.target,
                            prefix_length=route.prefix_length,
                            gateway=old_route.get('NextHop', route.gateway),
                            interface_name=route.interface_name,
                            metric=old_route.get('RouteMetric', route.metric),
                            persistent=True
                        )
                        success, error = self.route_manager.add_route(temp_route, route.if_index)
                        if success:
                            logger.info(f"回滚: 添加路由 {route.target}")
                        else:
                            logger.error(f"回滚失败: 添加路由 {route.target}, {error}")
                
                elif action_type == "change":
                    # 之前是 change,需要恢复到旧值
                    if old_route:
                        temp_route = Route(
                            enabled=True,
                            target=route.target,
                            prefix_length=route.prefix_length,
                            gateway=old_route.get('NextHop', route.gateway),
                            interface_name=route.interface_name,
                            metric=old_route.get('RouteMetric', route.metric),
                            persistent=True
                        )
                        success, error = self.route_manager.change_route(temp_route, route.if_index)
                        if success:
                            logger.info(f"回滚: 恢复路由 {route.target}")
                        else:
                            logger.error(f"回滚失败: 恢复路由 {route.target}, {error}")
            
            except Exception as e:
                logger.error(f"回滚操作异常: {e}")
        
        logger.warning("回滚完成")
    
    def get_execution_history(self) -> List[dict]:
        """获取执行历史"""
        return self.execution_history.copy()

