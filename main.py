from controller.AgentController import AgentController
from model.RoomGraph import RoomGraph
from model.AgentModel import AgentModel
from controller.SimulationController import SimulationController
from controller.AgentController import CrewmateController, ImposterController

def build_map():
    graph = RoomGraph()
    graph.connect_rooms("Electrical", "Storage")
    graph.connect_rooms("Storage", "MedBay")
    graph.connect_rooms("MedBay", "Cafeteria")
    graph.connect_rooms("Cafeteria", "Navigation")
    graph.connect_rooms("Storage", "Admin")
    return graph

def create_agents(room_graph):
    agent_specs = [
        ("agent1", "crewmate", "Electrical"),
        ("agent2", "crewmate", "Storage"),
        ("imposter", "imposter", "MedBay")
    ]
    
    agents = []
    for name, role, room in agent_specs:
        model = AgentModel(name, role, room)
        if role == "crewmate":
            controller = CrewmateController(model, room_graph)
        elif role == "imposter":
            controller = ImposterController(model, room_graph)
        agents.append(controller)
    return agents

if __name__ == "__main__":
    map_graph = build_map()
    agent_controllers = create_agents(map_graph)
    sim = SimulationController(agent_controllers)
    sim.run()