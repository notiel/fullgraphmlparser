import sys
import xmltodict
from logger import logging
import graphmlparser as gr
import makexml


def main(filenames):
    for filename in filenames:
        try:
            data = xmltodict.parse(open(filename + '.graphml').read())
        except FileNotFoundError:
            logging.error('File %s.graphml does not exist' % filename)
            continue
        flat_nodes = gr.get_flat_nodes(data)
        state_nodes = [node for node in flat_nodes if
                       gr.is_node_a_state(node) or gr.is_node_a_choice(node) or gr.is_node_a_group(node)]
        gr.update_qroup_nodes(state_nodes)
        states = makexml.create_states_from_nodes(state_nodes)
        flat_edges = gr.get_flat_edges(data)
        try:
            start, start_action = gr.get_start_node_action(flat_nodes, flat_edges)
        except ValueError:
            logging.error('UML-diagram %s.graphml does not have start node' % filename)
            continue
        makexml.update_states_with_edges(states, flat_edges, start)
        makexml.createxml(filename, states, start_action)


if __name__ == '__main__':
    main(sys.argv[1:])

