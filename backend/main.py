from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import networkx as nx
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables (Make sure GROQ_API_KEY is in your .env file)
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq Client
groq_client = Groq(api_key=GROQ_API_KEY)

# Initialize FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STEP 1: DEFINE THE BANGALORE NETWORK GRAPH ---
base_graph = nx.Graph()
base_graph.add_nodes_from(["Silk Board", "HSR Layout", "Koramangala", "Bellandur", "Domlur", "Marathahalli"])

# Add edges with weights (representing travel time in minutes under normal conditions)
edges = [
    ("Silk Board", "HSR Layout", 2),
    ("HSR Layout", "Bellandur", 4),
    ("Bellandur", "Marathahalli", 5),
    ("Silk Board", "Koramangala", 3),
    ("Koramangala", "Domlur", 4),
    ("Domlur", "Marathahalli", 6)
]
base_graph.add_weighted_edges_from(edges)

# Define Request Model
class EventRequest(BaseModel):
    text: str

@app.post("/api/analyze_event")
async def analyze_event(request: EventRequest):
    # --- STEP A: LLM EXTRACTION (GROQ LLAMA-3) ---
    prompt = f"""
    You are a traffic intelligence AI. Extract the incident details from the text below.
    Respond strictly in valid JSON format with exactly these keys:
    - "incident_type": string (e.g., "breakdown", "accident", "rally", "waterlogging")
    - "location": string (MUST exactly match one of these: "Silk Board", "HSR Layout", "Koramangala", "Bellandur", "Domlur", "Marathahalli". If unknown, default to "HSR Layout")
    - "severity": string (strictly "low", "medium", or "high")
    
    Text: "{request.text}"
    """
    
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.1,
            response_format={"type": "json_object"} # Forces perfect JSON output
        )
        extraction = json.loads(response.choices[0].message.content)
    except Exception as e:
        # Failsafe for Hackathon Demo if API rate limits hit
        extraction = {
            "incident_type": "unknown_incident",
            "location": "HSR Layout",
            "severity": "high"
        }

    # Clean data to ensure it matches our graph exactly
    valid_nodes = ["Silk Board", "HSR Layout", "Koramangala", "Bellandur", "Domlur", "Marathahalli"]
    loc = extraction.get("location", "HSR Layout")
    if loc not in valid_nodes:
        loc = "HSR Layout"
    extraction["location"] = loc
    sev = extraction.get("severity", "high").lower()

    # --- STEP B: ML PREDICTION SIMULATION ---
    if sev == "high":
        delay = 75.0
    elif sev == "medium":
        delay = 35.0
    else:
        delay = 15.0

    # Resource Allocation Matrix
    if delay > 45:
        resources = {"police_required": 12, "barricades": 40, "tow_trucks": 1}
    else:
        resources = {"police_required": 4, "barricades": 10, "tow_trucks": 0}

    # --- STEP C: GRAPH THEORY ROUTING & RIPPLE ENGINE ---
    # Standard route calculation (e.g., Flipkart truck going from Silk Board to Marathahalli)
    try:
        standard_route = nx.shortest_path(base_graph, source="Silk Board", target="Marathahalli", weight="weight")
    except:
        standard_route = []

    # Apply penalty to the graph simulating the blockage
    penalized_graph = base_graph.copy()
    if loc in penalized_graph.nodes:
        for neighbor in list(penalized_graph.neighbors(loc)):
            # Add a massive penalty (999) to simulate blocked roads around the epicenter
            penalized_graph[loc][neighbor]['weight'] += 999 

    # Calculate optimal diversion route avoiding the blockage
    try:
        optimal_diversion = nx.shortest_path(penalized_graph, source="Silk Board", target="Marathahalli", weight="weight")
    except:
        optimal_diversion = standard_route

    # Calculate Ripple Effect (Neighboring nodes get 40% of the delay)
    ripple = []
    if loc in base_graph.nodes:
        for n in base_graph.neighbors(loc):
            ripple.append({
                "node": n, 
                "secondary_delay_mins": round(delay * 0.4, 2)
            })

    # --- STEP D: RETURN PERFECT JSON TO FRONTEND ---
    return {
        "extraction": extraction,
        "predictions": {
            "predicted_delay_mins": delay,
            "resources": resources
        },
        "routing_and_ripple": {
            "standard_route": standard_route,
            "optimal_diversion": optimal_diversion,
            "ripple": ripple
        }
    }