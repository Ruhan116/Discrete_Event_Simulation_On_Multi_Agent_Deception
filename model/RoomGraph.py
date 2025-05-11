class RoomGraph:
    def __init__(self):
        self.adjacency = {}
    
    def add_room(self, room_name):
        if room_name not in self.adjacency:
            self.adjacency[room_name] = []
        
    def connect_rooms(self, room1, room2):
        self.add_room(room1)
        self.add_room(room2)
        self.adjacency[room1].append(room2)
        self.adjacency[room2].append(room1)
    
    def get_neighbors(self, room_name):
        return self.adjacency.get(room_name, [])
    
    def is_connected(self, room1, room2):
        return room2 in self.adjacency.get(room1, [])
    
    def __str__(self):
        return "\n".join(f"{room}: {sorted(neighbors)}" for room, neighbors in self.adjacency.items())
 

