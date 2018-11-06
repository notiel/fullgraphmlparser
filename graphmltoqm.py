import xmltodict
import qm
import graphml as gr
import create_qm as cr
from logger import logging
import sys


def main(filenames):


    #filenames = ['ka-tet', 'prioritizer2', 'location', 'emotion', 'dogan_ligt', 'reason_handler', 'dogan1',
     #            'lightsaber']
    #filenames = ["ka_tet_counter", "ka_tet", "character"]

    qm_model, qm_package = cr.prepare_qm()
    player_signal=[]

    for filename in filenames:

        try:
            data = xmltodict.parse(open(filename + '.graphml').read())
        except FileNotFoundError:
            logging.error('File %s.graphml does not exist' % filename)
            continue

        #get nodes from file
        flat_nodes = gr.get_flat_nodes(data)
        state_nodes = [node for node in flat_nodes if
                       gr.is_node_a_state(node) or gr.is_node_a_choice(node) or gr.is_node_a_group(node)]
        gr.update_qroup_nodes(state_nodes)
        state_nodes.sort(key=gr.coord_sort)

        coords = gr.get_minmax_coord(state_nodes)      #get min and max coord and height and widt of scheme
        #create states from nodes and add internal triggers to list of signals
        qm_states, player_signal = qm.create_states_from_nodes(state_nodes, coords, player_signal)
        #get edges for external triggers
        flat_edges = gr.get_flat_edges(data)
        try:
            start, start_node, start_action = gr.get_start_node_data(flat_nodes, flat_edges)
        except ValueError:
            logging.error('UML-diagram %s.graphml does not have start node' % filename)
            continue

        #add external trigger and update list of signals with them
        player_signal = qm.update_states_with_edges(qm_states, flat_edges, start, player_signal, coords[0], coords[1])
        #get notes
        notes = [node for node in flat_nodes if gr.is_node_a_note(node)]
        #create qm data
        event_fields = cr.create_qm(qm_package, filename, start_node, start_action, notes, qm_states, coords, player_signal)
    #create file with final code
    try:
        cr.finish_qm(qm_model, qm_package, filenames, player_signal, event_fields)
    except PermissionError:
        logging.fatal("File already exists and is locked")

if __name__ == '__main__':
    main(sys.argv[1:])
