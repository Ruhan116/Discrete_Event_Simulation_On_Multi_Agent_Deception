from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import UserSettableParameter
from model import AmongUsModel
from agents import Imposter
from voting import VotingDisplay

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
voting_display = VotingDisplay()

model_params = {
    "num_agents": UserSettableParameter('number', 'Number of Crewmates', 8),
    "num_imposters": UserSettableParameter('number', 'Number of Imposters', 1),
    "width": 20,
    "height": 20
}

server = ModularServer(
    AmongUsModel, 
    [grid, voting_display],
    "Among Us Simulation", 
    model_params
)

server.launch()