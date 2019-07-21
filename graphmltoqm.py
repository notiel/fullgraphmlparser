import xmltodict
import qm
import graphml as gr
import create_qm as cr
import service_files
from logger import logging
import sys
import os
from typing import Union, List


def get_states_from_graphml(filename: str):
    """
    creates state list
    :return:
    """
    try:
        data = xmltodict.parse(open(filename + '.graphml').read())
    except FileNotFoundError:
        logging.error('File %s.graphml does not exist' % filename)
        return list()
    # get nodes from file
    flat_nodes = gr.get_flat_nodes(data)
    state_nodes = [node for node in flat_nodes if
                   gr.is_node_a_state(node) or gr.is_node_a_choice(node) or gr.is_node_a_group(node)]
    state_nodes.sort(key=lambda st: len(st['id']))
    gr.update_qroup_nodes(state_nodes)
    state_nodes.sort(key=gr.coord_sort)
    coords = gr.get_minmax_coord(state_nodes)  # get min and max coord and height and widt of scheme
    # create states from nodes and add internal triggers to list of signals and all functions to function list
    qm_states, player_signal = qm.create_states_from_nodes(state_nodes, coords, [], [])
    # get edges for external triggers
    flat_edges = gr.get_flat_edges(data)
    try:
        start, start_node, start_action = gr.get_start_node_data(flat_nodes, flat_edges)
    except ValueError:
        logging.error('UML-diagram %s.graphml does not have start node' % filename)
        return list()
    # add external trigger and update list of signals with them
    player_signal = qm.update_states_with_edges(qm_states, flat_edges, start, player_signal, coords[0], coords[1])
    # get notes
    notes = [node for node in flat_nodes if gr.is_node_a_note(node)]
    return qm_states


def main(filenames: Union[List[str], str]):

    qm_model, qm_package = cr.prepare_qm()
    player_signal = list()
    event_fields = dict()
    ctor_fields = dict()
    ctor_code = ""
    cppcode = ""
    hcode = ""
    if not isinstance(filenames, list):
        filenames = [filenames]
    modelnames: List[str] = list()
    for filename in filenames:
        try:
            data = xmltodict.parse(open(filename + '.graphml').read())
            modelname = os.path.basename(filename)
            modelname = modelname[0].lower() + modelname[1:]
            modelnames.append(modelname)
        except FileNotFoundError:
            logging.error('File %s.graphml does not exist' % filename)
            continue
        # get nodes from file
        flat_nodes = gr.get_flat_nodes(data)
        state_nodes = [node for node in flat_nodes if
                       gr.is_node_a_state(node) or gr.is_node_a_choice(node) or gr.is_node_a_group(node)]
        state_nodes.sort(key=lambda st : len(st['id']))
        gr.update_qroup_nodes(state_nodes)
        state_nodes.sort(key=gr.coord_sort)

        coords = gr.get_minmax_coord(state_nodes)      # get min and max coord and height and widt of scheme
        # create states from nodes and add internal triggers to list of signals and all functions to function list
        functions: List[str] = list()
        qm_states, player_signal = qm.create_states_from_nodes(state_nodes, coords, player_signal, functions)
        # get edges for external triggers
        flat_edges = gr.get_flat_edges(data)
        try:
            start, start_node, start_action = gr.get_start_node_data(flat_nodes, flat_edges)
        except ValueError:
            logging.error('UML-diagram %s.graphml does not have start node' % filename)
            continue
        # add external trigger and update list of signals with them
        player_signal = qm.update_states_with_edges(qm_states, flat_edges, start, player_signal, coords[0], coords[1])
        # get notes
        notes = [node for node in flat_nodes if gr.is_node_a_note(node)]
        # create qm data
        event_fields, hcode, cppcode, ctor_code, ctor_fields = cr.create_qm(qm_package, modelname, start_node,
                                                                            start_action, notes, qm_states,
                                                                            coords)
    # create file with final code
    try:
        cr.finish_qm(qm_model, qm_package, filenames[0], modelnames, player_signal, event_fields, hcode, cppcode,
                     ctor_code, ctor_fields)
    except PermissionError:
        logging.fatal("File already exists and is locked")
    service_files.create_files(os.path.dirname(filenames[0]), player_signal, modelname, functions)


if __name__ == '__main__':
    # states = get_states_from_graphml(sys.argv[1:][0])
    main(sys.argv[1:])
