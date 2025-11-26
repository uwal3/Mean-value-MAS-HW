import logging
from datetime import datetime
from enum import Enum
from typing import Callable, List

from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, PeriodicBehaviour
from spade.message import Message


class MessageType:
    TERMINATION = "term"
    VALUE_UPDATE = "val"


class Cost(Enum):
    MESSAGE_C = 1000
    MESSAGE = 1
    MEMORY = 0.1
    OP = 0.01


class ConsensusAgent(Agent):

    class ConsensusBehaviour(PeriodicBehaviour):
        async def run(self):
            self.agent: ConsensusAgent

            # poll for incoming messages and calculate the new value on the fly
            new_value = 0
            msg = await self.receive()
            while msg:
                # if termination signal received echo it to everyone
                if msg.get_metadata("type") == MessageType.TERMINATION:
                    await self._broadcast_termination(excluded=msg.sender.jid)
                    self.kill()
                    return

                # it's cheaper to subtract the old value every time if n neighbours < Cost.Memory / Cost.OP
                new_value += float(msg.body) - self.agent.value  # type: ignore
                self.agent.add_cost(Cost.OP, 2)
                msg = await self.receive()
            new_value = self.agent.value + self.agent.alpha * new_value

            if self.agent.is_reporter and await self._check_convergence(new_value):
                await self._broadcast_termination()

                message = Message(to=self.agent.center_agent)
                message.set_metadata("type", MessageType.VALUE_UPDATE)
                message.body = f"{new_value}"
                await self.send(message)

                self.agent.add_cost(Cost.MESSAGE_C)
                self.kill()

            self.agent.value = new_value

            # publish the new value
            await self._broadcast_value(self.agent.value)
            self.agent.add_cost(Cost.MESSAGE, len(self.agent.recipients))

        async def on_end(self):
            self.agent.logger.debug(
                f"agent {self.agent.jid} finished with final value of {self.agent.value}"
            )
            await self.agent.stop()

        async def on_start(self):
            self.agent.logger.debug(
                f"agent {self.agent.jid} started with initial value of {self.agent.value}"
            )

        async def _check_convergence(self, new_value: float):
            if abs(new_value - self.agent.value) < self.agent.epsilon:
                self.agent.stable_ticks += 1
            else:
                self.agent.stable_ticks = 0
            return self.agent.stable_ticks >= 3

        async def _broadcast_termination(self, excluded=None):
            for recipient in self.agent.recipients:
                if recipient == excluded:
                    continue
                message = Message(to=recipient)
                message.set_metadata("type", MessageType.TERMINATION)
                await self.send(message)

        async def _broadcast_value(self, value: float):
            for recipient in self.agent.recipients:
                message = Message(to=recipient)
                message.body = f"{value}"
                message.set_metadata("type", MessageType.VALUE_UPDATE)
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
    ):
        super().__init__(jid, "password", 5222, False)

        self.value = value
        self.recipients = recipients
        self.center_agent = center_agent
        self.start_at = start_at
        self.stable_ticks = 0
        self.is_reporter = is_reporter

        self.alpha = 1 / (1 + len(recipients))
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

            if msg.get_metadata("type") == MessageType.VALUE_UPDATE:
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
