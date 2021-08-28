"""
This module creates qm structure

-get_start_state_data(start_state: int, states: [State]) -> tuple:           function finds start state and gets it's
                                                                             id and coordinates
-get_parameters_data(parameter: str) -> tuple:                               get data for variables from parameters
                                                                             string
-get_parameters_code(parameter_text: str, qm_class: etree._Element, qm_documentation: etree._Element):
                                                                             add parameters data to qm structure
-get_initial_code(qm_statechart: etree._Element,
                              id_start: int, x: int, y: int)                  add xml tags for start element
                                                                              to xml element tree
-get_trig_coordinates(trig: Trigger, states:[State])->str:                    create trigger coordinates string for qm
-get_action_coordinates(trig: Trigger)->tuple:                                functions gets coordinates for trigger
                                                                              label
                                                                              (relative to trigger start point)
-get_state_code(qm_statechart: etree._Element, qm_states:[State])             add xml for states to xml element tree
-get_simple_state_code(parent: etree._Element, state: State, states: [State]):
                                                                              get qm code for a simple state
-get_group_state_code(parent: etree._Element, state: State, states: [State]): get code for qroup. uses recursion

"""

from lxml import etree
from string import Template
from qm import *
from typing import List, Tuple
from math import fabs

QMTag = etree._Element

documentation = 'test qm file made by Ostranna and ksotar'  # documentation string
framework = "qpc"  # framework, use qpc for c and qpcpp for cpp
pack_name = 'SMs'  # name for your state machine package
stereotype = '0x02'  # some magical constant
initial_coordinates = '2,2,4,3'  # coordinates and type for initial point
box_coordinates = "0,-2,10,2"  # relative coordinates for action boxes
entry_coordinates = "1,2,30,4"  # relative coordinates for entry action
exit_coordinates = "1,6,30,4"  # relative coordinates for exit action
internal_trig_coordinates = "3,-1,20,0"  # relative coordinate for start of internal trigger label
trig_action_coordinates = "0,-2,25,4"  # relative coordinates for trigger label

vis_dict = {"public": "0x00", "private": "0x02", "protected": "0x01"}  # codes for visibility of variables


def get_parameters_data(parameter: str) -> Tuple[str, str, str, str]:
    """
    get data for variables from parameters string
    :param parameter: string with data for parameter
    :return: (type, name, visibility, comment) (if possible)
    """
    data: List[str] = parameter.split()
    if len(data) < 2:
        return "", "", "", ""
    if data[0] == "unsigned":
        if data[1] == 'int':
            param_type = 'unsigned int'
            i = 2
        else:
            return "", "", "", ""
    else:
        param_type = data[0]
        i = 1
    param_name: str = data[i].replace(";", "")
    param_name.replace(";", "")
    param_name.replace("/", "")
    param_vis: str = "0x00"
    param_comment: str = ""
    if len(data) > i + 1:
        param_vis = vis_dict[data[i + 1]] if data[i + 1] in vis_dict.keys() else ""
        if param_vis:
            data = data[(i + 1):]
        else:
            data = data[(i + 1):]
        param_comment = " ".join(data)
    return param_name, param_type, param_vis, param_comment


def update_event_fields(parameter: str, event_fields: dict):
    """
    function updates dictionary type:name of fields of event structure (empty by default)
    :param parameter:
    :param event_fields:
    :return:
    """
    if parameter:
        data: List[str] = parameter.split()
        param_name: str = data[-1].replace(";", "")
        param_type: str = ' '.join(data[:-1])
        event_fields[param_name] = param_type
        return event_fields


def get_event_struct(event_fields: dict, modelname: str) -> str:
    """
    funtion created c code for event struct using fields defined in event_fields dict
    :param modelname: name of model
    :param event_fields: dict with event fields
    :return: str with event struct
    """
    event_struct: str = "\ntypedef struct %s {\n    QEvt super;" % (modelname + 'QEvt')
    for key in event_fields.keys():
        event_struct += "\n    %s %s;" % (event_fields[key], key)
    event_struct += "\n} %s;\n" % (modelname + 'QEvt')
    return event_struct


def get_parameters_code(parameter_text: str, qm_class: QMTag, qm_documentation: QMTag):
    """
    add parameters data to qm structure
    :param qm_documentation: tag to documentation
    :param parameter_text: text with parameters data
    :param qm_class: xml field to add data
    :return:
    """
    wrong_data: str = ""
    parameters: List[str] = parameter_text.split("\n")
    for parameter in parameters:
        parameter = parameter.strip()
        param_name, param_type, param_vis, param_comment = get_parameters_data(parameter)
        if param_name:
            qm_attribute = etree.SubElement(qm_class, "attribute", name=param_name, type=param_type,
                                            visibility=param_vis, properties="0x00")
            if param_comment:
                qm_documentation = etree.SubElement(qm_attribute, "documentation")
            qm_documentation.text = param_comment
        else:
            wrong_data += ("\n" + parameter)
            qm_documentation.text = wrong_data


def get_trig_coordinates(trig: Trigger, states: [State]) -> str:
    """
    create trigger coordinates string for qm
    Example "21,65,2,2,3,-12,0,48,-11,12". First two values are coordinates of beginning, then type of arrow, then
    pairs of shift coordinates. Last last shift is calculated from end of arrow point. If arrow is vertical,
    last y shift is removed
    :param trig: trigger
    :param states: list of states
    :return: string with edge coordinate
    """
    state_x: int = get_state_by_id(states, trig.source, "old").x
    state_y: int = get_state_by_id(states, trig.source, "old").y
    width: int = get_state_by_id(states, trig.source, "old").width
    height: int = get_state_by_id(states, trig.source, "old").height
    cur_x: int = state_x + width // 2 + trig.x
    cur_y: int = state_y + height // 2 + trig.y
    coordinates: List[int] = [cur_x, cur_y, 2, 2]
    for i in range(len(trig.points)):
        x = trig.points[i][0]
        y = trig.points[i][1]
        coordinates.extend([y - cur_y, x - cur_x])
        cur_x = x
        cur_y = y
    state_x = get_state_by_id(states, trig.target, "old").x
    state_y = get_state_by_id(states, trig.target, "old").y
    width = get_state_by_id(states, trig.target, "old").width
    height = get_state_by_id(states, trig.target, "old").height
    last_x: int = state_x + width // 2 + trig.dx
    last_y: int = state_y + height // 2 + trig.dy
    coordinates.extend([last_y - cur_y, last_x - cur_x])
    if fabs(last_x - cur_x) <= 1:
        coordinates.pop()
    coordinates_str = ','.join(list(map(str, coordinates)))
    return coordinates_str


def get_action_coordinates(trig: Trigger) -> str:
    """
    dunctions gets coordinates for trigger label (relative to trigger start point)
    :param trig: trigger with label
    :return: string with action box coordinates (trigger label)
    """
    dx: int = trig.action_x
    dy: int = trig.action_y
    width = trig.action_width
    return "%i,%i,%i,4" % (dx, dy, width)


def get_guard_coordinates(trig: Trigger, move: int) -> str:
    """
    dunctions gets coordinates for trigger label (relative to trigger start point)
    :param move: some shift
    :param trig: trigger with label
    :return: string with action box coordinates (trigger label)
    """
    dx: int = trig.action_x
    dy: int = trig.action_y + move
    width: int = trig.action_width
    return "%i,%i,%i,4" % (dx, dy, width)


def get_initial_code(qm_statechart: QMTag, start_state: State, start_action: str, x: int, y: int):
    """
    add xml tags for start element to xml element tree
    Exampe: <initial target="../1">
                 <action>do something</action>
                 <initial_glyph conn="2,2,4,3,3,3">
                      <action box="0,-2,10,2"/>
                 </initial_glyph>
            </initial>
    :param qm_statechart: parent element of element tree to initial element
    :param start_state: start state
    :param start_action: start_action
    :param x: x coordinate of initial transaction
    :param y: y coordinate of initial transaction
    :return:
    """
    path: str = '../' + start_state.new_id[1]
    qm_initial = etree.SubElement(qm_statechart, 'initial', target=path)
    qm_initial_action = etree.SubElement(qm_initial, "action")
    qm_initial_action.text = start_action
    qm_initial_glyph = etree.SubElement(qm_initial, 'initial_glyph', conn="%s,%i,%i" % (initial_coordinates, x, y))
    _ = etree.SubElement(qm_initial_glyph, 'action', box=box_coordinates)


def get_state_code(qm_statechart: QMTag, states: [State], printed_ids: [str]):
    """
    add qm code for states to xml element tree
    EXAMPLE
    <state name="ambient">
        <entry>SndPlayer_delete_all();
               SndPlayer_add_track( Player_get_emotion( AMBIENT));</entry>
        <exit>SndPlayer_delete_all();</exit>
        <state_glyph node="3,5,33,13">
            <entry box="1,2,10,2"/>
            <exit box="1,4,10,2"/>
        </state_glyph>
    </state>
    :param qm_statechart: parent element of state
    :param states: list of States
    :param printed_ids: list of printed states
    :return:
    """
    for state in states:
        if state.new_id not in printed_ids:
            if state.type == 'group':
                get_group_state_code(qm_statechart, state, states, printed_ids)
            if state.type == 'state':
                get_simple_state_code(qm_statechart, state, states, printed_ids)


def get_simple_state_code(parent: QMTag, state: State, states: [State], printed_ids: [str]):
    """
    get qm code for a simple state
    :param parent: xml tree element to add data
    :param state: simple state
    :param states: list of states
    :return:
    :param printed_ids: list of printed states
    """
    printed_ids.append(state.new_id)
    qm_state = etree.SubElement(parent, 'state', name=state.name)
    if state.entry:
        qm_entry = etree.SubElement(qm_state, 'entry')
        qm_entry.text = state.entry
    if state.exit:
        qm_exit = etree.SubElement(qm_state, 'exit')
        qm_exit.text = state.exit
    for trig in state.trigs:
        get_trig_code(qm_state, states, trig)
    qm_state_glyph = etree.SubElement(qm_state, 'state_glyph',
                                      node="%i,%i,%i,%i" % (state.x, state.y, state.width, state.height))
    _ = etree.SubElement(qm_state_glyph, 'entry', box=entry_coordinates)
    _ = etree.SubElement(qm_state_glyph, 'exit', box=exit_coordinates)


def get_group_state_code(parent: QMTag, state: State, states: [State], printed_ids: [str]):
    """
    get code for qroup. uses recursion
    :param parent: xml data to add state code
    :param state: state to translate to code
    :param states: list of states
    :param printed_ids: list of printed states
    :return:
    """
    printed_ids.append(state.new_id)
    qm_state = etree.SubElement(parent, 'state', name=state.name)
    if state.entry:
        qm_entry = etree.SubElement(qm_state, 'entry')
        qm_entry.text = state.entry
    if state.exit:
        qm_exit = etree.SubElement(qm_state, 'exit')
        qm_exit.text = state.exit
    for trig in state.trigs:
        get_trig_code(qm_state, states, trig)
    for childstate in state.childs:
        if childstate.type == 'state':
            get_simple_state_code(qm_state, childstate, states, printed_ids)
        if childstate.type == 'group':
            get_group_state_code(qm_state, childstate, states, printed_ids)
    qm_state_glyph = etree.SubElement(qm_state, 'state_glyph',
                                      node="%i,%i,%i,%i" % (state.x, state.y, state.width, state.height))
    _ = etree.SubElement(qm_state_glyph, 'entry', box=entry_coordinates)
    _ = etree.SubElement(qm_state_glyph, 'exit', box=exit_coordinates)


def get_trig_code(qm_state: QMTag, states: [State], trig: Trigger):
    """
    functions adds qm tags for transition to xml tree
    :param qm_state: parent element for adding tags
    :param states: list of States
    :param trig: trigger to add
    :return:
    """
    if trig.type == "internal" and trig.guard != 'else':
        get_internal_trigger_code(trig, states, qm_state)
    if trig.type == "external":
        if not trig.guard or trig.guard == 'else':
            get_external_trigger_code(trig, states, qm_state)
        else:
            get_guard_trigger_code(trig, states, qm_state)
    if trig.type == "choice_start":
        get_choice_trigger_code(trig, states, qm_state)


def get_internal_trigger_code(trig: Trigger, states: [State], qm_state: QMTag):
    """
    gets qm code for internal trigger
    EXAMPLE
    <tran target="../../3" trig="GOT_REASON(id)">
        <tran_glyph conn="7,59,2,2,27,3">
            <action box="0,-2,15,2"/>
        </tran_glyph>
    </tran>
    :param trig: internal trigger
    :param states: list of States
    :param qm_state: tag of qm tree to add code to
    :return:
    """

    source_state: State = get_state_by_id(states, trig.source, "old")
    x: int = source_state.x
    delta: int = 2 if source_state.entry else 0
    if source_state.exit:
        delta += 2
    y: int = source_state.y + 4 * trig.id + delta
    qm_trig = etree.SubElement(qm_state, 'tran', trig=trig.name)
    qm_action = etree.SubElement(qm_trig, 'action')
    qm_action.text = trig.action
    qm_trig_glyph = etree.SubElement(qm_trig, 'tran_glyph',
                                     conn='%i,%i,%s' % (x, y, internal_trig_coordinates))
    _ = etree.SubElement(qm_trig_glyph, "action", box=trig_action_coordinates)


def get_external_trigger_code(trig: Trigger, states: [State], qm_state: QMTag):
    """
    creates qm code for external trigger
    get code for external trigger
    EXAMPLE
    <tran target="../../2" trig="GOT_REASON">
        <action>play_music()</action>
        <tran_glyph conn="51,17,2,2,5,-1,0,-35,8,2">
            <action box="-31,4,38,4"/>
        </tran_glyph>
    </tran>
    :param trig:
    :param states:
    :param qm_state:
    :return:
    """
    coordinates: List[int] = get_trig_coordinates(trig, states)
    action_coordinates: str = get_action_coordinates(trig)
    qm_trig = etree.SubElement(qm_state, 'tran', trig=trig.name, target="%s" %
                                                                        get_path(trig.source, trig.target, states))
    qm_action = etree.SubElement(qm_trig, 'action')
    qm_action.text = trig.action
    qm_trig_glyph = etree.SubElement(qm_trig, "tran_glyph", conn=coordinates)
    _ = etree.SubElement(qm_trig_glyph, "action", box=action_coordinates)


def get_guard_trigger_code(trig: Trigger, states: [State], qm_state: QMTag):
    """
    get qm code for triggers without else or with internal else
    Example
    <tran trig="GUARD_TRIG">
        <choice target="../../../../1/0">
         <guard>b == c</guard>
         <action>do this</action>
         <choice_glyph conn="38,31,5,3,4,-1,2">
          <action box="1,0,10,2"/>
         </choice_glyph>
        </choice>
        <tran_glyph conn="27,34,1,-1,11,-3">
         <action box="0,-2,10,2"/>
        </tran_glyph>
       </tran>
    :param trig:
    :param states:
    :param qm_state:
    :return:
    """
    coordinates: str = get_trig_coordinates(trig, states)
    action_coordinates: str = get_action_coordinates(trig)
    qm_trig = etree.SubElement(qm_state, 'tran', trig=trig.name)
    qm_choice = etree.SubElement(qm_trig, 'choice', target="../%s" % get_path(trig.source, trig.target, states))
    qm_guard = etree.SubElement(qm_choice, 'guard')
    qm_guard.text = trig.guard
    qm_action = etree.SubElement(qm_choice, 'action')
    qm_action.text = trig.action
    qm_choice_glyph = etree.SubElement(qm_choice, "choice_glyph", conn=coordinates)
    _ = etree.SubElement(qm_choice_glyph, "action", box=get_guard_coordinates(trig, 2))
    else_trig = get_else_trig(trig, states)
    if else_trig:
        qm_choice = etree.SubElement(qm_trig, 'choice')
        qm_guard = etree.SubElement(qm_choice, 'guard')
        qm_guard.text = 'else'
        qm_action = etree.SubElement(qm_choice, 'action')
        qm_action.text = else_trig.action
        qm_choice_glyph = etree.SubElement(qm_choice, "choice_glyph", conn=get_else_coordinates(coordinates))
        _ = etree.SubElement(qm_choice_glyph, "action", box=get_guard_coordinates(trig, 50))
    qm_tran_glyph = etree.SubElement(qm_trig, 'tran_glyph', conn=coordinates)
    _ = etree.SubElement(qm_tran_glyph, "action", box=action_coordinates)


def get_else_trig(trig: Trigger, states: [State]) -> Optional[Trigger]:
    """
    check if exists else part of choice trigger and gets this trigger
    :param trig: choice trigger
    :param states: list of states
    :return: else trigger of None
    """
    parent_state = get_state_by_id(states, trig.source, 'old')
    for child_trig in parent_state.trigs:
        if child_trig.guard == 'else' and child_trig.name == trig.name:
            return child_trig
    return None


def get_else_coordinates(coord_str: str) -> str:
    """
    :param coord_str: string with trigger coordinates
    :return: string with coordinates
    """
    coords: List[str] = coord_str.split(',')
    return "%s,%s,4,-1,-10" % (coords[0], coords[1])


def get_choice_trigger_code(trig: Trigger, states: [State], qm_state: QMTag):
    """
    get qm code for choice
    Example
    <tran trig="name">
        <choice target="../../../2">
            <guard>count == 0</guard>
            <action/>
            <choice_glyph conn="21,10,2,2,-2,36,22,0,2,-23">
                <action box="33,5,19,4"/>
            </choice_glyph>
        </choice>
        <choice target="../../../1">
            <guard>else</guard>
                <action/>
            <choice_glyph conn="21,10,2,2,10">
                <action box="-1,0,13,4"/>
            </choice_glyph>
        </choice>
        <tran_glyph conn="5,9,2,2,-1,5,0,7,2,4">
            <action box="0,0,10,4"/>
        </tran_glyph>
    </tran>
    :param trig: trigger that is choice_start
    :param states: list of states
    :param qm_state: element of xml tree to add code to
    :return:
    """
    coordinates: List[str] = get_trig_coordinates(trig, states)
    action_coordinates: str = get_action_coordinates(trig)
    qm_trig = etree.SubElement(qm_state, "tran", trig=trig.name)
    state_choice = get_state_by_id(states, trig.target, "old")

    for choice_trig in state_choice.trigs:
        qm_choice = etree.SubElement(qm_trig, "choice",
                                     target="../%s" % get_path(trig.source, choice_trig.target, states))
        qm_guard = etree.SubElement(qm_choice, "guard")
        guard = choice_trig.guard.replace("[", "")
        guard = guard.replace("]", "")
        qm_guard.text = guard
        qm_action = etree.SubElement(qm_choice, "action")
        qm_action.text = trig.action
        qm_choice_glyph = etree.SubElement(qm_choice, "choice_glyph", conn=get_trig_coordinates(choice_trig, states))
        _ = etree.SubElement(qm_choice_glyph, "action", box=get_action_coordinates(choice_trig))
    qm_trig_glyph = etree.SubElement(qm_trig, "tran_glyph", conn=coordinates)
    _ = etree.SubElement(qm_trig_glyph, 'action', box=action_coordinates)


def get_enum(text_labels: List[str]) -> str:
    """
    prepares list of signals for enum structure for c language: joins them into one string comma and \n-separated
    and adds _SIG to each signal
     Example:
        >>> get_enum(["EVENT1", "EVENT2"])
        "EVENT1_SIG,
         EVENT2_SIG"
    :param text_labels:
    :return: string
    """
    enum_labels: List[str] = [label + '_SIG' for label in text_labels]
    enum = ',\n'.join(enum_labels)
    enum = 'enum PlayerSignals {\nTICK_SEC_SIG = Q_USER_SIG,\n\n' + enum
    enum = enum + ',\n\nLAST_USER_SIG\n};'
    return enum


def update_ctor_fields(parameter: str, ctor_fields: dict):
    """
    function updates dictionary type:name of custom fields of constructor structure (empty by default)
    :param ctor_fields: dict for constructor parameters
    :param parameter: string with parameter
    :return:
    """
    if parameter:
        parameter: str = parameter.replace(";", "")
        data: List[str] = parameter.split()
        ctor_fields[data[-1]] = " ".join(data[:-1])
    return ctor_fields


def create_qm_constructor(qm_package: QMTag, Filename: str, filename: str, ctor_code: str, ctor_fields: dict):
    """
    creates qm code for constructor
    :param ctor_code: extra constructor code
    :param ctor_fields: dict with extra constructor fields
    :param qm_package: qm tag to add code below
    :param filename: filename of project
    :param Filename: filename with uppercase first letter
    :return:
    """
    qm_ctor = etree.SubElement(qm_package, "operation", name="%s_ctor" % Filename, type="void", visibility="0x00",
                               properties="0x00")
    for key in ctor_fields.keys():
        _ = etree.SubElement(qm_ctor, "parameter", name=key, type=ctor_fields[key])
    qm_code = etree.SubElement(qm_ctor, "code")
    qm_code.text = "%s *me = &%s;\n %s\nQHsm_ctor(&me->super, Q_STATE_CAST(&%s_initial));" % (Filename, filename,
                                                                                              ctor_code, Filename)


def create_qm_files(qm_model: QMTag, modelnames: [str], player_signal: [str], event_fields: dict, hcode: str,
                    cppcode: str):
    """
    creates qm code for files c and h
    :param hcode: code for hfile
    :param cppcode: code for cpp file
    :param modelnames: list of filenames
    :param qm_model: qm element to add code below
    :param player_signal: list of all trigger names
    :param event_fields: dict with new_event_fields
    :return:
    """
    modelnames: List[str] = [modelname[0].lower() + modelname[1:] for modelname in modelnames]
    Modelnames: List[str] = [Modelname[0].upper() + Modelname[1:] for Modelname in modelnames]
    name: str = '-'.join(modelnames)
    qm_directory = etree.SubElement(qm_model, "directory", name=".")
    qm_file = etree.SubElement(qm_directory, "file", name="%s.cpp" % name)
    qm_text = etree.SubElement(qm_file, "text")
    with open('templates/с_template') as t:
        include: str = "\n".join(["#include \"" + filename + ".h\"" for filename in modelnames])
        consts: str = ""
        for modelname in modelnames:
            consts += 'QHsm * const the_%s = (QHsm *) &%s; /* the opaque pointer */\n' % (modelname, modelname)
        constructors: str = ""
        for Modelname in Modelnames:
            constructors += "$define(SMs::%s_ctor)\n$define(SMs::%s)\n\n" % (Modelname, Modelname)
        c_code: str = Template(t.read()).substitute(
            {"include": include, "consts": consts, "constructors": constructors, "cppcode": cppcode})
    qm_text.text = c_code
    qm_file = etree.SubElement(qm_directory, "file", name="%s.h" % name)
    qm_text = etree.SubElement(qm_file, "text")
    with open("templates/h_template") as t:
        declare: str = ""
        for Modelname in Modelnames:
            modelname = Modelname[0].lower() + Modelname[1:]
            declare += "\n$declare(SMs::%s)\n\nstatic %s %s; /* the only instance of the %s class */\n\n" \
                       % (Modelname, Modelname, modelname, Modelname)
        declares = ""
        if modelnames:
            for modelname in modelnames:
                Modelname = modelname[0].upper() + modelname[1:]
                declares += "extern QHsm * const the_%s; /* opaque pointer to the %s HSM */\n\n$declare(SMs::%s_ctor)" \
                            % (modelname, modelname, Modelname)

            modelname = modelnames[0]
            h_code = Template(t.read()).substitute({"hcode": hcode, "declare": declare,
                                                    "declares": declares, "filename_h": name + "_h",
                                                    "event_struct": get_event_struct(event_fields, modelname),
                                                    "player_signals": get_enum(player_signal)})
            qm_text.text = h_code


def prepare_qm():
    qm_model = etree.Element('model', version="4.0.3")
    qm_doc = etree.SubElement(qm_model, 'documentation')
    qm_doc.text = documentation
    _ = etree.SubElement(qm_model, 'framework', name=framework)
    qm_package = etree.SubElement(qm_model, 'package', name=pack_name, stereotype=stereotype)
    return qm_model, qm_package


def create_qm(qm_package: QMTag, modelname: str, start_state: str, start_action: str,
              notes: List[Dict[str, Any]], states: List[State], coords: Tuple[int, int, int , int]) \
        -> Tuple[Dict[str, str], str, str, str, Dict[str, str]]:
    """
    function creates xml from list os states with trsnsitions using special rools and writes in to .qm file
    :param start_action: action for start node
    :param qm_package: tag to qm package
    :param modelname: name of resulting file
    :param start_state: start state id
    :param notes  is a node with start variables
    :param states: list of states
    :param coords: tuple with min and max coords
    :return: list of special event fields orgonized as dictionary, code for h and cpp files
    """
    modelname = modelname[0].lower() + modelname[1:]
    Modelname = modelname[0].upper() + modelname[1:]
    qm_class = etree.SubElement(qm_package, 'class', name=Modelname, superclass="%s::QHsm" % framework)
    qm_class_doc = etree.SubElement(qm_class, "documentation")
    event_fields: Dict[str, str] = dict()
    ctor_fields: Dict[str, str] = dict()
    hcode = ""
    cppcode = ""
    ctor_code = ""
    for note in notes:
        text = get_note_label(note)
        if text.startswith("State fields"):
            text = '\n'.join(text.split('\n')[1:])
            get_parameters_code(text, qm_class, qm_class_doc)
        if text.startswith("Event fields"):
            for line in text.split('\n')[1:]:
                update_event_fields(line, event_fields)
        if text.startswith("Code for h-file:"):
            hcode = '\n//Start of h code from diagram\n' + '\n'.join([s for s in text.split('\n')[1:] if s]) + \
                    '\n//End of h code from diagram\n'
        if text.startswith("Code for cpp-file:"):
            cppcode = '\n//Start of c code from diagram\n'+'\n'.join([s for s in text.split('\n')[1:] if s]) +\
                      "\n//End of c code from diagram\n"
        if text.startswith("Constructor code"):
            ctor_code = '\n'.join(text.split('\n')[1:])
        if text.startswith("Constructor fields"):
            for line in text.split('\n')[1:]:
                ctor_fields = update_ctor_fields(line, ctor_fields)
    qm_statechart = etree.SubElement(qm_class, 'statechart')
    start_state = get_state_by_id(states, start_state, 'old')
    x = start_state.x
    y = start_state.y
    get_initial_code(qm_statechart, start_state, start_action, y - 1, x - 2)
    printed_ids = []
    get_state_code(qm_statechart, states, printed_ids)
    _ = etree.SubElement(qm_statechart, 'state_diagram', size="%i,%i" %
                                                              ((coords[2] - coords[0]) // divider + 30,
                                                               (coords[3] - coords[1]) // divider + 40))
    return event_fields, hcode, cppcode, ctor_code, ctor_fields


def finish_qm(qm_model: QMTag, qm_package, filename: str, modelnames: [str], player_signal, event_fields: dict,
              hcode: str, cppcode: str, ctor_code: str, ctor_fields: dict):
    """
    creates final part of qm file
    :param filename: name of file
    :param ctor_fields:
    :param ctor_code:
    :param cppcode:
    :param hcode:
    :param qm_model:
    :param qm_package:
    :param modelnames:
    :param player_signal:
    :param event_fields:
    :return:
    """
    for modelname in modelnames:
        modelname = modelname[0].lower() + modelname[1:]
        Modelname = modelname[0].upper() + modelname[1:]
        create_qm_constructor(qm_package, Modelname, modelname, ctor_code, ctor_fields)
    create_qm_files(qm_model, modelnames, player_signal, event_fields, hcode, cppcode)
    xml_tree = etree.ElementTree(qm_model)
    xml_tree.write('%s.qm' % filename, xml_declaration=True, encoding="UTF-8", pretty_print=True)
