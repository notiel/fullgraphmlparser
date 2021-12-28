"""
this is special module for creating objects for qm file. Module contains description of class State (namedtiple)
for states and  class Trigger for trigsitions between states and functions for theis analyze and creation

-get_state_by_id(states: [State], id:int, type:str) -> State                 gets state by its id
-def create_actions(raw_triggers: str, source: int) -> [Trigger]             creates trigger list from actions string
-create_state_from_node(id: int, node: dict) -> State:                       creates single qm state
-create_choice_from_node(node: dict, new_id: int, min_x: int, min_y: int) -> State:
                                                                             creates choice state from node
-create_states_from_nodes(nodes: [dict], min_x: int, min_y: int) -> [State]: function gets node data from node dict
                                                                             and returns State object with all  data
-update_states_with_edges(states: [State], flattened_edges: [dict]):         updates states with external transitions
-is_state_a_child(child: State, parent: State) -> bool:                      detects if one node is a parent to other
-is_state_a_child_by_coord(x, y, width, height, parent: State) -> bool:      detects if one node is a parent to other
                                                                             (using coordinates)
-get_parent(child: State, states: [State]) -> State:                         gets id of parent of a child
-get_parent_by_coord(x, y, w, h, states: [State]) -> State:                  gets id of parent of a child
-def get_childs(parent: State, states: [State]) ->[str]:                     gets list of childs
"""

from graphml import *
import re
from typing import List, Optional, Tuple
from stateclasses import State, Trigger


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


def get_functions(actions: str, functions: List[str]):
    """
    gets functions from code
    :param actions: text of node
    :param functions: list of sunctions to add new
    :return:
    """
    f_regexp = r'([A-Z]\w+)\([^\)]*\)'
    new_functions = re.findall(f_regexp, actions)
    for func in new_functions:
        if func not in functions:
            functions.append(func)
    return


def create_actions(raw_triggers: str, source: str, player_signal: List[str], functions: List[str]) -> \
        Tuple[List[Trigger], List[str]]:
    """
    parses raw label text with events and their actions to get a list of Triggers ("exit" and "entry" events ignored)
    we use regexp to split raw data string
    regexp is some non-space symbols, then some space symbols, than "/" symbol
    Example:
        create_actions("entry/
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
    :param functions: list of fucntions
    :param raw_triggers: string with events and reactions
    :param source: id of source node
    :param player_signal - list of all sygnals
    :return: list of Triggers, list of sygnals
    """
    # regexp takes beginnig of string, than some a-zA-Z0-9_ symbols tnan spaces, than [guard] then /
    trigger_regexp: str = r"^ *\w+ *(?:\[.+?\])?\/"
    trigger_list = re.findall(trigger_regexp, raw_triggers, re.MULTILINE)
    trigger_data = re.split(trigger_regexp, raw_triggers, flags=re.MULTILINE)
    triggers: Dict[str, str] = dict(list(zip(trigger_list, trigger_data[1:])))
    actions: List[Trigger] = list()
    for (trigger_id, (trigger, action)) in enumerate(triggers.items(), start=1):
        guard: str = ""
        i = trigger.index(r'/')
        trigger_name: str = trigger[:i].strip()
        if '[' in trigger_name:
            guard_regexp: str = r"\[.*\]"
            res = re.search(guard_regexp, trigger_name)
            guard = res.group(0)[1:-1]
            trigger_name = re.split(guard_regexp, trigger_name)[0].strip()

        if trigger_name not in player_signal and trigger_name and trigger_name != "entry" and trigger_name != 'exit':
            player_signal.append(trigger_name)
        # Un-indent each line in the (potentially multiline) action by the indent of the first line.
        lines = action.split('\n')[1:]  # discard 0, as 0-th line is the whitespace after 'SOME_SIG/'
        if lines:
            indent = len(lines[0]) - len(lines[0].lstrip())
            action = '\n'.join(line[indent:] for line in lines)
            action = action.rstrip()
        actions.append(Trigger(name=trigger_name, action=action, source=source, type="internal", guard=guard,
                               target=""))
    # add functions to function list
    get_functions(raw_triggers, functions)
    return actions, player_signal


def create_state_from_node(node: dict, node_type: str, states: [State],
                           player_signal: List[str], functions: List[str]) -> Tuple[State, List[str]]:
    """
    creates state from mode with node_type type (state or group)
    :param functions: list with functions
    :param node: dict with node data
    :param node_type: state or group
    :param states - list of created states
    :param player_signal - list of triggers
    :return State
    """
    name: str = get_state_label(node) if node_type == 'state' else get_group_label(node)
    actions: str = get_state_actions(node) if node_type == 'state' else get_group_actions(node)
    node_id = node['id']
    (triggers, player_signal) = create_actions(actions, node_id, player_signal, functions)
    state_entry: List[str] = [trig.action for trig in triggers if trig.name == 'entry']
    state_exit: List[str] = [trig.action for trig in triggers if trig.name == 'exit']
    state_entry_str: str = '#ifdef DESKTOP\nprintf("Entered state %s");\n#endif /* def DESKTOP */\n' % name
    state_entry_str += state_entry[0] if state_entry else ""
    state_exit_str: str = '#ifdef DESKTOP\nprintf("Exited state %s");\n#endif /* def DESKTOP */\n' % name
    state_exit_str += state_exit[0] if state_exit else ""
    triggers: List[Trigger] = [trig for trig in triggers if trig.name != 'entry' and trig.name != 'exit']
    parent: State = get_parent_by_label(node_id, states)
    new_id: List[str] = [(parent.new_id[0] + "/" + str(len(parent.childs) + len(parent.trigs)))]
    state: State = State(name=name, type=node_type, id=node_id, new_id=new_id, actions=actions,
                         entry=state_entry_str, exit=state_exit_str, trigs=triggers, parent=parent, childs=list())
    return state, player_signal


def create_choice_from_node(node: dict, states: [State]) -> State:
    """
    creates choice state from node
    :param node: dict with node data
    :param states - list of already creates states
    :return State
    """
    node_id = node['id']
    parent: State = get_parent_by_label(node_id, states)
    new_id: List[str] = [parent.new_id[0] + "/" + str(len(parent.childs) + len(parent.trigs))]
    state: State = State(name=get_state_label(node), type="choice", id=node_id, new_id=new_id, actions="",
                         entry="", exit="", trigs=[], parent=parent, childs=list())
    return state


def create_global_state() -> State:
    """
    creates global parent state of all states
    :return: global parent state
    """
    state = State(name="global", type="group", id="", new_id=["1"], actions="", entry="", exit="", trigs=[],
                  parent=None, childs=[])
    return state


def create_states_from_nodes(nodes: [dict], player_signal, functions: List[str]) -> \
        Tuple[List[State], List[str]]:
    """
    function gets node data from node dict and returns State object with all necessary data
    :param functions: list of functions
    :param player_signal: list of signals
    global wigth for global state, global height global state
    :param nodes: list of dicts with data
    :return: State list
    """
    states: List[State] = [create_global_state(), create_terminate_state()]
    add_terminal_trigger(states)
    for node in nodes:
        if is_node_a_group(node):
            state, player_signal = create_state_from_node(node, "group", states, player_signal, functions)
            states.append(state)
    for node in nodes:
        if is_node_a_state(node):
            state, player_signal = create_state_from_node(node, "state", states, player_signal, functions)
            states.append(state)
    for node in nodes:
        if is_node_a_choice(node):
            state = create_choice_from_node(node, states)
            states.append(state)
    return states, player_signal


def update_states_with_edges(states: [State], flat_edges: [dict], start_state: str, player_signal: [str]):
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
        for edge_type in edge_types:
            try:
                old_source: str = edge['source']
                if old_source != start_state and len(edge.keys()) > 3:
                    old_target: str = edge['target']
                    source_state: State = get_state_by_id(states, old_source, "old")
                    target_state: State = get_state_by_id(states, old_target, "old")
                    if is_edge_correct(edge, edge_type) and "#text" in edge[edge_type]['y:EdgeLabel'].keys():
                        action: str = edge[edge_type]['y:EdgeLabel']["#text"].split('/')
                        trigger_name: str = action[0].strip()
                        guard: str = ""
                        if '[' in trigger_name and ']' in trigger_name:
                            guard_regexp: str = r"\[.*\]"
                            res = re.search(guard_regexp, trigger_name)
                            guard: str = res.group(0)[1:-1]
                            trigger_name: str = re.split(guard_regexp, trigger_name)[0].strip()
                        trigger_action: str = action[1].strip() if len(action) > 1 else ""
                    else:
                        trigger_name = ""
                        trigger_action = ""
                        guard = ""
                    trig_type = "external"
                    if source_state.type == "choice":
                        trig_type = "choice_result"
                    if target_state.type == "choice":
                        trig_type = "choice_start"
                    trigger = Trigger(name=trigger_name, type=trig_type, guard=guard, source=old_source,
                                      target=old_target, action=trigger_action)
                    source_state.trigs.append(trigger)
                    if trigger_name and trigger_name not in player_signal:
                        player_signal.append(trigger_name)
            except KeyError:
                continue
    update_state_ids(states)
    return player_signal


def create_terminate_state() -> State:
    """
    creates state for terminate state machine on desktop
    :return: global parent state
    """
    state: State = State(name="final?def DESKTOP", type="state", id="last", new_id=["2"], actions="",
                         entry="""printf("\nBye! Bye!\n"); exit(0);""", exit="", trigs=[], parent=None,
                         childs=[])
    return state


def add_terminal_trigger(states):
    terminate: State = get_state_by_id(states, "last", "old")
    first: State = get_state_by_id(states, "", "old")
    trigger: Trigger = Trigger(name="TERMINATE?def DESKTOP", type="external", guard="", source=first.id,
                               target=terminate.id, action="")
    first.trigs.append(trigger)


def update_state_ids(states: [State]):
    """
    updates state ids to get path in ids
    :param states: list of states
    :return:
    """
    states.sort(key=lambda st: st.x)
    for i in range(0, len(states)):
        if states[i].new_id[0] == '1':
            states[i].new_id.append("1")
        else:
            if states[i].new_id[0] == '2':
                states[i].new_id.append("2")
            else:
                len_brothers: int = len(states[i].parent.childs)
                trigs = states[i].parent.trigs
                len_trigs = len(set([trig.name for trig in trigs]))
                states[i].new_id.append(states[i].parent.new_id[1] + "/" + str(len_brothers + len_trigs))
                if states[i].type != 'choice':
                    states[i].parent.childs.append(states[i])


def get_start_state_data(start_state: int, states: [State]) -> List[str]:
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
    return get_state_by_id(states, first_node, "new").new_id


def is_state_a_child_by_label(parent: State, label: str) -> bool:
    """
    ckecks if parent state is really parent for child state
    :param parent: is a parent state?
    :param label: child label
    :return: is a  child?
    """
    pass
    return label.startswith(parent.id)


def get_parent_by_label(label: str, states: List[State]) -> Optional[State]:
    """
    gets nearest parent using node id
    :param label: child label
    :param states: list of States
    :return:
    """
    parents: List[State] = [state for state in states if is_state_a_child_by_label(state, label)]
    if not parents:
        return None
    parents.sort(key=lambda st: len(st.id))
    return parents[-1]


def get_parent_list(state: State) -> List[State]:
    """
    get list of parent states
    :param state: current state
    :return: list of parent states
    """
    curr_state: State = state.parent
    parents: List[State] = list()
    while curr_state:
        parents.append(curr_state)
        curr_state = curr_state.parent
    return parents
