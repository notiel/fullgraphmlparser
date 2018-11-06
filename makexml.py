'''
This module creates xml template using graphml diagrams
-State                                                                          dataclass with State data
-Signal                                                                         dataclass with Signal data
-get_state_by_id(states: [State], id:int, type:str) -> State                    gets state by its id
-create_actions(raw_triggers: str, source: int) -> [Signal]                     creates trigger list from actions string
-create_state_from_node(id: int, node: dict) -> State:                          creates single  state
-create_states_from_nodes(nodes: [dict]) -> [State]:                            function gets node data from node dict
-update_states_with_edges(states: [State], flattened_edges: [dict]):            updates states list with external
                                                                                transitions
-get_state_code(parent: etree._Element, states:[State])                         add xml for states to xml element tree
-get_simple_state_code(parent: etree._Element, state: State, states: [State]):  get xml code for a simple state
'''

from dataclasses import dataclass, field
from lxml import etree
from graphmlparser import *
import re


@dataclass
class Signal:
    name: str = ""
    guard: str = ""
    action: str = ""
    type: str = "external"


@dataclass
class State:
    id: int  # for guard system
    name: str = ""
    type: str = 'State'
    signals: [Signal] = field(default_factory=list)
    entry: str = ""
    exit: str = ""
    actions: str = ""


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


def create_actions(raw_triggers: str) -> [Signal]:
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
                                                play_sound(get_random_sound(BLASTER));)
         Trigger(name="BUTTON2_PRESSED_FOR_THREE_SECOND"), action="play_sound(get_random_sound(FORCE);"),
         Trigger(name="BOTH_BUTTONS_PRESSED"), action="change_color(get_color(rgb_table));
                                                     play_sound(get_sound(BOOT));")]
    :param raw_triggers: string with events and reactions
    :return: list of sygnals
    """
    trigger_regexp = r"\S+\s*/"
    trigger_list = re.findall(trigger_regexp, raw_triggers)
    trigger_data = re.split(trigger_regexp, raw_triggers)
    triggers = dict(list(zip(trigger_list, trigger_data[1:])))
    actions = []
    for (trigger_id, (trigger, action)) in enumerate(triggers.items(), start=1):
        guard = ""
        trigger_name = trigger[:-1].strip()
        if '[' in trigger_name:
            guard_regexp = r"\[.*\]"
            res = re.search(guard_regexp, trigger_name)
            guard = res.group(0)[1:-1]
            trigger_name = re.split(guard_regexp, trigger_name)[0].strip()
            if guard != 'else':
                logging.warning("Internal trigger %s[%s] can't contain guard" % (trigger_name, guard))
        actions.append(
            Signal(name=trigger_name, action=action.strip(), guard=guard))
    return actions


def create_state_from_node(node: dict, node_type: str) -> (State, [str]):
    """
    creates state from mode with node_type type (state or group)
    :param node: dict with node data
    :param node_type: state or group
    :return State
    """
    node_id = node['id']
    name = get_state_label(node) if node_type == 'state' else get_group_label(node)
    actions = get_state_actions(node) if node_type == 'state' else get_group_actions(node)
    triggers = create_actions(actions)
    state_entry = [trig.action for trig in triggers if trig.name == 'entry']
    state_exit = [trig.action for trig in triggers if trig.name == 'exit']
    state_entry = state_entry[0] if state_entry else ""
    state_exit = state_exit[0] if state_exit else ""
    triggers = [trig for trig in triggers if trig.name != 'entry' and trig.name != 'exit']
    state = State(name=name, type=node_type, signals=triggers, entry=state_entry, exit=state_exit, id=node_id)
    return state


def create_choice_from_node(node: dict) -> State:
    """
    creates choice state from node
    :param node: dict with node data
    :return State
    """
    node_id = node['id']
    state = State(name=get_state_label(node), type="choice", id=node_id)
    return state


def create_states_from_nodes(nodes: [dict]) -> [State]:
    """
    function gets node data from node dict and returns State object with all necessary data
    :param nodes: list of dicts with data
    :return: State list
    """
    states = []
    for node in nodes:
        if is_node_a_group(node):
            state = create_state_from_node(node, "group")
            states.append(state)
    for node in nodes:
        if is_node_a_state(node):
            state = create_state_from_node(node, "state")
            states.append(state)
    for node in nodes:
        if is_node_a_choice(node):
            state = create_choice_from_node(node)
            states.append(state)
    return states


def update_states_with_edges(states: [State], flat_edges: [dict], start_state: int):
    """
    function parses events on edges and adds them as external triggers to corresponding state (excluding start_edge)
    and recognizes and adds special labels to a choice edgea
    :param states: list of states
    :param flat_edges: list with edges
    :param start_state - id for start state for exclude start edge
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
            else:
                trigger_name = ""
                trigger_action = ""
                guard = ""
            trig_type = "external"
            if source_state.type == "choice":
                trig_type = "choice_result"
            if target_state.type == "choice":
                trig_type = "choice_start"
            trigger = Signal(name=trigger_name, type=trig_type, guard=guard, action=trigger_action)
            source_state.signals.append(trigger)


def createxml(filename: str, states: [State], start_action: str):
    """

    :param filename: name of resulting file
    :param states: list of states with data
    :param start_action: initial action
    :return:
    """
    xml_uml = etree.Element('umldiagram')
    xml_description = etree.SubElement(xml_uml, 'description')
    xml_description.text = ' '
    xml_eventfields = etree.SubElement(xml_uml, 'eventfields')
    xml_eventfields.text = '/*add event fields here as field tag with parameters name and type*/'
    xml_statefields = etree.SubElement(xml_uml, 'statefields')
    xml_statefields.text = '/*add state fields here as field tag with parameters name and type*/'
    xml_constructor = etree.SubElement(xml_uml, 'constructor')
    xml_ctorfields = etree.SubElement(xml_constructor, 'ctorfields')
    xml_ctorfields.text = '/*add extra constructor fields here as field tag with parameters name and type*/'
    xml_ctorcode = etree.SubElement(xml_constructor, 'ctorcode')
    xml_ctorcode.text = etree.CDATA('\n/*extra constructor code*/\n')
    xml_hcode = etree.SubElement(xml_uml, 'hcode')
    xml_hcode.text = etree.CDATA('\n/*add any code to add to .h file*/\n')
    xml_cppcode = etree.SubElement(xml_uml, 'cppcode')
    xml_cppcode.text = etree.CDATA('\n/*add any code to add to .cpp file*/\n')
    xml_initial = etree.SubElement(xml_uml, 'initial')
    xml_initial.text = etree.CDATA('\n/*'+start_action+'*/\n')
    add_states_to_xml(xml_uml, states)
    xml_tree = etree.ElementTree(xml_uml)
    xml_tree.write('%s.xml' % filename, xml_declaration=True, encoding="UTF-8", method="xml", pretty_print=True,)


def add_states_to_xml(xml_parent: etree._Element, states: [State]):
    """
    add xml code for states to xml element tree
    :param xml_parent: parent element of state
    :param states: list of States
    :return:
    """
    for state in states:
        get_simple_state_code(xml_parent, state, states)


def get_simple_state_code(parent: etree._Element, state: State, states: [State]):
    """
    get qm code for a simple state
    :param parent: xml tree element to add data
    :param state: simple state
    :param states: list of states
    :return:
    """
    xml_state = etree.SubElement(parent, 'state', name=state.name)
    if state.entry:
        xml_entry = etree.SubElement(xml_state, 'entry')
        xml_entry.text = etree.CDATA('\n/*'+state.entry + '*/\n')
    if state.exit:
        qm_exit = etree.SubElement(xml_state, 'exit')
        qm_exit.text = etree.CDATA('\n/*' + state.exit + '*/\n')
    for signal in state.signals:
        get_signal_code(xml_state, signal)


def get_signal_code(xml_state: etree._Element, signal: Signal):
    """
    functions adds tags for signal to xml tree
    :param xml_state: parent element for adding tags
    :param signal: signal to add
    :return:
    """
    xml_signal = etree.SubElement(xml_state, "signal", name=signal.name)
    if signal.guard:
        xml_guard = etree.SubElement(xml_signal, 'guard')
        xml_guard.text = etree.CDATA(signal.guard)
    xml_code = etree.SubElement(xml_signal, 'code')
    xml_code.text = etree.CDATA("\n/*" + signal.action + '*/\n')
