import json
import networkx as nx
import matplotlib.pyplot as plt

#TODO remove file_path as it will be given within the llmPipeline run_batch()
def build_question_tree(file_path, email_result):
    # Load JSON data
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Extract questions from the provided dictionary
    questions = email_result['questions']

    # Create a directed graph
    G = nx.DiGraph()

    # Add nodes and edges
    for question in questions:
        q_id = question['question_id']
        layer = question['layer']
        color = 'green' if question.get('processed') else 'red'
        G.add_node(q_id, layer=layer, color=color)

        parent_id = question.get('parent_id')
        if parent_id is not None:
            G.add_edge(parent_id, q_id)

    # Create a layered layout manually
    layers = {}
    for node, attrs in G.nodes(data=True):
        layer = attrs['layer']
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(node)

    pos = {}
    y_gap = 1
    for i, layer in enumerate(sorted(layers.keys())):
        x_gap = 1 / (len(layers[layer]) + 1)
        for j, node in enumerate(sorted(layers[layer])):
            pos[node] = (j * x_gap + x_gap, -i * y_gap)

    colors = [G.nodes[n]['color'] for n in G.nodes]

    plt.figure(figsize=(18, 12))
    nx.draw(
        G, pos, with_labels=True, node_color=colors, node_size=2500,  # Increased node size
        font_size=12, font_color="black", font_weight="bold",
        arrows=True, arrowstyle='-|>', arrowsize=20
    )
    plt.title('Hierarchical Question Tree (Green=Processed, Red=Unprocessed)', fontsize=16)
    plt.show()

# Call the function with the provided file
build_question_tree("C:/Users/modio/Desktop/EmailSignals/review_results/2025-07-10_18-18-14--686f602699a8bf938dc2ab37.json")