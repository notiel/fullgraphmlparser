"""
this is special module for creating objects for qm file. Module contains description of class State (namedtiple)
for states and  class Trigger for trigsitions between states and functions for theis analyze and creation

-State                                                                       namedtuple with State data
-Trigger                                                                     namedtuple with trigger data
-get_state_by_id(states: [State], id:int, type:str) -> State                 gets state by its id
-def create_actions(raw_triggers: str, source: int) -> [Trigger]             creates trigger list from actions string
-create_state_from_node(id: int, node: dict) -> State:                       creates single qm state
-create_choice_from_node(node: dict, new_id: int, min_x: int, min_y: int) -> State:
                                                                             creates choice state from node
-create_states_from_nodes(nodes: [dict], min_x: int, min_y: int) -> [State]: function gets node data from node dict
                                                                             and returns State object with all necessary data
-update_states_with_edges(states: [State], flattened_edges: [dict]):         updates states list with external transitions
-is_state_a_child(child: State, parent: State) -> bool:                      detects if one node is a parent to other
-is_state_a_child_by_coord(x, y, width, height, parent: State) -> bool:      detects if one node is a parent to other (using coordinates)
-get_parent(child: State, states: [State]) -> State:                         gets id of parent of a child
-get_parent_by_coord(x, y, w, h, states: [State]) -> State:                  gets id of parent of a child
-def get_childs(parent: State, states: [State]) ->[str]:                     gets list of childs
"""

from collections import namedtuple
from graphml import *
import re
from logger import logging
from math import fabs



divider = 10  # we divide graphml coordinates by that value
action_delta = 5 #addition to action box
internal_trigger_height = 5 #height of space for internal trigger
internal_trigger_delta = 10 #addition to trigger name length
global_h_delta = 10 #addition to global height
global_w_delta = 10 #addition to global width
terminal_w = 10
terminal_h = 10


"""
   class State describes state of uml-diagram and translates to qm format.
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

State = namedtuple("State", "name type actions trigs entry exit id new_id  x y width height parent childs")

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

Trigger = namedtuple("Trigger", "name type guard source target action id x y dx dy points action_x action_y action_width")


def get_state_by_id(states: [State], state_id: str, id_type: str) -> State:
    """
    gets state by its id
    :param id_type: for "old" we search for state with id = id, for "new" we search state with new_id = id
    :param states: list of states
    :param state_id: id for search
    :return: state with searched id
    """
    if id_type == 'new':
        for state in states:
            if state.new_id == state_id:
                return state
    if id_type == 'old':
        for state in states:
            if state.id == state_id:
                return state
    return states[0]


def create_actions(raw_triggers: str, source: str, player_signal: [str]) -> [Trigger]:
    """
    parses raw label text with events and their actions to get a list of Triggers ("exit" and "entry" events ignored)
    we use regexp to split raw data string
    regexp is some non-space symbols, then some space symbols, than "/" symbol
    Example:
        >>>create_actions("entry/
                           BUTTON2_PRESSED/
                           flash(get_color(rgb_table));
                           play_sound(get_random_sound(BLASTER));
                           BUTTON2_PRESSED_FOR_THREE_SECOND/
                           play_sound(get_random_sound(FORCE);
                           BOTH_BUTTONS_PRESSED/
                           change_color(get_color(rgb_table));
                           play_sound(get_sound(BOOT), 5);")

        [Trigger(name="BUTTON2_PRESSED", action="flash(get_color(rgb_table));
                                                play_sound(get_random_sound(BLASTER));", source=5)
         Trigger(name="BUTTON2_PRESSED_FOR_THREE_SECOND"), action="play_sound(get_random_sound(FORCE);", source=5),
         Trigger(name="BOTH_BUTTONS_PRESSED"), action="change_color(get_color(rgb_table));
                                                     play_sound(get_sound(BOOT));", source=5)]
    :param raw_triggers: string with events and reactions
    :param source: id of source node
    :param player_signal - list of all sygnals
    :return: list of Triggers, list of sygnals
    """
    trigger_regexp = r"\S+\s*/"+'\n'
    trigger_list = re.findall(trigger_regexp, raw_triggers)
    trigger_data = re.split(trigger_regexp, raw_triggers)
    triggers = dict(list(zip(trigger_list, trigger_data[1:])))
    actions = []
    for (trigger_id, (trigger, action)) in enumerate(triggers.items(), start=1):
        guard = ""
        trigger_name = trigger[:-2].strip()
        if '[' in trigger_name:
            guard_regexp = r"\[.*\]"
            res = re.search(guard_regexp, trigger_name)
            guard = res.group(0)[1:-1]
            trigger_name = re.split(guard_regexp, trigger_name)[0].strip()
            if guard != 'else':
                logging.warning("Internal trigger %s[%s] can't contain guard" % (trigger_name, guard))

        if trigger_name not in player_signal and trigger_name and trigger_name != "entry" and trigger_name != 'exit':
            player_signal.append(trigger_name)
        if trigger_name and trigger_name[-1] == ')':
            trigger_name+='+BASE'
        actions.append(
            Trigger(name=trigger_name, action=action.strip(), source=source, type="internal", guard=guard, target="",
                    id=trigger_id, x=0, y=internal_trigger_height * trigger_id, dx=len(trigger_name)+internal_trigger_delta, dy=0, points=[], action_x=0,
                    action_y=5 * trigger_id - 2,
                    action_width=len(trigger_name)+action_delta))
    return actions, player_signal


def create_state_from_node(node: dict, node_type: str, min_x: int, min_y: int, states: [State], player_signal: [str]) \
        -> (State, [str]):
    """
    creates state from mode with node_type type (state or group)
    :param node: dict with node data
    :param node_type: state or group
    :param min_x - min x coordinate to add to state coordinate to excluse negative coordinates
    :param min_y - min y coordinate to add to state coordinate to excluse negative coordinates
    :param states - list of created states
    :param player_signal - list of triggers
    :return State
    """
    name = get_state_label(node) if node_type == 'state' else get_group_label(node)
    actions = get_state_actions(node) if node_type == 'state' else get_group_actions(node)
    node_id = node['id']
    (triggers, player_signal) = create_actions(actions, node_id, player_signal)
    state_entry = [trig.action for trig in triggers if trig.name == 'entry']
    state_exit = [trig.action for trig in triggers if trig.name == 'exit']
    state_entry = state_entry[0] if state_entry else ""
    state_exit = state_exit[0] if state_exit else ""
    triggers = [trig for trig in triggers if trig.name != 'entry' and trig.name != 'exit']

    x, y, width, height = get_coordinates(node)
    x = x // divider - min_x // divider + 2
    y = y // divider - min_y // divider + 2
    width = width // divider
    height = height // divider
    parent = get_parent_by_coord(x, y, width, height, states)
    new_id = [(parent.new_id[0] + "/" + str(len(parent.childs) + len(parent.trigs)))]
    state = State(name=name, type=node_type, id=node_id, new_id=new_id, actions=actions,
                  entry=state_entry, exit=state_exit, trigs=triggers, x=x,
                  y=y, width=width, height=height, parent=parent, childs=[])
    return (state, player_signal)


def create_choice_from_node(node: dict, min_x: int, min_y: int, states: [State]) -> State:
    """
    creates choice state from node
    :param node: dict with node data
    :param min_x - min x coordinate to add to state coordinate to excluse negative coordinates
    :param min_y - min y coordinate to add to state coordinate to excluse negative coordinates
    :param states - list of already creates states
    :return State
    """
    node_id = node['id']
    x, y, width, height = get_coordinates(node)
    x = x // divider - min_x // divider + 1
    y = y // divider - min_y // divider + 1
    width = width // divider
    height = height // divider
    parent = get_parent_by_coord(x, y, width, height, states)
    new_id = [parent.new_id[0] + "/" + str(len(parent.childs)+len(parent.trigs))]
    state = State(name=get_state_label(node), type="choice", id=node_id, new_id=new_id, actions="",
                  entry="", exit="", trigs=[], x=x, y=y,
                  width=width, height=height, parent=parent, childs=[])
    return state


def create_global_state(w: int, h: int)->State:
    """
    creates global parent state of all states
    :param w: width between states
    :param h: height of all states
    :return: global parent state
    """
    state = State(name="global", type="group", id="global", new_id=["1"], actions="",
                  entry="", exit="", trigs=[],
                  x= 1, y= 1, width=w // divider + global_w_delta, height=h // divider + global_h_delta, parent=None,
                  childs=[])
    return state



def create_states_from_nodes(nodes: [dict], coords: list, player_signal) -> [State]:
    """
    function gets node data from node dict and returns State object with all necessary data
    :param coords: min x coordinate to calibrate others, min y coordinate to calibrate others,
    global wigth for global state, global height global state
    :param nodes: list of dicts with data
    :return: State list
    """
    min_x, min_y, w, h = coords[0], coords[1], coords[2] - coords[0], coords[3] - coords[1]
    states = [create_global_state(w, h)]
    states.append(create_terminate_state(states))
    add_terminal_trigger(states)
    for node in nodes:
        if is_node_a_group(node):
            state, player_signal = create_state_from_node(node, "group", min_x, min_y, states, player_signal)
            states.append(state)
    for node in nodes:
        if is_node_a_state(node):
            state, player_signal = create_state_from_node(node, "state", min_x, min_y, states, player_signal)
            states.append(state)
    for node in nodes:
        if is_node_a_choice(node):
            state = create_choice_from_node(node, min_x, min_y, states)
            states.append(state)
    return states, player_signal


def update_states_with_edges(states: [State], flat_edges: [dict], start_state: State, player_signal: [str], min_x:int, min_y:int):
    """
    function parses events on edges and adds them as external triggers to corresponding state (excluding start_edge)
    and recognizes and adds special labels to a choice edgea
    :param states: list of states
    :param flat_edges: list with edges
    :param start_state - id for start state for exclude start edge
    :param player_signal - list of already created signals
    :return:
    """
    for edge in flat_edges:
        old_source = edge['source']
        if old_source != start_state:
            old_target = edge['target']
            source_state = get_state_by_id(states, old_source, "old")
            target_state = get_state_by_id(states, old_target, "old")
            if is_edge_correct(edge, "y:GenericEdge") and "#text" in edge['y:GenericEdge']['y:EdgeLabel'].keys():
                action = edge['y:GenericEdge']['y:EdgeLabel']["#text"].split('/')
                trigger_name = action[0].strip()
                guard = ""
                if '[' in trigger_name and ']' in trigger_name:
                    guard_regexp = r"\[.*\]"
                    res = re.search(guard_regexp, trigger_name)
                    guard = res.group(0)[1:-1]
                    trigger_name = re.split(guard_regexp, trigger_name)[0].strip()
                    if guard == 'else':
                        logging.warning("External trigger %s[%s] can't contain 'else'" % (trigger_name, guard))
                trigger_action = action[1].strip() if len(action) > 1 else ""
                if trigger_name and trigger_name[-1] == ')':
                    trigger_name+='+BASE'
            else:
                trigger_name = ""
                trigger_action = ""
                guard = ""
            x, y, dx, dy, points = get_edge_coordinates(edge)
            new_points = []
            for point in points:
                new_points.append(((point[0] - min_x)// divider, (point[1] - min_y)// divider))
            action_x, action_y, action_width = get_edge_label_coordinates(edge)
            trig_type = "external"
            if source_state.type == "choice":
                trig_type = "choice_result"
            if target_state.type == "choice":
                trig_type = "choice_start"
            print(trigger_name)
            trigger = Trigger(name=trigger_name, type=trig_type, guard=guard, source=old_source, target=old_target, action=trigger_action,
                              id=0,
                              x=(x) // divider, y=(y)// divider, dx=dx // divider, dy=dy // divider, points=new_points, action_x=action_x // divider, action_y=action_y // divider,
                              action_width=action_width // divider+3)
            source_state.trigs.append(trigger)
            if trigger_name and trigger_name not in player_signal:
                player_signal.append(trigger_name)
    update_state_ids(states)
    return player_signal

def create_terminate_state(states: [State])->State:
    """
    creates state for terminate state machine on desktop
    :param x: x of global state
    :param y: y of global state
    :param w: width between states
    :param h: height of all states
    :return: global parent state
    """
    global_state = get_state_by_id(states, 'global', 'old')
    state = State(name="final?def DESKTOP", type="state", id="last", new_id=["2"], actions="",
                  entry="""printf("Bye! Bye!"); exit(0);""", exit="", trigs=[],
                  x=global_state.x + global_state.width //2 - terminal_w //2,
                  y= states[0].y+states[0].height+5, width=terminal_w, height=terminal_h, parent=None,
                  childs=[])
    return state

def add_terminal_trigger(states):
    terminate = get_state_by_id(states, "last", "old")
    first = get_state_by_id(states, "global", "old")
    trigger = Trigger(name="TERMINATE?def DESKTOP", type="external", guard="", source=first.id, target=terminate.id, action="",
                      id=0,x=0, y=first.height//2, dx=0, dy=-terminal_h//2, points=[], action_x=-5,
                      action_y=2, action_width=10)
    first.trigs.append(trigger)

def update_state_ids(states: [State]):
    """

    :param states:
    :return:
    """
    states.sort(key = lambda st: st.x)
    for i in range(0, len(states)):
        if states[i].new_id[0] == '1':
            states[i].new_id.append("1")
        else:
            if states[i].new_id[0] == '2':
                states[i].new_id.append("2")
            else:
                brothers = len(states[i].parent.childs)
                trigs =  len(states[i].parent.trigs)
                states[i].new_id.append(states[i].parent.new_id[1] + "/" + str(brothers+trigs))
                if states[i].type != 'choice':
                    states[i].parent.childs.append(states[i])


def get_start_state_data(start_state: int, states: [State]) -> tuple:
    """
    function finds start state and gets it's id and coordinates
    :param start_state: id of start state
    :param states: list of states
    :return: id, x and y of start state
    """
    first_node = 0
    for state in states:
        if state.trigs:
            for trig in state.trigs:
                if trig.source == start_state:
                    first_node = trig.target
    return (get_state_by_id(states, first_node, "new").new_id, get_state_by_id(states, first_node, "old").y,
            (get_state_by_id(states, first_node, "new").x - 2))


def is_state_a_child(child: State, parent: State) -> bool:
    """
    detects if one node is a parent to other (using coordinates)
    :param child: child?
    :param parent: parent?
    :return: True if is a child else false
    """
    if child.x >= parent.x and child.y >= parent.y and child.x <= parent.x + parent.width and child.y<=parent.y+parent.height:
            return True
    return False


def is_state_a_child_by_coord(x, y, width, height, parent: State) -> bool:
    """
    detects if one node is a parent to other (using coordinates)
    :param x: x coord of a child
    :param y:  y coord of a child
    :param width: width of a child
    :param height: height of a child
    :param parent: parent?
    :return: true if child else false
    """
    if x+1 >= parent.x and y+1 >= parent.y and x + width - 1 <= parent.x + parent.width:
        if y + height - 1 <= parent.y + parent.height:
            return True
    return False

def get_parent(child: State, states: [State]) -> State:
    """
    gets id of parent of a child
    :param child: state to get parent
    :param states: all states
    :return: parent
    """
    parents = [state for state in states if is_state_a_child(state)]
    if not parents:
        return None
    parents.sort(key = lambda st: st.x, reverse=True)
    return parents[0]

def get_parent_by_coord(x, y, w, h, states: [State]) -> State:
    """
    gets id of parent of a child
    :param x: x coord of a child
    :param y:  y coord of a child
    :param w: width of a child
    :param h: height of a child

    :param states: all states
    :return: parent
    """
    parents = [state for state in states if is_state_a_child_by_coord(x, y, w, h, state)]
    if not parents:
        return None
    parents.sort(key = lambda st: st.x, reverse=True)
    return parents[0]

def get_parent_list(state: State, states: [State])->[State]:
    """
    get list of parent states
    :param state: current state
    :param states: list of all states
    :return: list of parent states
    """
    curr_state = state.parent
    parents = []
    while curr_state:
        parents.append(curr_state)
        curr_state = curr_state.parent
    return parents


def get_path(state1: State, state2: State, states)->str:
    """
    gets path from state1 to state2 as for folders:
    EXAMPLE: "../../1/2"
    :param state1: first state
    :param state2: second state
    :param states: list of states
    :return:
    """
    state1 = get_state_by_id(states, state1, "old")
    state2 = get_state_by_id(states, state2, "old")
    if state1.id == "global" and state2.id == "last":
        return "../../2"
    if state1 == state2:
        return ".."
    parents1 = get_parent_list(state1, states)
    parents2 = get_parent_list(state2, states)
    for parent in parents1:
        if parent in parents2:
            level = parents1.index(parent)+2
            path = "../"*level
            path2 = list(reversed(state2.new_id[1].split('/')))
            path2 = path2[:parents2.index(parent)+1]
            path+="/".join(list(reversed(path2)))
            return path

