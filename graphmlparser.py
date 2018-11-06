"""
graphml.py is a technical module for getting xml structure from graphml
it contains functions for analyze and transform data in .graphml file
-flatten(mixed data, key) -                                            flattens mixed_data list using key
-flatten_with_key(mixed_data: list, key: str, newkeys: dict) -> list   flattens data nodes using key
                                                                       adding new dict keys from newkeys
-get_flat_nodes(data: dict)->[dict]:                                   gets list of flattened nodes from data dict
-get_sub_nodes(nodes: list) -> list:                                   gets all sub-nodes from groupnodes
-update_group_nodes(nodes: list)                                       gets all levels of group nodes
-is_node_a_choice(node: dict) -> bool                                  detects if node in graphml file is a choice
-is_node_a_state(node: dict) -> bool                                   detects if node in graphml file is a state
-is_node_a_group(node:dict) -> bool                                    detects if node in graphml is group node
-get_state_label(data: dict) -> str                                    gets state label from state node
-get_group_label(data: dict)-> str:                                    gets group node label from node data
-get_state_actions(data: dict) -> str                                  gets actions for state as a single string
-def get_group_actions(data: dict) -> str:                             get label with actions from group node data
-get_flat_edges(data: dict)->[dict]:                                   gets list of flattened edges from data dict
-is_edge_correct(edge: dict, edge_type: str) -> bool                   checks if edge is correct
-get_start_node_action(nodes: [dict], edges: [dict]) -> int, str       get id of a start node and initial action
"""

from logger import logging


def flatten(mixed_data: list, key: str) -> list:
    """
    function separates data nodes using key
    Example:
        >>>flatten([{'data':[info1, info2]}], 'data')
        [info1, info2]
    :param mixed_data: list of nodes with data
    :param key: dictionary key to get list with data
    :return: list with data items
    """
    flat_data = []
    for node in mixed_data:
        if isinstance(node, dict) and key in node.keys():
            node_data = node[key]
            if isinstance(node_data, dict):
                flat_data.append(node_data)
            else:
                for e in node_data:
                    flat_data.append(e)
    return flat_data


def flatten_with_key(mixed_data: list, key: str, newkeys: dict) -> list:
    """
    function separates data nodes using key adding new dict keys from newkeys
    Example:
        >>>flatten_with_key([{'data' : [info1, info2]}, 'id':1, 'test':'value'], 'data', {'id':'number', 'test':'data'})
        [{info1, 'number':1, 'data':'value'}, {info2, 'number':1, 'data':'value'}]
    :param mixed_data: list of nodes with data
    :param key: dictionary key to get list with data
    :param newkeys: key for additional data to extract
    :return: list with data items
    """
    flat_data = []
    for node in mixed_data:
        if isinstance(node, dict) and key in node.keys():
            node_data = node[key]
            if isinstance(node_data, dict):
                for k in newkeys.keys():
                    node_data.update([(newkeys[k], node[k])])
                flat_data.append(node_data)
            else:
                for e in node_data:
                    for k in newkeys.keys():
                        e.update([(newkeys[k], node[k])])
                    flat_data.append(e)
    return flat_data


def get_sub_nodes(nodes: list) -> list:
    """
    gets all sub-nodes from groupnodes (detects in node has subnodes (has "graph' key) and gets all nodes in node['graph']
    item, flattened by node and by data fields
    :param nodes: list of nodes
    :return: list of nodes
    """
    group_nodes = [node for node in nodes if '@yfiles.foldertype' in node.keys()]
    res = []
    while group_nodes:
        new = [node['graph'] for node in group_nodes]
        new = flatten(new, 'node')
        res.extend(new)
        group_nodes = [node for node in new if '@yfiles.foldertype' in node.keys()]
    return res


def update_qroup_nodes(data: [dict]):
    """
    gets all levels of group nodes
    :param data:
    :return:
    """
    for node in data:
        if is_node_a_group(node):
            group_nodes = node['y:ProxyAutoBoundsNode']['y:Realizers']['y:GroupNode']
            if isinstance(group_nodes, list):
                for group_node in group_nodes:
                    if group_node['y:State']['@closed'] == 'false':
                        correct = group_node
                node['y:ProxyAutoBoundsNode']['y:Realizers']['y:GroupNode'] = correct


def get_flat_nodes(data: dict) -> [dict]:
    """
    gets list of flattened nodes from data dictg
    :param data: dict with data
    :return: list of nodes
    """
    nodes = data['graphml']['graph']['node']
    if isinstance(nodes, dict):
        nodes = [nodes]
    nodes.extend(get_sub_nodes(nodes))
    nodes = flatten_with_key(nodes, 'data', {'@id': 'id'})
    return nodes


def is_node_a_choice(node: dict) -> bool:
    """
    detects if node is a choice (using @configuration key)
    :param node: dict with node
    :return: true if state otherwise false
    """
    try:
        if node['y:GenericNode']['@configuration'] == "com.yworks.bpmn.Gateway.withShadow":
            return True
    except KeyError:
        return False
    return False


def is_node_a_state(node: dict) -> bool:
    """
    detects if node is a state (using @configuration key)
    :param node: dict with node
    :return: true if state otherwise false
    """
    try:
        if node['y:GenericNode']['@configuration'] == "com.yworks.entityRelationship.big_entity":
            return True
    except KeyError:
        return False
    return False


def is_node_a_group(node: dict) -> bool:
    """
    detects if node if group node
    :param node: dict with node
    :return: true if group else false
    """
    if 'y:ProxyAutoBoundsNode' in node.keys():
        return True
    return False


def get_state_label(data: dict) -> str:
    """
    gets state label from node data
    :param data: dict with data
    :return: string with label
    """
    node_id = data['id']
    try:
        data = data['y:GenericNode']['y:NodeLabel']
    except KeyError:
        logging.warning("Cannot retrieve state name %s" % data['id'])
    if not isinstance(data, list):
        data = [data]
    for label in data:
        if "#text" in label.keys() and '@configuration' in label.keys():
            if label['@configuration'] == 'com.yworks.entityRelationship.label.name':
                return label['#text']
    logging.warning("Cannot retrieve state name %s" % node_id)
    return ""


def get_group_label(data: dict) -> str:
    """
    gets group node label from node data
    :param data: dict with data
    :return: string with label
    """
    node_id = data['id']
    try:
        data = data['y:ProxyAutoBoundsNode']['y:Realizers']['y:GroupNode']
    except KeyError:
        logging.warning("Cannot retrieve group name %s" % data['id'])
        return ""
    data = flatten([data], 'y:NodeLabel')
    for label in data:
        if "#text" in label.keys() and '@modelName' in label.keys():
            if label['@modelName'] == 'internal':
                return label['#text']
    logging.warning("Cannot retrieve group name %s" % node_id)
    return ""


def get_state_actions(data: dict) -> str:
    """
    get label with actions from node data
    :param data: node with data
    :return: str with actions
    """
    try:
        data = data['y:GenericNode']
    except KeyError:
        logging.warning("Cannot retrieve state actions %s" % data['id'])
    data = flatten([data], 'y:NodeLabel')
    for label in data:
        if "#text" in label.keys() and '@configuration' in label.keys():
            if label['@configuration'] == 'com.yworks.entityRelationship.label.attributes':
                return label['#text']
    return ""


def get_group_actions(data: dict) -> str:
    """
        get label with actions from group node data
        :param data: node with data
        :return: str with actions
        """
    try:
        data = data['y:ProxyAutoBoundsNode']['y:Realizers']['y:GroupNode']
    except KeyError:
        logging.warning("Cannot retrieve group actions %s" % data['id'])
        return ""
    data = flatten([data], 'y:NodeLabel')
    for label in data:
        if "#text" in label.keys() and '@modelName' in label.keys():
            if label['@modelName'] == 'custom':
                return label['#text']
            if label['@alignment'] == 'left':
                return label['#text']
    return ""


def get_flat_edges(data: dict) -> [dict]:
    """
    gets list of transitions from data dict
    :param data: dict with data
    :return: list of transitions
    """
    edges = data['graphml']['graph']['edge']
    flattened_edges = flatten_with_key(edges, 'data', {'@source': 'source', '@target': 'target'})
    return flattened_edges


def is_edge_correct(edge: dict, edge_type: str) -> bool:
    """
    checks if edge contains all necessary data to be a correct edge with label
    :param edge: dict with edge data
    :param edge_type: type of edge:generic or curve
    :return: true if edge is generic false otherwise
    """
    if edge_type not in edge.keys():
        return False
    if 'y:EdgeLabel' not in edge[edge_type].keys():
        return False
    return True


def get_start_node_action(nodes: [dict], edges) -> (int, str):
    """functions gets start node id (target of start edge) and raises exception if no start node found
    :param nodes: list of nodes
    :param edges: list of edges
    :return: initial trigger action and its id
    """
    node_id = ""
    for node in nodes:
        if 'y:GenericNode' in node.keys() and '@configuration' in node['y:GenericNode'].keys():
            if node['y:GenericNode']['@configuration'] == 'com.yworks.bpmn.Event.withShadow':
                node_id = node['id']
    if not node_id:
        raise ValueError
    for edge in edges:
        if edge['source'] == node_id:
            if is_edge_correct(edge, "y:GenericEdge") and "#text" in edge['y:GenericEdge']['y:EdgeLabel'].keys():
                return node_id, edge['y:GenericEdge']['y:EdgeLabel']["#text"]
            return None, ""
    raise ValueError  # raise exception of no start node found
