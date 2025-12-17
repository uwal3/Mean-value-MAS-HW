import logging
from datetime import datetime
from enum import Enum
from typing import Callable, List

from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, PeriodicBehaviour
from spade.message import Message


class Performative:
    REQUEST = "request"
    INFORM = "inform"


class Cost(Enum):
    MESSAGE_C = 1000
    MESSAGE = 1
    MEMORY = 0.1
    OP = 0.01


class ConsensusAgent(Agent):

    class ConsensusBehaviour(PeriodicBehaviour):
        async def run(self):
            self.agent: ConsensusAgent

            old_value = self.agent.value

            # poll for incoming messages and apply LVP algorithm
            msg = await self.receive()
            while msg:
                # if a request is received, echo it to everyone
                if msg.get_metadata("performative") == Performative.REQUEST:
                    await self._broadcast_request(excluded=msg.sender.jid)
                    self.kill()
                    return

                neighbor_value = float(msg.body)  # type: ignore
                self.agent.value += self.agent.alpha * (
                    neighbor_value - self.agent.value
                )
                self.agent.add_cost(Cost.OP, 3)
                msg = await self.receive()

            if self.agent.is_reporter and await self._check_convergence(old_value):
                await self._broadcast_request()

                message = Message(to=self.agent.center_agent)
                message.set_metadata("performative", Performative.INFORM)
                message.body = f"{self.agent.value}"
                await self.send(message)

                self.agent.add_cost(Cost.MESSAGE_C)
                self.kill()

            # publish the new value
            await self._broadcast_value(self.agent.value)
            self.agent.add_cost(Cost.MESSAGE, len(self.agent.recipients))

        async def on_end(self):
            self.agent.logger.debug(
                f"agent {self.agent.jid} finished with final value of {self.agent.value}"
            )
            await self.agent.stop()

        async def _check_convergence(self, new_value: float):
            if abs(new_value - self.agent.value) < self.agent.epsilon:
                self.agent.stable_ticks += 1
            else:
                self.agent.stable_ticks = 0
            return self.agent.stable_ticks >= self.agent.min_stable_ticks

        async def _broadcast_request(self, excluded=None):
            for recipient in self.agent.recipients:
                if recipient == excluded:
                    continue
                message = Message(to=recipient)
                message.set_metadata("performative", Performative.REQUEST)
                await self.send(message)

        async def _broadcast_value(self, value: float):
            for recipient in self.agent.recipients:
                message = Message(to=recipient)
                message.body = f"{value}"
                message.set_metadata("performative", Performative.INFORM)
                await self.send(message)
            self.agent.logger.debug(
                f"agent {self.agent.jid} published the new value of {value}"
            )

    def __init__(
        self,
        jid: str,
        value: float,
        recipients: List[str],
        center_agent: str,
        start_at: datetime,
        is_reporter: bool = False,
        epsilon: float = 1e-2,
        min_stable_ticks: int = 3,
    ):
        super().__init__(jid, "password", 5222, False)

        self.value = value
        self.recipients = recipients
        self.center_agent = center_agent
        self.start_at = start_at
        self.min_stable_ticks = min_stable_ticks
        self.stable_ticks = 0
        self.is_reporter = is_reporter

        self.alpha = 1 / (1 + 3 * len(recipients))
        self.epsilon = epsilon
        self.total_cost = 0

        self.logger = logging.getLogger(jid)

    async def setup(self):
        b = self.ConsensusBehaviour(period=1, start_at=self.start_at)
        self.add_behaviour(b)

    def add_cost(self, cost: Cost, count: int = 1):
        self.total_cost += cost.value * count


class CenterAgent(Agent):

    class CenterBehaviour(OneShotBehaviour):
        async def run(self):
            self.agent: CenterAgent

            msg = None
            while not msg:
                msg = await self.receive(1)

            if msg.get_metadata("performative") == Performative.INFORM:
                value = float(msg.body)  # type: ignore
                self.agent.logger.debug(f"received value: {value}")
                if self.agent.callback:
                    self.agent.callback(value)  # type: ignore

            await self.agent.stop()

    def __init__(self, jid: str, callback=None):
        """
        listens for messages from consensus agents

        :param callback: optional callback function to do something with the received value
        """
        super().__init__(jid, "password", 5222, False)
        self.callback = callback

        self.logger = logging.getLogger(jid)

    async def setup(self):
        b = self.CenterBehaviour()
        self.add_behaviour(b)
