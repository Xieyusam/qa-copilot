with open('app/services/agents/stategraph/graph.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    # 如果有待执行的多个 agent，并行执行
    if len(pending_agents) > 1:
        logger.info(f"route_from_supervisor: 并行执行 {pending_agents}")
        return [Send(agent, {"pending_agents": [agent]}) for agent in pending_agents]'''

new = '''    # 如果有待执行的多个 agent，并行执行
    if len(pending_agents) > 1:
        logger.info(f"route_from_supervisor: 并行执行 {pending_agents}")
        # 使用 lambda 包装，避免立即求值
        def make_send(agent):
            return Send(agent, state)
        return [make_send(agent) for agent in pending_agents]'''

if old in content:
    content = content.replace(old, new)
    print('Fixed route_from_supervisor')
else:
    print('Pattern not found')

with open('app/services/agents/stategraph/graph.py', 'w', encoding='utf-8') as f:
    f.write(content)