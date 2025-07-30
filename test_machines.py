#!/usr/bin/env python3
"""
测试机器数据创建和API响应
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agent.world_manager import world_manager, Position

def test_machines():
    """测试机器数据"""
    print("🧪 测试机器数据...")

    # 清理现有机器
    all_machines = world_manager.get_all_machines()
    for machine_id in all_machines.keys():
        world_manager.remove_machine(machine_id)

    # 创建测试机器
    test_machines = [
        ("robot_01", [0, 0, 0], 10, "worker"),
        ("robot_02", [2, 0, 0], 8, "scout"),
        ("robot_03", [4, 0, 0], 12, "defender"),
        ("robot_04", [0, 2, 0], 9, "worker"),
        ("robot_05", [2, 2, 0], 11, "scout"),
    ]

    for machine_id, position, life, machine_type in test_machines:
        world_manager.register_machine(
            machine_id=machine_id,
            position=Position(*position),
            life_value=life,
            machine_type=machine_type
        )
        print(f"✅ 创建机器: {machine_id} 在位置 {position}")

    # 验证机器创建
    all_machines = world_manager.get_all_machines()
    print(f"\n📊 当前机器数量: {len(all_machines)}")

    for machine_id, machine_info in all_machines.items():
        print(f"🤖 {machine_id}: 位置{machine_info.position}, 生命值{machine_info.life_value}")

    print("\n🎉 机器数据测试完成!")
    print("💡 现在可以:")
    print("   1. 访问 http://localhost:3000 查看前端")
    print("   2. 运行 python examples/test_human_machine_lineup_simple.py 测试连续命令")

if __name__ == "__main__":
    test_machines()
