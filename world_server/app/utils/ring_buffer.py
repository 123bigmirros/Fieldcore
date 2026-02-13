# -*- coding: utf-8 -*-
"""
Ring Buffer - 循环队列实现

使用固定数组和两个游标实现循环队列
每个buffer只有一个写线程，无需加锁
"""

from typing import Optional, Any


class RingBuffer:
    """循环队列（无锁，单写线程安全）"""

    def __init__(self, capacity: int):
        """初始化循环队列"""
        if capacity <= 0:
            raise ValueError("Capacity must be positive")

        self.capacity = capacity
        self.buffer = [None] * capacity
        self.read_idx = 0  # 读游标
        self.write_idx = 0  # 写游标
        self.size = 0  # 当前元素数量

    def is_full(self) -> bool:
        """检查队列是否已满"""
        return self.size >= self.capacity

    def is_empty(self) -> bool:
        """检查队列是否为空"""
        return self.size == 0

    def put(self, item: Any) -> bool:
        """添加元素到队列（仅由写线程调用）"""
        if self.is_full():
            return False

        self.buffer[self.write_idx] = item
        self.write_idx = (self.write_idx + 1) % self.capacity
        self.size += 1
        return True

    def get(self) -> Optional[Any]:
        """从队列取出元素（仅由读线程调用）"""
        if self.is_empty():
            return None

        item = self.buffer[self.read_idx]
        self.buffer[self.read_idx] = None
        self.read_idx = (self.read_idx + 1) % self.capacity
        self.size -= 1
        return item

    def clear(self):
        """清空队列"""
        self.buffer = [None] * self.capacity
        self.read_idx = 0
        self.write_idx = 0
        self.size = 0

