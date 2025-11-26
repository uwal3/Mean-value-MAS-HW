import asyncio
from datetime import datetime, timedelta

import spade

from agent import ConsensusAgent
from topology import generate_full_topology, generate_ring_topology


async def main():

    N_AGENTS = 12

    topology = generate_full_topology(N_AGENTS)

    start_at = datetime.now() + timedelta(seconds=3)

    agents = []

    for node in topology:
        agent = ConsensusAgent(
            jid=node["jid"],
            value=node["value"],
            recipients=node["neighbors"],
            start_at=start_at,
        )
        agents.append(agent)
        await agent.start()

    while any([agent.is_alive() for agent in agents]):
        await asyncio.sleep(0.25)

    print("\nresults:")
    for agent in agents:
        print(f"agent {agent.jid}: {agent.value}")
        await agent.stop()


if __name__ == "__main__":
    spade.run(main())
