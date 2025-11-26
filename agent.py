from datetime import datetime
from enum import Enum
from typing import List

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message


class Cost(Enum):
    MESSAGE_C = 1000
    MESSAGE = 1
    MEMORY = 0.1
    OP = 0.01


class ConsensusAgent(Agent):

    class ConsensusBehaviour(PeriodicBehaviour):
        async def run(self):
            self.agent: ConsensusAgent

            # poll for incoming messages
            incoming_values = []
            msg = await self.receive()
            while msg:
                print(
                    f"agent {self.agent.jid} received a message from {msg.sender.jid}"
                )
                incoming_values.append(float(msg.body))  # type: ignore
                msg = await self.receive()
            self.agent.add_cost(Cost.MEMORY, len(incoming_values) + 1)

            # update internal value
            self.agent.value = self.agent.value + self.agent.alpha * sum(
                [x_j - self.agent.value for x_j in incoming_values]
            )
            self.agent.add_cost(Cost.OP, len(incoming_values) * 2 + 1)

            # publish the new value
            for recipient in self.agent.recipients:
                message = Message(to=recipient)
                message.body = f"{self.agent.value}"
                await self.send(message)
                self.agent.add_cost(Cost.MESSAGE)

            print(
                f"agent {self.agent.jid} published the new value of {self.agent.value}"
            )

        async def on_end(self):
            print(
                f"agent {self.agent.jid} finished with final value of {self.agent.value}"
            )
            await self.agent.stop()

        async def on_start(self):
            print(
                f"agent {self.agent.jid} started with initial value of {self.agent.value}"
            )

    def __init__(
        self,
        jid: str,
        value: float,
        recipients: List[str],
        start_at: datetime,
        is_reporter: bool = False,
        epsilon: float = 1e-2,
    ):
        super().__init__(jid, "password", 5222, False)

        self.is_reporter = is_reporter
        self.start_at = start_at
        self.value = value
        self.recipients = recipients

        self.alpha = 1 / (1 + len(recipients))
        self.epsilon = epsilon
        self.total_cost = 0

    async def setup(self):
        b = self.ConsensusBehaviour(period=1, start_at=self.start_at)
        self.add_behaviour(b)

    def add_cost(self, cost: Cost, count: int = 1):
        self.total_cost += cost.value * count
