"""Ripple-effect propagation over a static Bangalore corridor graph."""

import networkx as nx

BANGALORE_GRAPH = nx.Graph()
BANGALORE_GRAPH.add_weighted_edges_from(
    [
        ("Silk Board", "Koramangala", 3.2),
        ("Koramangala", "HSR Layout", 4.1),
        ("HSR Layout", "Bellandur", 5.0),
        ("Bellandur", "Marathahalli", 4.5),
        ("Silk Board", "HSR Layout", 6.8),
        ("Koramangala", "Bellandur", 7.2),
    ]
)


def calculate_ripple(source_node: str, delay_mins: float) -> list[dict]:
    if source_node not in BANGALORE_GRAPH:
        return []

    secondary_delay = round(delay_mins * 0.4, 2)
    neighbors = BANGALORE_GRAPH.neighbors(source_node)

    return [
        {
            "node": neighbor,
            "secondary_delay_mins": secondary_delay,
        }
        for neighbor in neighbors
    ]
