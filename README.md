# PBL3

📦 [PBL3- ROUTE PLANNER]
MVP Status: [e.g., v1.0-Production]

Group Members: Aubane JOSEPH, Anfel BOUSSOURA, Delhia KEDDAR, Joan ATTAL

---------------------------------------------------------------------
🎯 Project Overview

Provide a concise (2-3 sentence) description of what your application does and the specific problem it solves. Why did you build this?

Our app is a public transit route planner for several French cities (Paris, Lyon, Bordeaux, Lille). You type a departure and arrival station, and it finds the fastest path using Dijkstra's algorithm, including transfer penalties between lines. We built it to apply the graph algorithms we studied in class to something concrete and familiar.

----------------------------------------------------------------------
🚀 Quick Start (Architect Level: < 60s Setup)

Instructions on how to get this project running on a fresh machine.

Clone the repo:
git clone [https://github.com/anfelboussoura-cloud/pbl3%5C]
cd [project-folder]

Setup Virtual Environment:
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

Install Dependencies:
pip install -r requirements.txt

Run Application:
python main.py

-----------------------------------------------------------------
🛠️ Technical Architecture

Explain how your code is organized. An "Architect-level" README should describe the separation of concerns.

Everything is in main.py, split into logical sections. The graph is built as a weighted adjacency list from a JSON file, then Dijkstra finds the fastest path, tracking (station, line) pairs to correctly handle the 120-second transfer penalty. BFS and DFS are also implemented for network exploration and connectivity checks.

-----------------------------------------------------------------
🧪 Testing & Validation

How can a user verify the code works?

Validation is manual using mini_reseau.json, a small network easy to verify by hand. Launch the app, pick that network, and route between two distant stations to see a full itinerary with transfers and total time.

-------------------------------------------------------------------
📦 Dependencies

List the main third-party libraries used and why they were chosen:

library_name: We only use Python's standard library, no external packages needed. json reads the data files, heapq powers Dijkstra's priority queue, and collections.deque handles BFS.

-----------------------------------------------------------------------
🔮 Future Roadmap (v2.0)

What features would you add if you had more time or a larger budget?

A graphical map interface, real GTFS data from RATP/SNCF, multi-criteria routing (fewest transfers), and live disruption alerts.

__
