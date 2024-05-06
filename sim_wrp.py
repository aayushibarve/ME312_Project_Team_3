import heapq
import networkx as nx
import math
from create_graph import recreate_graph_from_file
import ast

class AmbulanceDispatch:
    def __init__(self, graph, ambulance_data):
        self.graph = graph
        self.available_ambulances = ambulance_data
        self.unavailable_ambulances = {}
        self.priority_queue = []
        self.current_time = 0  # Track the current time for dispatches
        self.was_queue_processed = False  # Track whether the queue was processed
        self.hospital_to_station = read_ambulance_station_assignments('hospital_to_station_mapping.txt')

    def find_nearby_ambulances(self, patient_node, radius=float('inf')):
        nearby_ambulances = {}
        min_distance = float('inf')
        nearest_ambulance_id = None

        for ambulance_id, ambulance_data in self.available_ambulances.items():
            ambulance_node=ambulance_data[2]
            try:
                path_length = nx.dijkstra_path_length(self.graph, source=ambulance_node, target=patient_node, weight='weight')  # Assuming weights represent distance/time
                if path_length <= radius:
                    nearby_ambulances[ambulance_id] = (ambulance_node, path_length)
                if path_length < min_distance:
                    min_distance = path_length
                    nearest_ambulance_id = ambulance_id
            except nx.NetworkXNoPath:
                pass
                #print(f"No path from ambulance {ambulance_id} at node {ambulance_node} to patient at node {patient_node}")

        if not nearby_ambulances and nearest_ambulance_id:
            nearest_ambulance_node, nearest_distance = self.available_ambulances[nearest_ambulance_id], min_distance
            nearby_ambulances[nearest_ambulance_id] = (nearest_ambulance_node, nearest_distance)

        return nearby_ambulances


    def dispatch_ambulance(self, patient_call, hospital_node, patient_type, patient_id):
        print('Printing patient call',patient_call,' id ',patient_id)
        patient_node=patient_call[0]
        print(patient_node)
        call_time=patient_call[2]
        #print(f"{self.current_time}: Attempting dispatch for patient {patient_id} at {patient_node}")
        self.update_available_ambulances()

        if not self.available_ambulances:
            print(f"{self.current_time}: No ambulances available, enqueued patient at {patient_node} with priority {self.determine_priority(patient_node, self.current_time)}")
            heapq.heappush(self.priority_queue, (self.determine_priority(patient_node, self.current_time), patient_call, hospital_node, patient_type, self.current_time,patient_id))
            return


        nearby_ambulances = self.find_nearby_ambulances(patient_node)
        if not nearby_ambulances:
            print(f"No nearby ambulances found; adding to queue")
            heapq.heappush(self.priority_queue, (self.determine_priority(patient_node, self.current_time), patient_call, hospital_node, patient_type, self.current_time,patient_id))
            return

        best_ambulance_id, best_cost = self.select_best_ambulance(nearby_ambulances, patient_node, hospital_node)
        if best_ambulance_id is None:
            print(f"Unable to find a suitable ambulance for dispatch; adding to queue")
            heapq.heappush(self.priority_queue, (self.determine_priority(patient_node, self.current_time), patient_call, hospital_node, patient_type, self.current_time,patient_id))
            return
        nearest_station_data = self.hospital_to_station[hospital_node]
        return_time = nearest_station_data['travel_time']
        self.mark_ambulance_unavailable(best_ambulance_id, hospital_node, best_cost, patient_call, patient_id)
        print(f"Ambulance {best_ambulance_id} dispatched to {patient_node} for patient {patient_id}, will be free at {self.current_time + best_cost}")

    def update_available_ambulances(self):
        newly_available = []
        for ambulance_id, info in list(self.unavailable_ambulances.items()):
            if info['availability_time'] <= self.current_time:
                newly_available.append(ambulance_id)
                free=self.unavailable_ambulances[ambulance_id]
                patient_id=free['patient_id']
                response_time=free['availability_time']
                call_time=free['call_time']
                assignment_time=free['assignment_time']
                f = open("results_wrp.txt", "a")
                f.write(f"Patient {patient_id} called at time {call_time}, received an assignment at {assignment_time}, reached a hospital at {response_time}\n")
                f.close()
                hospital_location = info['hospital_location']  # Changed from 'hospital_location' to 'station_location'
                self.available_ambulances[ambulance_id] = (hospital_location, hospital_location, hospital_location, info['path_to_station'],self.current_time)
                del self.unavailable_ambulances[ambulance_id]

        if newly_available:
            print(self.current_time,f":Ambulances {newly_available} now available and stationed accordingly")


    def process_queued_requests(self):
        if not self.available_ambulances or not self.priority_queue:
            #print(f"{self.current_time}: No processing required: No available ambulances or empty queue.")
            return

        print(f"{self.current_time}: Processing queue. Queue Length: {len(self.priority_queue)}")
        while self.priority_queue and self.available_ambulances:
            priority, patient_call, hospital_node, patient_type, _,patient_id = heapq.heappop(self.priority_queue)
            print(patient_call, " in process queued requests")
            self.dispatch_ambulance(patient_call, hospital_node, patient_type,patient_id)

        print(f"{self.current_time}: Remaining queue length: {len(self.priority_queue)}")

    def determine_priority(self, patient_node, time):
        return time  # Negative time to prioritize earlier requests

    def select_best_ambulance(self, nearby_ambulances, patient_node, hospital_node):
        # Assume shortest path to patient plus path from patient to hospital determines best ambulance
        min_total_cost = float('inf')
        best_ambulance_id = None
        for ambulance_id, (ambulance_node, cost_to_patient) in nearby_ambulances.items():
            try:
                cost_to_hospital = nx.dijkstra_path_length(self.graph, source=patient_node, target=hospital_node, weight='weight')
                total_cost = cost_to_patient + cost_to_hospital
                if total_cost < min_total_cost:
                    min_total_cost = total_cost
                    best_ambulance_id = ambulance_id
            except nx.NetworkXNoPath:
                pass
                #print(f"No path from patient at node {patient_node} to hospital at node {hospital_node}")

        return best_ambulance_id, min_total_cost if best_ambulance_id else None

    def mark_ambulance_unavailable(self, ambulance_id, hospital_node, best_cost, patient_call, patient_id):
        # After delivering a patient, the ambulance goes to the nearest station
        nearest_station_data = self.hospital_to_station[hospital_node]
        path_to_station = nearest_station_data['travel_path']
        nearest_station = nearest_station_data['station']
        #return_time = nearest_station_data['travel_time']
        self.unavailable_ambulances[ambulance_id] = {
            'hospital_location': hospital_node,
            'station_location': nearest_station,
            'path_to_station': path_to_station,
            'availability_time': self.current_time + best_cost,
            'assignment_time':self.current_time,
            'patient_id':patient_id,
            'call_time':patient_call[2]
        }
        del self.available_ambulances[ambulance_id]

    
    
    def run_simulation(self, patient_calls):
        # Determine the last call time to know when to stop processing new calls.
        last_call_time = max(call[2] for id,call in patient_calls.items())+1000

        # Main simulation loop
        while self.current_time <= last_call_time : #or not self.is_queue_empty()
            #print('running',self.current_time)
            # Process new or pending calls at the current time
            self.process_calls_and_queue(patient_calls)
            # Update the status of ambulances (e.g., make available ones that have completed their tasks)
            self.update_available_ambulances()
            # Try to dispatch any remaining queued requests
            self.process_queued_requests()
            # Increment the simulation time only if more calls are expected or the queue is not empty
            if self.current_time < last_call_time : #or not self.is_queue_empty()
                self.current_time += 1
            else:
                break  # Break the loop if no more
    def is_queue_empty(self):
        # Check if there are no more requests in the priority queue
        return len(self.priority_queue) == 0
    def process_calls_and_queue(self, patient_calls):
        # Process all calls that are scheduled for the current time
        for patient_id, call in patient_calls.items():
            if call[2] == self.current_time:  # time is the third element in the tuple
                patient_node, hospital_node, _ = call
                hospital_node = assignments.get(patient_node, "Unknown")  # Get hospital node from assignments
                self.dispatch_ambulance(call, hospital_node, _, patient_id)

       
def read_hospital_assignments(assignment_file_path):
    assignments = {}
    with open(assignment_file_path, 'r') as f:
        next(f)  # Skip the header line
        for line in f:
            emergency, hospital = line.strip().split(' assigned to ')
            assignments[emergency] = hospital
    return assignments

def read_ambulance_station_assignments(file_path):
    assignments = {}
    with open(file_path, 'r') as f:
        next(f)  # Skip the header line
        for line in f:
            hospital, data = line.strip().split(' assigned to ')
            station, travel_details = data.split(', Travel Time: ')
            travel_time, travel_path = travel_details.split(', path: ')
            travel_path=ast.literal_eval(travel_path)
            assignments[hospital] = {'station': station, 'travel_time': float(travel_time), 'travel_path':travel_path}
    return assignments


if __name__ == "__main__":
    f = open("results_wrp.txt", "w")
    f.write(f"Without returning protocol\n")
    f.close()
    graph = recreate_graph_from_file('graph_structure.txt')
    assignment_file_path = 'hospital_assignments.txt'
    assignments = read_hospital_assignments(assignment_file_path)
    ambulance_data = {
    1: ('A210', None, 'A210', None, None),
    2: ('A211', None, 'A211', None, None),
    3: ('A212', None, 'A212', None, None),
    4: ('A213', None, 'A213', None, None),
    5: ('A214', None, 'A214', None, None),
    
}
    #ambulance id, hospital the ambulance went to, surrent loaction between ambulance and station, path from hospital to station
    dispatcher = AmbulanceDispatch(graph, ambulance_data)
    patient_calls = {
    1: ('E28', 1, 5),       # Close to A210
    2: ('E8', 1, 30),       # Close to A211
    3: ('E31', 1, 60),      # Close to A212
    4: ('E37', 1, 100),     # Close to A213
    5: ('E4', 1, 150),      # Close to A214
    6: ('E7', 1, 210),      # Close to A215
    7: ('E6', 2, 280),      # Close to A216
    8: ('E107', 2, 360),    # Close to A210
    9: ('E108', 3, 450),    # Close to A211
    10: ('E10', 4, 550),    # Close to A212
    11: ('E115', 5, 660),   # Close to A213
    12: ('E119', 6, 780),   # Close to A214
    13: ('E123', 7, 910),   # Close to A215
    14: ('E126', 8, 1050),  # Close to A216
    15: ('E129', 9, 1200),  # Close to A210
    16: ('E132', 10, 1360), # Close to A211
    17: ('E135', 1, 1530),  # Close to A212
    18: ('E138', 2, 1710),  # Close to A213
    19: ('E142', 3, 1900),  # Close to A214
    20: ('E145', 4, 2100),  # Close to A215
    21: ('E147', 1, 2310),  # Close to A216
    22: ('E149', 2, 2530),  # Close to A210
    23: ('E151', 3, 2760),  # Close to A211
    24: ('E153', 4, 3000),  # Close to A212
    25: ('E155', 5, 3250),  # Close to A213
    26: ('E157', 6, 3510),  # Close to A214
    27: ('E159', 7, 3780),  # Close to A215
    28: ('E161', 8, 4060),  # Close to A216
    29: ('E163', 9, 4350),  # Close to A210
    30: ('E165', 10, 4650)  # Close to A211
}



    dispatcher.run_simulation(patient_calls)
