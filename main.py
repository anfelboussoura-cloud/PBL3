""" Route planner """

import json
import heapq
from collections import deque


# ==============================================================================
# Graph Utility Functions 
# ==============================================================================

#returns the number of vertices (order of the graph)
def vertexCount(G):
    return len(G) # Number of stations = number of vertices (/keys) in the dictionary

#returns the number of edges of an undirected graph (its size)
def edgeCount(G) :
    s = 0
    for value in G.values():
        s += len(value)  # We sum the number of neighbors of each station
    return s // 2 # Each connection is listed twice (A->B and B->A), so we divide by 2


# ==============================================================================
# Loading Data and Building the Graph
# ==============================================================================

def load_network(filepath):
    """Read the JSON file and return the raw network data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def build_graph(data):
    """ We build a weighted graph from the JSON files. 

    The JSON structure uses French keys:
      - "lignes" : dict of lines, each with a "stations" list (ordered)
      - "connexions" : list of explicit connections (may be empty)
      - "correspondances" : list of transfer stations
      - "temps_moyen" : default travel time in seconds between two stations

    When "connexions" is empty, connections are automatically generated from
    the ordered "stations" list of each line, using "temps_moyen" as travel time.

    Graph structure (weighted adjacency list):
     graph[station] = [(neighbor, time_in_seconds, line), ...]
    (The weight is the time_in_seconds)

    Returns:
     graph : dictionary representing the weighted graph
     transfers : a dictionary where each transfer station name is a key,
                 and gives back the lines available at that station
                 and the time needed to transfer between them"""
   
    graph = {}

    # Default travel time between two consecutive stations (seconds)
    default_time = data.get('temps_moyen', 90)

    lines_data = data.get('lignes', data.get('lines', {}))

    # Step 1 : add all stations as vertices
    for line_name, line_data in lines_data.items(): 
        for station in line_data['stations']:
            if station not in graph:
                graph[station] = []

    # Step 2 : add edges from the connexions list (if the list exists and is not empty)
    # Important: the connexions list already contains both directions (A->B and B->A)
    # so we add each connection as a one-way edge only
    # Adding the reverse would create duplicates in the graph.
    connexions = data.get('connexions', data.get('connections', []))
    for conn in connexions:
        dep = conn.get('from', conn.get('depuis', conn.get('de', '')))
        arr = conn.get('to', conn.get('vers', ''))
        time = conn.get('time', conn.get('temps', default_time))
        line = conn.get('line', conn.get('ligne', ''))

        if dep not in graph :
            graph[dep] = []
        if arr not in graph :
            graph[arr] = []

        # Add as a one-way edge: the reverse direction is already listed
        # as a separate entry in the connexions list (as in mini_reseau.json)
        graph[dep].append((arr, time, line))

    # Step 3 : if connexions was empty, generate edges from the ordered station lists
    # (both directions, since only one direction is listed per pair)
    if not connexions:
        for line_name, line_data in lines_data.items():
            stations = line_data['stations'] # ordered list of stations
            time = line_data.get('temps', default_time)
            for i in range(len(stations) - 1):
                dep = stations[i]
                arr = stations[i + 1] # next station in the line
                graph[dep].append((arr, time, line_name)) #A->B
                graph[arr].append((dep, time, line_name)) #B->A

    # Step 4 : build the transfer dictionary
    transfers = {}
    transfer_list = data.get('correspondances', data.get('transfers', [])) 
    for transfer in transfer_list:
        station = transfer['station']
        lines = transfer.get('lignes', transfer.get('lines', []))
        t_time = transfer.get('temps', transfer.get('transfer_time', 120))
        transfers[station] = { 'lines': lines, # Lines available at this station
                               'transfer_time': t_time }

    return graph, transfers


def get_transfer_stations(transfers):
    """Return the list of transfer station names."""
    return list(transfers.keys()) # The keys of the transfers dictionary are the transfer station names


# ==============================================================================
# Graph Traversal Algorithms
# ==============================================================================

#Parcours en largeur, File FIFO
def bfs(graph, start):
    """ Breadth-First Search from station 'start'.
    It visits stations level by level (fewest stops first), 
    Uses a queue, no recursion.
    Returns the list of visited stations in order."""

    visited = []
    seen = set() # To track visited stations and avoid cycles
    queue = deque([start]) # Initialize the queue with the starting station
    seen.add(start) 

    while queue :
        station = queue.popleft() # We remove the oldest station
        visited.append(station)
        for neighbor, _, _ in graph[station]: 
            # we only care about the neighbor station name here
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)

    return visited

#Parcours en profondeur, pile LIFO
def dfs(graph, start):
    """ Depth-First Search from station 'start'.
    Explores as deep as possible before backtracking.
    Uses an explicit stack, no recursion.
    Returns the list of visited stations in order. """

    visited = []
    seen = set() 
    stack = [start] 

    while stack:
        station = stack.pop() #We remove the last added element
        if station in seen : 
            continue  # Station already visited → we skip
        seen.add(station)
        visited.append(station)
        for neighbor, _, _ in graph[station]: 
            if neighbor not in seen :
                stack.append(neighbor) 

    return visited


def is_connected(graph):
    """ We check that every station can be reached from any other station.
    Uses BFS from the first station and checks if all stations are visited."""
    
    if not graph:
        return True
    start = next(iter(graph)) # We'll take any departure station
    visited = bfs(graph, start) # We traverse the entire graph from there
    return len(visited) == len(graph) 


# ==============================================================================
# Dijkstra's Algorithm 
# ==============================================================================

def dijkstra(graph, transfers, start, end):
    """ Finds the fastest route (shortest travel time) between a start and an end station.

    A transfer penalty of 120 seconds is added whenever the traveler switches line at a transfer station.

    Returns:
        path : a list of (station, line) representing each step of the route
        total_time : the total travel time in seconds
        If no path exists, returns (None, inf)"""
    
    TRANSFER_TIME = 120

    # Priority queue entries : (time_so_far, station, current_line, path)
    # We start one entry per line available at the departure station
    heap = []
    # We write _,_, because in graph[station]=[(arrival (neighbor),time,line),...] we are only interested in the line 
    for _, _, line in graph[start]:   
        heap.append((0, start, line, [(start, line)]))

    # Track the best known time for each (station, line) state
    best = {}

    while heap :
        time, station, current_line, path = heapq.heappop(heap)
        # heappop always extracts the item with the shortest time
        
        state = (station, current_line)
        if state in best:
            continue          # already found a better way to reach this state
        best[state] = time

        if station == end:
            return path, time

        for neighbor, travel_time, line in graph[station]:

            # Switching line is only possible at a transfer station
            if line != current_line:  # Line change?
                if station not in transfers:
                    continue  # Not possible here → we skip
                extra = TRANSFER_TIME  # 120 second penalty
            else:
                extra = 0  # Same line → no penalty

            new_time = time + travel_time + extra
            new_state = (neighbor, line)

            if new_state not in best:
                new_path = path + [(neighbor, line)]
                heapq.heappush(heap, (new_time, neighbor, line, new_path))

    return None, float('inf')


# ==============================================================================
# Displaying the route
# ==============================================================================

def format_time(seconds):
    """Convert a number of seconds into a readable string."""
    minutes = seconds // 60
    secs = seconds % 60  
    if minutes == 0 :
        return f"{secs} seconds" 
    if secs == 0 :
        return f"{minutes} minutes"
    return f"{minutes} minutes {secs} seconds"


def display_route(path, total_time):
    """ Print the route step by step in a readable format.
    path : list of (station, line)"""

    if not path:
        print("No route found.")
        return

    print("\n" + "="*55)
    print("                  ROUTE RESULT")
    print("="*55)

    current_line = path[0][1]

    for i, (station, line) in enumerate(path):
        # enumerate() gives both the index (i) and the value (station, line) at each step

        if i == 0:
            # First station in the path → this is where the journey starts
            print(f"  Board at {station}, line {line}")
            current_line = line

        elif i == len(path) - 1:
            # Last station in the path (index = length - 1) → journey ends here
            if line != current_line :
                # Line changed on the very last step → show the transfer first
                prev_station = path[i - 1][0] # [0] gets the station name, ignoring the line
                print(f"  Transfer at {prev_station}, take line {line}")
                current_line = line
            print(f"  Alight at {station}, line {line}")

        else :
            # Middle stations : still travelling, not at the end yet
            if line != current_line:
                # The line changed → we must have transferred at the previous station
                prev_station = path[i - 1][0]
                print(f"  Transfer at {prev_station}, take line {line}")
                current_line = line  # update the current line tracker
                print(f"  Continue through {station}")
            else:
                # Same line as before → just passing through
                print(f"  Continue through {station}")

    print("-"*55)
    print(f"  Estimated total time: {format_time(total_time)}")
    print("="*55 + "\n")


# ==============================================================================
# Console Interface
# ==============================================================================

# City name -> JSON filename mapping
CITY_FILES = {
    "Paris": "paris.json",
    "Bordeaux": "bordeaux.json",
    "Lille": "lille.json",
    "Lyon": "lyon.json",
    "Mini network": "mini_reseau.json",
}


def select_city():
    """Show the city list and return the name of the chosen city."""
    print("\n=== Available cities ===")
    cities = list(CITY_FILES.keys())  # extract city names as a list to allow index access
    for i, city in enumerate(cities, 1): # start counting from 1 (not 0) for display
        print(f"  {i}. {city}")

    while True:
        choice = input("Choose a city (number): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(cities): 
            # isdigit() : checks the input is a number, not letters or symbols
            # 1 <= ... <= len(cities) : checks the number is within the valid range
            return cities[int(choice) - 1] # -1 because lists start at index 0, not 1
        print("Invalid choice, please try again.")


def select_station(graph, prompt):
    """
    Ask the user to type a station name.
    If the name is not found, show close matches and ask again.
    """

    while True:
        station = input(prompt).strip()
        if station in graph:
            return station # exact match found → done
        
        # No exact match → search for partial matches (ignoring upper and lowercase letters)
        matches = [s for s in graph if station.lower() in s.lower()]
        # .lower() on both sides so "chat" matches "Châtelet" regardless of case
        if matches:
            print(f"Station not found. Did you mean: {', '.join(matches[:5])} ?")
            # [:5] : show at most 5 suggestions to avoid flooding the screen
        else:
            print("Station not found. Check the spelling.")


def show_network_info(graph, transfers):
    """Print basic statistics about the loaded network."""
    print(f"  Stations        : {vertexCount(graph)}")
    print(f"  Connections     : {edgeCount(graph)}")
    print(f"  Transfer points : {len(get_transfer_stations(transfers))}")
    print(f"  Connected graph : {'Yes' if is_connected(graph) else 'No'}")


def run_route(graph, transfers):
    """Ask for a departure and an arrival station, then display the best route."""
    print()
    departure = select_station(graph, "Departure station: ")
    arrival   = select_station(graph, "Arrival station  : ")

    if departure == arrival:
        print("You are already at your destination !")
        return

    path, total_time = dijkstra(graph, transfers, departure, arrival)

    if path is None:
        print("No route found between these two stations.")
    else:
        display_route(path, total_time)


def main():
    print("=" * 55)
    print("   Route Planner")
    print("=" * 55)

    while True:
        # Step 1 : choose a city
        city = select_city()
        filepath = CITY_FILES[city]

        try:
            data = load_network(filepath)
        except FileNotFoundError:
            print(f"File '{filepath}' not found.")
            print("Make sure the JSON file is in the same folder as this script.")
            continue

        graph, transfers = build_graph(data)
        print(f"\n  Network '{city}' loaded.")
        show_network_info(graph, transfers)

        # Step 2 : plan routes in a loop until the user changes city or quits
        while True:
            run_route(graph, transfers)

            print("\n  1. New route (same city)")
            print("  2. Change city")
            print("  3. Quit")
            action = input("Your choice : ").strip()
            #.strip removes unnecessary spaces at the beginning and end of the input

            if action == "3":
                print("\nGoodbye!\n")
                return
            elif action == "2":
                break
            # action == "1": loop back and ask for a new route


if __name__ == "__main__":
    main()
