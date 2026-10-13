from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from src.data.publication_slots import SlotDecision, SlotStore
from src.git_database import DatabaseCheckpoint


@dataclass(frozen=True)
class PublicationGate:
    """Slot owner, remote checkpoint and real clock used at the publication boundary."""
    slots: SlotStore
    decision: SlotDecision
    checkpoint: DatabaseCheckpoint
    clock: Callable[[], datetime]

    async def is_open(self) -> bool:
        """Recheck the window at an adapter's actual public-post boundary."""
        return await self.slots.can_publish(self.decision, self.clock())

    async def authorize(self, event_id: int) -> bool:
        """Persist no-replay reservation remotely before any social publication call."""
        await self.slots.arm(self.decision, event_id)
        commit_sha = await self.checkpoint.save("reservation")
        await self.slots.confirm_reservation(self.decision, commit_sha)
        return await self.is_open()
