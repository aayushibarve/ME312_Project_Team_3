import networkx as nx
from create_graph import recreate_graph_from_file

def assign_stations_to_hospitals(graph):
    assignments = {}
    travel_times = {}  # Store travel times from stations to hospitals
    travel_paths = {}
    # Identify stations and hospitals in the graph
    stations = [node for node in graph.nodes if node.startswith('A')]  # Assuming stations start with 'A'
    hospitals = [node for node in graph.nodes if node.startswith('H')]

    # Compute shortest paths from stations to hospitals
    for hospital in hospitals:
        shortest_path_length = float('inf')
        closest_station = None
        best_path = None
        for station in stations:
            try:
                # Compute the shortest path length to each station
                path_length = nx.shortest_path_length(graph, station, hospital, weight='weight')
                path = nx.shortest_path(graph, hospital, station, weight='weight')
                if path_length < shortest_path_length:
                    shortest_path_length = path_length
                    closest_station = station
                    best_path=path
            except nx.NetworkXNoPath:
                # No path exists between station and hospital, skip
                continue
        if closest_station:
            assignments[hospital] = closest_station
            travel_times[(closest_station, hospital)] = shortest_path_length  # Store travel time
            travel_paths[(hospital, closest_station)] = best_path

    return assignments, travel_times, travel_paths

def save_assignments_to_file(assignments, travel_times, travel_paths, file_path):
    with open(file_path, 'w') as f:
        f.write("Assignment of Ambulance Stations to Hospitals:\n")
        for hospital, station in assignments.items():
            f.write(f"{hospital} assigned to {station}, Travel Time: {travel_times[(station, hospital)]}, path: {travel_paths[(hospital,station)]}\n")


file_path = 'graph_structure.txt'

G = recreate_graph_from_file(file_path)

# Assign stations to hospitals based on shortest distance
station_assignments, travel_times, travel_paths = assign_stations_to_hospitals(G)

# Save the assignments and travel times to a file
output_file_path = 'hospital_to_station_mapping.txt'
save_assignments_to_file(station_assignments, travel_times, travel_paths, output_file_path)

print("Ambulance station assignments with travel times have been saved to", output_file_path)
