from simulation.Event import Event, EventType
from simulation.Scheduler import Scheduler
from view.SimulationView import SimulationView
from view.RoomView import RoomView 

class SimulationController:
    def __init__(self, agent_controllers):
        self.scheduler = Scheduler()
        self.agent_controllers = agent_controllers
        self.view = SimulationView()
        self.room_view = RoomView()

    
    def run(self):
        for controller in self.agent_controllers:
            event = controller.decide_next_action(self.scheduler.clock, self.agent_controllers)
            if event:
                self.scheduler.add_event(event)
        
        while True:
            event = self.scheduler.process_next_event()
            if not event:
                break
            self.handle_event(event)

    def handle_event(self, event):
        self.view.log_event(self.scheduler.clock, event.agent.name, event.event_type)
        self.room_view.print_rooms(self.agent_controllers, self.scheduler.clock)

        if event.event_type == EventType.MOVE:
            event.agent.current_room = event.data['destination']
        
        elif event.event_type == EventType.KILL:
            target_name = event.data['target']
            for ctrl in self.agent_controllers:
                if ctrl.model.name == target_name:
                    ctrl.model.alive = False
                    # Log the kill
                    self.view.log_kill(event.agent.name, ctrl.model.name)
                    break


        alive_crewmates = [
            ctrl for ctrl in self.agent_controllers 
            if ctrl.model.role == 'crewmate' and ctrl.model.alive
        ]
        alive_imposters = [
            ctrl for ctrl in self.agent_controllers 
            if ctrl.model.role == 'imposter' and ctrl.model.alive
        ]

        if not alive_crewmates:
            self.view.log_end("All crewmates are dead. Imposters win!")
            exit()  # or return to stop gracefully

        if not alive_imposters:
            self.view.log_end("All imposters are dead. Crewmates win!")
            exit()

        for ctrl in self.agent_controllers:
            if ctrl.model == event.agent:
                new_event = ctrl.decide_next_action(self.scheduler.clock, self.agent_controllers)
                if new_event:
                    self.scheduler.add_event(new_event)

