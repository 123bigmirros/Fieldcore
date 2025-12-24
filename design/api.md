# agent_controller
    - agentCreate: 创建human或machine，machine必须对应一个具体的human
    - getAgentInfo: 获取Agent和MachineInfo
    - updateAgentInfo: 更新AgentInfo  
    - sendCmd: 向human或machine发送prompt指令，或直接执行具体命令 

# mcp_controller
    - list_tools: 获取工具信息 
    - call_tool


# world_controller
    - machine_register: 注册machine在地图中的位置,并返回唯一编码
    - machine_action: 处理machine的移动、攻击等操作
    - save_world: 对world进行持久化操作，保证可以重启
    
