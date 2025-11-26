import asyncio
import logging
import random
from datetime import datetime, timedelta

import spade
from omegaconf import OmegaConf

from agent import ConsensusAgent
from util.logging import setup_global_logging
from util.topology import generate_full_topology, generate_ring_topology

setup_global_logging(logging.DEBUG)

file_cfg = OmegaConf.load("./conf/config.yaml")
cli_cfg = OmegaConf.from_cli()
cfg = OmegaConf.merge(file_cfg, cli_cfg)


async def main():

    logger = logging.getLogger(__name__)

    n_agents = cfg.graph.n
    values = cfg.graph["values"]
    if not values:
        logger.info("no values have been specified, using random numbers")
        values = [random.randint(0, 100) for _ in range(n_agents)]
    else:
        n_agents = len(values)

    topology = None
    if cfg.graph.topology == "full":
        topology = generate_full_topology(
            n=n_agents, values=values, domain=cfg.xmpp.domain
        )
    elif cfg.graph.topology == "ring":
        topology = generate_ring_topology(
            n=n_agents, values=values, domain=cfg.xmpp.domain
        )
    assert topology is not None, "topology must be either 'full' or 'ring'"

    agents = []
    start_at = datetime.now() + timedelta(seconds=cfg.agents.start_delay_sec)
    for i, node in enumerate(topology):
        agent = ConsensusAgent(
            jid=node["jid"],
            value=node["value"],
            recipients=node["neighbors"],
            start_at=start_at,
            epsilon=cfg.agents.epsilon,
        )
        if i == 0:
            agent.is_reporter = True
        agents.append(agent)

        logger.info(f"new node with value of {node['value']}")
        await agent.start()

    while any([agent.is_alive() for agent in agents]):
        await asyncio.sleep(0.25)

    total_cost = sum([agent.total_cost for agent in agents])
    for agent in agents:
        logger.info(f"{agent.jid} finished: {agent.value=}")

    logger.info(f"total cost: {total_cost}")


if __name__ == "__main__":
    spade.run(main())
