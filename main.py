import asyncio
import logging
from datetime import datetime, timedelta

import spade

from agent import ConsensusAgent
from util.logging import setup_global_logging
from util.topology import generate_full_topology, generate_ring_topology

setup_global_logging(logging.DEBUG)


async def main():
    logger = logging.getLogger(__name__)

    N_AGENTS = 4

    topology = generate_ring_topology(N_AGENTS)

    start_at = datetime.now() + timedelta(seconds=3)

    agents = []

    for i, node in enumerate(topology):
        agent = ConsensusAgent(
            jid=node["jid"],
            value=node["value"],
            recipients=node["neighbors"],
            start_at=start_at,
        )
        if not i:
            agent.is_reporter = True
        agents.append(agent)
        await agent.start()

    while any([agent.is_alive() for agent in agents]):
        await asyncio.sleep(0.25)

    for agent in agents:
        logger.info(f"agent {agent.jid} finished: {agent.value=}, {agent.total_cost=}")
        await agent.stop()


if __name__ == "__main__":
    spade.run(main())
