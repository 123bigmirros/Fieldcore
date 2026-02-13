# -*- coding: utf-8 -*-
"""
World Client - 世界服务 HTTP 客户端

封装对 world_server 微服务的调用
"""

import requests
from typing import Dict, List, Optional, Tuple


class WorldClient:
    """世界服务 HTTP 客户端"""

    def __init__(self, base_url: str = "http://localhost:8005"):
        self.base_url = base_url
        self.timeout = 5

    def _post(self, path: str, data: dict = None) -> dict:
        """POST 请求"""
        resp = requests.post(f"{self.base_url}{path}", json=data, timeout=self.timeout)
        return resp.json()

    def _get(self, path: str) -> dict:
        """GET 请求"""
        resp = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
        return resp.json()

    # ==================== 核心 API ====================

    def register_machine(
        self,
        machine_id: str,
        position: List[float],
        owner: str = "",
        life_value: int = 10,
        machine_type: str = "worker",
        size: float = 1.0,
        facing_direction: Tuple[float, float] = (1.0, 0.0),
        view_size: int = 3
    ) -> Tuple[bool, str]:
        """注册机器人"""
        result = self._post("/api/world/machine_register", {
            "machine_id": machine_id,
            "position": position,
            "owner": owner,
            "life_value": life_value,
            "machine_type": machine_type,
            "size": size,
            "facing_direction": list(facing_direction),
            "view_size": view_size
        })
        return result.get("success", False), result.get("error", "")

    def machine_action(self, machine_id: str, action: str, params: dict = None) -> dict:
        """执行机器人动作"""
        return self._post("/api/world/machine_action", {
            "machine_id": machine_id,
            "action": action,
            "params": params or {}
        })

    def save_world(self) -> bool:
        """保存世界状态"""
        result = self._post("/api/world/save_world")
        return result.get("success", False)

    def get_machine_view(self, machine_id: str) -> Optional[dict]:
        """获取机器人视野"""
        result = self._get(f"/api/world/machine_view/{machine_id}")
        if "error" in result:
            return None
        return result

    # ==================== 便捷方法（基于 machine_action）====================

    def move(self, machine_id: str, direction: List[float], distance: float) -> dict:
        """移动机器人"""
        return self.machine_action(machine_id, "move", {
            "direction": direction,
            "distance": distance
        })

    def attack(self, machine_id: str, damage: int = 1) -> dict:
        """攻击"""
        return self.machine_action(machine_id, "attack", {"damage": damage})

    def turn(self, machine_id: str, direction: List[float]) -> dict:
        """转向"""
        return self.machine_action(machine_id, "turn", {"direction": direction})

    def remove_machine(self, machine_id: str) -> bool:
        """移除机器人"""
        result = self.machine_action(machine_id, "remove", {})
        return result.get("success", False)

    # ==================== 调试方法 ====================

    def get_all_machines(self) -> dict:
        """获取所有机器人"""
        try:
            return self._get("/api/world/debug/machines")
        except requests.exceptions.Timeout:
            raise Exception(f"World Server 请求超时 (timeout={self.timeout}s)")
        except requests.exceptions.RequestException as e:
            raise Exception(f"World Server 请求失败: {e}")

    def get_all_obstacles(self) -> dict:
        """获取所有障碍物"""
        return self._get("/api/world/debug/obstacles")

    def reset_world(self) -> dict:
        """重置世界"""
        return self._post("/api/world/debug/reset")

    def check_collision(self, position: List[float], size: float = 1.0, exclude_id: str = None) -> dict:
        """碰撞检测（通过尝试注册临时机器人实现）"""
        # 简化：直接获取所有数据自行计算
        machines = self.get_all_machines()
        obstacles = self.get_all_obstacles()

        # 简单碰撞检测
        for m_id, m in machines.items():
            if m_id == exclude_id:
                continue
            m_pos = m['position']
            dist = sum((a - b) ** 2 for a, b in zip(position, m_pos)) ** 0.5
            if dist < max(size, m.get('size', 1.0)) * 0.5:
                return {'collision': True}

        for obs in obstacles.values():
            obs_pos = obs['position']
            dist = sum((a - b) ** 2 for a, b in zip(position, obs_pos)) ** 0.5
            if dist < max(size, obs.get('size', 1.0)) * 0.5:
                return {'collision': True}

        return {'collision': False}

    def health_check(self) -> bool:
        """健康检查"""
        try:
            result = self._get("/health")
            return result.get("status") == "ok"
        except Exception:
            return False

    def get_machine(self, machine_id: str) -> Optional[dict]:
        """获取单个机器人"""
        machines = self.get_all_machines()
        return machines.get(machine_id)


# 全局客户端实例
world_client = WorldClient()
