import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def recreate_graph_from_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Initialize an empty graph
    G = nx.Graph()
    
    
    n_nodes = int(lines[0])
    
   
    for i in range(1, n_nodes+1):
        line = lines[i].split()
        node_type = line[0]
        node_id = f"{node_type}{line[1]}"
        x, y = float(line[2]), float(line[3])
        G.add_node(node_id, pos=(x, y), node_type=node_type)
    
    # Extract edges information
    for line in lines[n_nodes+1:]:
        node1, node2, weight = line.split()
        G.add_edge(node1, node2, weight=float(weight))
    
    return G


def visualize_graph(G):
    
    colors = {'E': 'blue', 'H': 'green', 'A': 'red'}
    sizes = {'E': 100, 'H': 200, 'A': 300}
    print(G.nodes(data=True))
    node_colors = [colors[data['node_type']] for _, data in G.nodes(data=True)]
    node_sizes = [sizes[data['node_type']] for _, data in G.nodes(data=True)]

   
    pos = nx.get_node_attributes(G, 'pos')

    
    plt.figure(figsize=(12, 12))
    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=node_sizes, edge_color='gray', font_size=8)

  
    legend_handles = [mpatches.Patch(color=color, label=label) for label, color in colors.items()]
    plt.legend(handles=legend_handles, loc='best')

    plt.title('Visualized Graph from Text File')
    plt.axis('equal')  
    plt.show()

# File path to the 'graph_structure.txt' file
file_path = 'graph_structure.txt'


G_recreated = recreate_graph_from_file(file_path)

visualize_graph(G_recreated)
