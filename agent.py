from datetime import datetime
from typing import List

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message


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

            # update internal value
            self.agent.value = self.agent.value + self.agent.alpha * sum(
                [x_j - self.agent.value for x_j in incoming_values]
            )

            # publish the new value
            for recipient in self.agent.recipients:
                message = Message(to=recipient)
                message.body = f"{self.agent.value}"
                await self.send(message)

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
        self, jid: str, value: float, recipients: List[str], start_at: datetime
    ):
        super().__init__(jid, "password", 5222, False)

        self.start_at = start_at
        self.value = value
        self.recipients = recipients

        self.alpha = 1 / (1 + len(recipients))

    async def setup(self):
        b = self.ConsensusBehaviour(period=1, start_at=self.start_at)
        self.add_behaviour(b)
