"""
graphml.py is a technical module for .graphml->.qm transator
it contains functions for analyze and transform data in .graphml file
-flatten(mixed data, key) -                                            flattens mixed_data list using key
-flatten_with_key(mixed_data: list, key: str, newkeys: dict) -> list   flattens data nodes using key
                                                                       adding new dict keys from newkeys
-get_flat_nodes(data: dict)->[dict]:                                   gets list of flattened nodes from data dict
-get_flat_edges(data: dict)->[dict]:                                   gets list of flattened edges from data dict
-get_sub_nodes(nodes: list) -> list:                                   gets all sub-nodes from groupnodes
-get_start_node_id(nodes: [dict]) -> int                               get id of a start node
-is_node_a_choice(node: dict) -> bool                                  detects if node in graphml file is a choice
-is_node_a_state(node: dict) -> bool                                   detects if node in graphml file is a state
-get_coordinates(node: dict) -> tuple                                  gets x, y, width and height of a node
-get_minmax_coord(nodes: [node]) -> tuple                              function gets the smallest/biggest x and y coord
-get_state_actions(data: dict) -> str                                  gets actions for state as a single string
-def get_group_actions(data: dict) -> str:                             get label with actions from group node data
-get_state_label(data: dict) -> str                                    gets state label from state node
-get_group_label(data: dict)-> str:                                    gets group node label from node data
-is_edge_correct(edge: dict, edge_type: str) -> bool                   checks if edge is correct
-def get_edge_coordinates(edge: dict) -> tuple                         function get edge coordinates (start as a shift from
                                                                       source state center, enf as a shift from source state
                                                                       center)
-def get_edge_label_coordinates(edge: dict) -> tuple:                  gets coordinates for edge label
"""

edgetype = 'y:PolyLineEdge'


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


def update_qroup_nodes(data: [dict]):
    """

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

def get_flat_edges(data: dict) -> [dict]:
    """
    gets list of transitions from data dict
    :param data: dict with data
    :return: list of transitions
    """
    edges = data['graphml']['graph']['edge']
    flattened_edges = flatten_with_key(edges, 'data', {'@source': 'source', '@target': 'target'})
    return flattened_edges


def get_start_node_data(nodes: [dict], edges) -> tuple:
    """functions gets start node id (target of start edge) and raises exception if no start node found
    :param nodes: list of nodes
    :param edges: list of edges
    :return: id of start node, target of initial trigger, initial trigger action
    """
    node_id = 0
    for node in nodes:
        if 'y:GenericNode' in node.keys() and '@configuration' in node['y:GenericNode'].keys():
            if node['y:GenericNode']['@configuration'] == 'com.yworks.bpmn.Event.withShadow':
                node_id = node['id']
    for edge in edges:
        if edge['source'] == node_id and len(edge.keys()) > 3:
            if is_edge_correct(edge, edgetype) and "#text" in edge[edgetype]['y:EdgeLabel'].keys():
                action = edge[edgetype]['y:EdgeLabel']["#text"]
            else:
                action = ""
            return node_id, edge['target'], action
    raise ValueError                   #raise exception of no start node found


def is_node_a_choice(node: dict) -> bool:
    """
    detects if node is a choice (using @configuration key)
    :param node: dict with node
    :return: true if state otherwise false
    """
    if 'y:GenericNode' in node.keys() and '@configuration' in node['y:GenericNode'].keys():
        if node['y:GenericNode']['@configuration'] == "com.yworks.bpmn.Gateway.withShadow":
            return True
    return False



def is_node_a_state(node: dict) -> bool:
    """
    detects if node is a state (using @configuration key)
    :param node: dict with node
    :return: true if state otherwise false
    """
    if 'y:GenericNode' in node.keys() and '@configuration' in node['y:GenericNode'].keys():
        if node['y:GenericNode']['@configuration'] == "com.yworks.entityRelationship.big_entity":
            return True
    return False


def is_node_a_note(node: dict) -> bool:
    """
    detects is node contains start variables
    :param node: dict with node
    :return: true if start variables else false
    """
    if 'y:UMLNoteNode' in node.keys() and 'y:NodeLabel' in node['y:UMLNoteNode'].keys():
        if "#text" in node['y:UMLNoteNode']['y:NodeLabel'].keys():
            return True
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


def get_note_label(node: dict) -> str:
    """
    gets note_label data
    :param node:
    :return:
    """
    return node['y:UMLNoteNode']['y:NodeLabel']["#text"]


def get_coordinates(node: dict) -> tuple:
    """
    function to get node coordinates
    :param node: node with data
    :return: (x, y, width, height)
    """
    if 'y:GenericNode' not in node.keys() and 'y:ProxyAutoBoundsNode' not in node.keys():
        return 0, 0, 0, 0
    node = node['y:GenericNode'] if 'y:GenericNode' in node.keys() else node['y:ProxyAutoBoundsNode']['y:Realizers'][
        'y:GroupNode']
    if 'y:Geometry' not in node.keys():
        return 0, 0, 0, 0
    node = node['y:Geometry']
    x = int(float(node['@x']))
    y = int(float(node['@y']))
    width = int(float(node['@width']))
    height = int(float(node['@height']))
    return x, y, width, height


def coord_sort(node: dict) -> float:
    """
    function for sorting nodes by x
    :param node: dict with node data
    :return: x coordinates
    """
    x, _, _, _ = get_coordinates(node)
    return x


def get_minmax_coord(nodes: [dict]) -> tuple:
    """
    function gets the smallest x and y coordinate for nodes to make shift or coordinate system
    :param nodes: list of nodes
    :return: (min x, min y)
    """
    min_x, min_y, max_x, max_y = 0, 0, 0, 0
    for node in nodes:
        if 'y:GenericNode' in node.keys() or ('y:ProxyAutoBoundsNode' in node.keys() and 'y:Realizers' in node['y:ProxyAutoBoundsNode'].keys() and 'y:GroupNode' in node['y:ProxyAutoBoundsNode']['y:Realizers'].keys()):
            temp_node = node['y:GenericNode'] if 'y:GenericNode' in node.keys() else node['y:ProxyAutoBoundsNode']['y:Realizers']['y:GroupNode']
            temp_node = temp_node['y:Geometry']
            x = int(float(temp_node['@x']))
            y = int(float(temp_node['@y']))
            w = int(float(temp_node['@width']))
            h = int(float(temp_node['@height']))
            min_x = min([min_x, x])
            min_y = min([min_y, y])
            max_x = max([max_x, x + w])
            max_y = max([max_y, y + h])
    return min_x - 1, min_y - 1, max_x + 1, max_y + 1


def get_state_actions(data: dict) -> str:
    """
    get label with actions from node data
    :param data: node with data
    :return: str with actions
    """
    if 'y:GenericNode' not in data.keys() or 'y:NodeLabel' not in data['y:GenericNode'].keys():
        return ""
    data = data['y:GenericNode']
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
    if 'y:ProxyAutoBoundsNode' not in data.keys():
        return ""
    data = data['y:ProxyAutoBoundsNode']
    if 'y:Realizers' not in data.keys():
        return ""
    data = data['y:Realizers']
    if 'y:GroupNode' not in data.keys():
        return ""
    data = data['y:GroupNode']
    data = flatten([data], 'y:NodeLabel')
    for label in data:
        if "#text" in label.keys() and '@modelName' in label.keys():
            if label['@modelName'] == 'custom':
                return label['#text']
            if label['@alignment'] == 'left':
                return label['#text']
    return ""


def get_state_label(data: dict) -> str:
    """
    gets state label from node data
    :param data: dict with data
    :return: string with label
    """
    if 'y:GenericNode' not in data.keys() or 'y:NodeLabel' not in data['y:GenericNode'].keys():
        return ""
    data = data['y:GenericNode']
    data = flatten([data], 'y:NodeLabel')
    for label in data:
        if "#text" in label.keys() and '@configuration' in label.keys():
            if label['@configuration'] == 'com.yworks.entityRelationship.label.name':
                return label['#text']
    return ""


def get_group_label(data: dict) -> str:
    """
    gets group node label from node data
    :param data: dict with data
    :return: string with label
    """
    if 'y:ProxyAutoBoundsNode' not in data.keys():
        return ""
    data = data['y:ProxyAutoBoundsNode']
    if 'y:Realizers' not in data.keys():
        return ""
    data = data['y:Realizers']
    if 'y:GroupNode' not in data.keys():
        return ""
    data = data['y:GroupNode']
    data = flatten([data], 'y:NodeLabel')
    for label in data:
        if "#text" in label.keys() and '@modelName' in label.keys():
            if label['@modelName'] == 'internal':
                return label['#text']
    return ""


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


def get_edge_coordinates(edge: dict) -> tuple:
    """
    function get edge coordinates (start as a shift from source state center, enf as a shift from source state center,
    points coordinates between them (as int)
    :param edge: dict with edge data
    :return: (first_x, first_y, last_dx, last_dy, points)
    """
    coordinates = edge[edgetype]['y:Path']
    x = int(float(coordinates['@sx']))
    y = int(float(coordinates['@sy']))
    last_dx = int(float(coordinates['@tx']))
    last_dy = int(float(coordinates['@ty']))
    points = []
    if 'y:Point' in coordinates.keys():
        coordinates = [coordinates['y:Point']] if isinstance(coordinates['y:Point'], dict) else coordinates['y:Point']
        points = [(int(float(point['@x'])), int(float(point['@y']))) for point in coordinates]
    return x, y, last_dx, last_dy, points


def get_edge_label_coordinates(edge: dict) -> tuple:
    """
    gets coordinates for edge label
    :param edge: dict with edge data
    :return: x, y, width of edge coordinates
    """
    if is_edge_correct(edge, edgetype):
        label = edge[edgetype]['y:EdgeLabel']
        return int(float(label['@x'])), int(float(label['@y'])), int (float(label['@width']))
    else:
        return 0, 0, 0
