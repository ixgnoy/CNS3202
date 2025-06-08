import json
import folium
import networkx as nx
import streamlit as st
from geopy.distance import geodesic
from streamlit_folium import st_folium
import time
import multiprocessing

# Load JSON
with open("my.json", "r", encoding="utf-8") as f:
    cities_data = json.load(f)

# Extract city coordinates
city_coords = {
    city['city']: (float(city['lat']), float(city['lng']))
    for city in cities_data
}
city_list = list(city_coords.keys())

# Build graph
G = nx.Graph()
N_NEIGHBORS = 3
for city in city_list:
    G.add_node(city)
    distances = []
    for other in city_list:
        if city != other:
            dist = geodesic(city_coords[city], city_coords[other]).kilometers
            distances.append((other, dist))
    distances.sort(key=lambda x: x[1])
    for neighbor, dist in distances[:N_NEIGHBORS]:
        G.add_edge(city, neighbor, weight=dist)

# Wrapped BFS function for multiprocessing
def bfs_task(args):
    graph_data, start, goal = args
    graph = nx.node_link_graph(graph_data, edges="edges")  # for future compatibility
    visited = set()
    queue = [(start, [start])]
    while queue:
        (vertex, path) = queue.pop(0)
        if vertex in visited:
            continue
        visited.add(vertex)
        for neighbor in graph[vertex]:
            if neighbor == goal:
                return path + [neighbor]
            else:
                queue.append((neighbor, path + [neighbor]))
    return None

# Convert graph for serialization (required for multiprocessing)
graph_data = nx.node_link_data(G, edges="edges")
# Ensure the graph is serializable

# ---- Streamlit App UI ----
st.title("Malaysia City Path Finder (BFS with Parallel Processing)")

# Dropdowns for cities
start_city = st.selectbox("Select starting city", sorted(city_list), index=0)
end_city = st.selectbox("Select destination city", sorted(city_list), index=1)

# Button logic to trigger path finding
if st.button("Find Path"):
    if start_city == end_city:
        st.warning("Start and destination must be different.")
    else:
        N_RUNS = 10_000
        num_workers = multiprocessing.cpu_count()

        start_time = time.perf_counter()

        # Prepare arguments
        task_args = [(graph_data, start_city, end_city)] * N_RUNS

        with multiprocessing.Pool(processes=num_workers) as pool:
            results = pool.map(bfs_task, task_args)

        end_time = time.perf_counter()

        # Take first successful path (all are expected to be the same)
        path = next((res for res in results if res), None)

        avg_time_sec = (end_time - start_time) / N_RUNS
        exec_time_ms = avg_time_sec * 1000  # Convert to milliseconds


        # Save in session state
        st.session_state["path_result"] = {
            "path": path,
            "exec_time": exec_time_ms,
            "start": start_city,
            "end": end_city,
            "n_runs": N_RUNS
        }

# -------- Display persistent result --------
if "path_result" in st.session_state:
    result = st.session_state["path_result"]
    path = result["path"]
    if path:
        st.success(f"Path found! Average Execution Time over {result['n_runs']} runs: {result['exec_time']:.3f} ms")
        st.write(" → ".join(path))

        # Draw the map
        m = folium.Map(location=city_coords[result["start"]], zoom_start=7)
        for city, coord in city_coords.items():
            folium.CircleMarker(coord, radius=2, color="gray", fill=True).add_to(m)

        for i in range(len(path) - 1):
            folium.PolyLine([city_coords[path[i]], city_coords[path[i + 1]]], color="blue", weight=4).add_to(m)

        for idx, city in enumerate(path):
            folium.CircleMarker(
                location=city_coords[city],
                radius=6,
                color="green" if idx == 0 else "red" if idx == len(path) - 1 else "orange",
                fill=True,
                popup=f"{city} (Step {idx+1})"
            ).add_to(m)

        st_folium(m, width=700, height=500)
    else:
        st.error("No path found.")



if __name__ == "__main__":
    multiprocessing.freeze_support()
# This code is designed to run in a Streamlit app and uses multiprocessing to perform BFS on a graph of Malaysian cities.
# It allows users to select a starting and ending city, and then finds the path using parallel processing.  