#!/usr/bin/env python3
"""Reference regression for cached-LOSS prefix provenance owner-event semantics.

This is deliberately independent of the solver.  It checks the compact
`origin_outer_event <= last_exited_outer_event` predicate against an explicit
reference model before the frozen 12-parent cohort is inspected.
"""

from __future__ import annotations

import random


class Compact:
    def __init__(self, slots: int = 32) -> None:
        self.owner = [0] * slots
        self.depth = 0
        self.next_event = 1
        self.active = 0
        self.last_exited = 0

    def enter(self) -> None:
        if self.depth == 0:
            assert self.next_event < 2**32
            self.active = self.next_event
            self.next_event += 1
        self.depth += 1

    def exit(self) -> None:
        assert self.depth > 0
        self.depth -= 1
        if self.depth == 0:
            self.last_exited = self.active
            self.active = 0

    def insert(self, slot: int) -> None:
        self.owner[slot] = self.active if self.depth else 0

    def clear(self, slot: int) -> None:
        self.owner[slot] = 0

    def later(self, slot: int) -> bool:
        o = self.owner[slot]
        return o != 0 and o <= self.last_exited


class Reference:
    def __init__(self, slots: int = 32) -> None:
        self.owner = [None] * slots
        self.stack: list[int] = []
        self.next_event = 1
        self.exited: set[int] = set()

    def enter(self) -> None:
        if not self.stack:
            event = self.next_event
            self.next_event += 1
        else:
            event = self.stack[-1]
        self.stack.append(event)

    def exit(self) -> None:
        assert self.stack
        event = self.stack.pop()
        if not self.stack:
            self.exited.add(event)

    def insert(self, slot: int) -> None:
        self.owner[slot] = self.stack[-1] if self.stack else None

    def clear(self, slot: int) -> None:
        self.owner[slot] = None

    def later(self, slot: int) -> bool:
        return self.owner[slot] in self.exited


def deterministic() -> None:
    c, r = Compact(4), Reference(4)
    c.enter(); r.enter()                 # A
    c.insert(0); r.insert(0)
    assert not c.later(0)
    c.enter(); r.enter()                 # nested A
    c.insert(1); r.insert(1)
    c.exit(); r.exit()
    assert not c.later(0) and not c.later(1)
    c.exit(); r.exit()
    assert c.later(0) and c.later(1)

    c.enter(); r.enter()                 # B
    assert c.later(0)                    # A remains reusable while B is active
    c.insert(2); r.insert(2)
    assert not c.later(2)
    c.clear(0); r.clear(0)
    assert not c.later(0)
    c.exit(); r.exit()
    assert c.later(2)


def randomized(seed: int = 0xC0C1E, steps: int = 200_000) -> None:
    rng = random.Random(seed)
    c, r = Compact(), Reference()
    for i in range(steps):
        actions = ["insert", "clear", "hit"]
        if c.depth < 8:
            actions.append("enter")
        if c.depth:
            actions.append("exit")
        action = rng.choice(actions)
        slot = rng.randrange(len(c.owner))
        if action == "enter":
            c.enter(); r.enter()
        elif action == "exit":
            c.exit(); r.exit()
        elif action == "insert":
            c.insert(slot); r.insert(slot)
        elif action == "clear":
            c.clear(slot); r.clear(slot)
        else:
            assert c.later(slot) == r.later(slot), (i, slot)
        assert c.depth == len(r.stack)
        for s in range(len(c.owner)):
            assert c.later(s) == r.later(s), (i, action, s)


def wrap_guard() -> None:
    c = Compact(1)
    c.next_event = 2**32
    try:
        c.enter()
    except AssertionError:
        pass
    else:
        raise AssertionError("uint32 event-id wrap must fail closed")


if __name__ == "__main__":
    deterministic()
    randomized()
    wrap_guard()
    print("cached-LOSS prefix owner-event model: PASS")
