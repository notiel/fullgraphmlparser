
from dataclasses import dataclass
from typing import List, Tuple, Optional

"""
   Class Trigger describes Triggers of uml-diagrams
        name: name of trigger
        type: internal or external
        guard: text of trigger guard if any
        source: source state of trigger (actual for external triggers)
        target: target state of trigger (actual for external triggers)
        action: action for this trigger if any
        id: order number of internal trigger for better coordinates
        x, y: start of trigger visual path
        dx, dy: first relative movement of trigger visual path
        points: other relative movements of trigger visual path
        action_x, action_y, action_width: coordinates of trigger label
"""


@dataclass
class Trigger:
    name: str
    source: str
    target: str
    action: str
    id: int
    x: int
    y: int
    dx: int
    dy: int
    points: List[Tuple[int, int]]
    action_x: int
    action_y: int
    action_width: int
    type: str = "internal"
    guard: str = ""


"""
   class State describes state of uml-diagram and trigslates to qm format.
   Fields:
        name: name of state
        type: state or choice
        trigs: list of trigsitions from this state both external and internal
        entry: action on entry event
        exit: action on exit event
        id: number of state
        actions: raw_data for external actions
        old_id: id of state in graphml
        x, y: graphical coordinates
        height, width: height and with of node
"""


@dataclass
class State:
    name: str
    type: str
    actions: str
    trigs: List[Trigger]
    entry: str
    exit: str
    id: str
    new_id: List[str]
    x: int
    y: int
    width: int
    height: int
    parent: Optional['State']
    childs: List['State']
