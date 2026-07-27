"""Progress-callback types shared by the cleanup services.

These were previously annotated ``"object | None"``, which told a reader (and a
type checker) nothing about how to call them. The services invoke them once per
attempted item or batch so a task can report progress and errors as it goes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

# (target_id, ok, error) — called after each individual delete/unfollow attempt.
ItemCallback = Callable[[int, bool, dict[str, Any] | None], None]

# (media_id, batch, error) — called after each batched favorite delete.
BatchCallback = Callable[[int, Sequence[str], dict[str, Any] | None], None]
