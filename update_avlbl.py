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
        path=None
        min_path=None
        nearest_ambulance_id = None

        for ambulance_id, ambulance_data in self.available_ambulances.items():
            ambulance_node=ambulance_data[2]
            try:
                path_length = nx.dijkstra_path_length(self.graph, source=ambulance_node, target=patient_node, weight='weight')  # Assuming weights represent distance/time
                path = nx.dijkstra_path(self.graph, source=ambulance_node, target=patient_node, weight='weight')
                if path_length <= radius:
                    nearby_ambulances[ambulance_id] = (ambulance_node, path_length,path)
                if path_length < min_distance:
                    min_distance = path_length
                    nearest_ambulance_id = ambulance_id
                    min_path=path
            except nx.NetworkXNoPath:
                pass
                #print(f"No path from ambulance {ambulance_id} at node {ambulance_node} to patient at node {patient_node}")

        if not nearby_ambulances and nearest_ambulance_id:
            nearest_ambulance_node, nearest_distance = self.available_ambulances[nearest_ambulance_id], min_distance
            nearby_ambulances[nearest_ambulance_id] = (nearest_ambulance_node, nearest_distance, min_path)

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

        best_ambulance_id, best_cost, best_path = self.select_best_ambulance(nearby_ambulances, patient_node, hospital_node)
        if best_ambulance_id is None:
            print(f"Unable to find a suitable ambulance for dispatch; adding to queue")
            heapq.heappush(self.priority_queue, (self.determine_priority(patient_node, self.current_time), patient_call, hospital_node, patient_type, self.current_time,patient_id))
            return
        nearest_station_data = self.hospital_to_station[hospital_node]
        return_time = nearest_station_data['travel_time']
        current_loc1=self.available_ambulances[best_ambulance_id]
        current_loc=current_loc1[2]
        self.mark_ambulance_unavailable(current_loc,best_ambulance_id, hospital_node, best_cost, patient_call, patient_id, best_path)
        print(f"Ambulance {best_ambulance_id} dispatched to {patient_node} for patient {patient_id}, will be free at {self.current_time + best_cost}")

    def update_available_ambulances(self):
        newly_available = []
        for ambulance_id, info in list(self.unavailable_ambulances.items()):
            current_node = info['current_node']
            path=info['final_path']
            #print('Amb ID',ambulance_id,path)
            current_node_in_path=path.index(current_node)
            if current_node!=path[-1]:
                next_node=path[current_node_in_path+1]
                #print('nonetype', path[current_node_in_path+1])
                #edge=self.graph.get_edge_data(current_node, next_node)
                #print(edge)
                availability_time=self.graph.get_edge_data(current_node, next_node)['weight']
                estimated_time=availability_time+info['current_time_t0']
                if estimated_time<=self.current_time:
                    print('Here')
                    new_current_node=path[current_node_in_path+1]
                    info['current_node']=new_current_node
                    info['current_time_t0']=self.current_time
                    print(self.current_time,':Location of assigned ambulance ', ambulance_id ,'updated to ' ,new_current_node)
            if info['availability_time'] <= self.current_time:
                newly_available.append(ambulance_id)
                free=self.unavailable_ambulances[ambulance_id]
                patient_id=free['patient_id']
                response_time=free['availability_time']
                call_time=free['call_time']
                assignment_time=free['assignment_time']
                f = open("results.txt", "a")
                f.write(f"Patient {patient_id} called at time {call_time}, received an assignment at {assignment_time}, reached a hospital at {response_time}\n")
                f.close()
                hospital_location = info['hospital_location']  # Changed from 'hospital_location' to 'station_location'
                self.available_ambulances[ambulance_id] = (hospital_location, hospital_location, hospital_location, info['path_to_station'],self.current_time)
                del self.unavailable_ambulances[ambulance_id]
        for ambulance_id, info in list(self.available_ambulances.items()):
            if info[1]:
                current_node=info[2]
                path=self.hospital_to_station[info[1]]['travel_path']
                current_node_in_path=path.index(current_node)
                if current_node!=path[-1]:
                    availability_time=self.graph.get_edge_data(current_node, path[current_node_in_path+1])['weight']
                    estimated_time=availability_time+info[4]
                    if estimated_time<=self.current_time:
                        new_current_node=path[current_node_in_path+1]
                        self.available_ambulances[ambulance_id]=(info[0],info[1],new_current_node,info[3],self.current_time)
                        print(self.current_time,':Location of available ambulance ', ambulance_id ,'updated to ' ,new_current_node)


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
        for ambulance_id, (ambulance_node, cost_to_patient, path_to_patient) in nearby_ambulances.items():
            try:
                cost_to_hospital = nx.dijkstra_path_length(self.graph, source=patient_node, target=hospital_node, weight='weight')
                path_to_hospital= nx.dijkstra_path(self.graph, source=patient_node, target=hospital_node, weight='weight')
                total_cost = cost_to_patient + cost_to_hospital
                if total_cost < min_total_cost:
                    min_total_cost = total_cost
                    best_ambulance_id = ambulance_id
                    best_path=path_to_patient[0:-1]+path_to_hospital

            except nx.NetworkXNoPath:
                pass
                #print(f"No path from patient at node {patient_node} to hospital at node {hospital_node}")

        return best_ambulance_id, min_total_cost, best_path if best_ambulance_id else None

    def mark_ambulance_unavailable(self, ambulance_location,ambulance_id, hospital_node, best_cost, patient_call, patient_id, best_path):
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
            'call_time':patient_call[2],
            'final_path':best_path,
            'current_node':ambulance_location,
            'current_time_t0':self.current_time
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
    f = open("results.txt", "w")
    f.write(f"With returning protocol\n")
    f.close()
    graph = recreate_graph_from_file('graph_structure.txt')
    assignment_file_path = 'hospital_assignments.txt'
    assignments = read_hospital_assignments(assignment_file_path)
    ambulance_data = {1: ('A210', None, 'A210', None,None), 2: ('A211', None, 'A211', None,None)} 
    #ambulance id, hospital the ambulance went to, current loaction between ambulance and station, path from hospital to station
    dispatcher = AmbulanceDispatch(graph, ambulance_data)
    patient_calls = {1:('E150', 1, 5), 2:('E153', 1, 10), 3:('E43', 1, 15), 4:('E120', 1, 20), 5:('E140', 1, 25), 6:('E92', 1, 30)}
    dispatcher.run_simulation(patient_calls)
