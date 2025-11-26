import asyncio
import logging
import random
from datetime import datetime, timedelta

import spade
from omegaconf import OmegaConf

from agent import CenterAgent, ConsensusAgent
from util.logging import setup_global_logging
from util.topology import generate_full_topology, generate_ring_topology

setup_global_logging(logging.INFO)

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
    target = sum(values) / n_agents

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

    def log(value: float):
        logger.info(f"the mean value is {value}, {target=}")

    center_agent_jid = "center_agent@localhost"
    center_agent = CenterAgent(center_agent_jid, log)
    await center_agent.start()

    agents = []
    start_at = datetime.now() + timedelta(seconds=cfg.agents.start_delay_sec)
    for i, node in enumerate(topology):
        agent = ConsensusAgent(
            jid=node["jid"],
            value=node["value"],
            center_agent=center_agent_jid,
            recipients=node["neighbors"],
            start_at=start_at,
            epsilon=cfg.agents.epsilon,
        )
        if i == 0:
            agent.is_reporter = True
        agents.append(agent)

        logger.info(f"new node with value of {node['value']}")
        await agent.start()

    while center_agent.is_alive():
        await asyncio.sleep(1)

    total_cost = sum([agent.total_cost for agent in agents])
    for agent in agents:
        logger.info(f"{agent.jid} finished: {agent.value=}")

    logger.info(f"total cost: {total_cost}")


if __name__ == "__main__":
    spade.run(main())
