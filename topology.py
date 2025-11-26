import random
from typing import Any, Dict, List


def generate_ring_topology(
    n: int, domain: str = "localhost", values: List[int] | None = None
) -> List[Dict[str, Any]]:
    topology = []

    for i in range(1, n + 1):
        prev_id = n if i == 1 else i - 1
        next_id = 1 if i == n else i + 1

        my_jid = f"agent{i}@{domain}"
        neighbors = [f"agent{prev_id}@{domain}", f"agent{next_id}@{domain}"]

        start_value = random.randint(0, 500) if not values else values[i - 1]

        topology.append({"jid": my_jid, "value": start_value, "neighbors": neighbors})
    return topology


def generate_full_topology(
    n: int, domain: str = "localhost", values: List[int] | None = None
) -> List[Dict[str, Any]]:
    topology = []

    all_jids = [f"agent{i}@{domain}" for i in range(1, n + 1)]

    for i in range(1, n + 1):
        my_jid = f"agent{i}@{domain}"
        neighbors = [jid for jid in all_jids if jid != my_jid]
        start_value = random.randint(0, 500) if not values else values[i - 1]
        topology.append({"jid": my_jid, "value": start_value, "neighbors": neighbors})
    return topology
