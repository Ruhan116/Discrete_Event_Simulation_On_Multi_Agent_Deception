class AgentModel:
    def __init__(self, name, role, current_room):
        self.name = name
        self.role = role  # 'crewmate' or 'imposter'
        self.current_room = current_room
        self.alive = True
