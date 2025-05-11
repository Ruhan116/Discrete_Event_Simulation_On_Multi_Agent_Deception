class RoomView:
    def __init__(self, log_file="room_occupancy.log"):  
        self.log_file = log_file
        self._setup_log_file()

    def _setup_log_file(self):
        with open(self.log_file, "w") as f:
            f.write(f"--- Room Occupancy Log ---\n")

    def print_rooms(self, agent_controllers, timestamp): 
        room_map = {}
        for ctrl in agent_controllers:
            room = ctrl.model.current_room
            name = ctrl.model.name
            alive = ctrl.model.alive
            if room not in room_map:
                room_map[room] = []
            if alive:
                room_map[room].append(name)
        print(f"\n--- Agents in Rooms at time {timestamp:.2f} ---") 
        with open(self.log_file, "a") as f:
            f.write(f"\n--- Agents in Rooms at time {timestamp:.2f} ---\n")
        for room, agents in room_map.items():
            print(f"{room}: {', '.join(agents) if agents else 'None'}")
            with open(self.log_file, "a") as f:
                f.write(f"{room}: {', '.join(agents) if agents else 'None'}\n")
        print("----------------------\n")
        with open(self.log_file, "a") as f:
                f.write("----------------------\n")