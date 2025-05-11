from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
from model import AmongUsModel
from agents import Imposter

def agent_portrayal(agent):
    portrayal = {
        "Shape": "circle",
        "Filled": "true",
        "Layer": 0,
        "Color": "red" if isinstance(agent, Imposter) else "blue",
        "r": 0.5 if agent.alive else 0.2
    }
    return portrayal

grid = CanvasGrid(agent_portrayal, 20, 20, 500, 500)
server = ModularServer(AmongUsModel, [grid], "Among Us Simulation", {"num_agents": 8, "num_imposters": 1})
server.launch()