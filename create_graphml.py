from lxml import etree

namespace_dict = {None: "http://graphml.graphdrawing.org/xmlns",
                  'java': "http://www.yworks.com/xml/yfiles-common/1.0/java",
                  'sys': "http://www.yworks.com/xml/yfiles-common/markup/primitives/2.0",
                  'x': "http://www.yworks.com/xml/yfiles-common/markup/2.0",
                  'xsi': "http://www.w3.org/2001/XMLSchema-instance",
                  'y': "http://www.yworks.com/xml/graphml",
                  'yed': "http://www.yworks.com/xml/yed/3"}

scheme = "http://graphml.graphdrawing.org/xmlns http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd"
scheme_loc = "http://www.w3.org/2001/XMLSchema-instance"


prepare_dict = {'d0': {'attr.name':"Description", 'attr.type':"string", 'for':'graph'},
                'd1': {'for': 'port', 'yfiles.type' : 'portgraphics'},
                'd2': {'for': 'port', 'yfiles.type' : 'portgeometry'},
                'd3': {'for': 'port', 'yfiles.type': 'portuserdata'},
                'd4': {'attr.name':"url", 'attr.type':"string", 'for':'node'},
                'd5': {'attr.name':"description", 'attr.type':"string", 'for':'node'},
                'd6': {'for': 'node', 'yfiles.type': 'nodegraphics'},
                'd7': {'for': 'graphml', 'yfiles.type': 'resources'},
                'd8': {'attr.name': "url", 'attr.type': "string", 'for': 'edge'},
                'd9': {'attr.name': "description", 'attr.type': "string", 'for': 'edge'},
                'd10': {'for': 'edge', 'yfiles.type': 'edgegraphics'},
                }

graph_dict = {'edgedefault':'directed',
              'id': 'G'}

simple_node_color_dict = {'color': '#E8EEF7',
                          'color2' :' #B7C9E3',
                          'transparent' : "false"}

configuration = 'com.yworks.entityRelationship.big_entity'

node_border_dict = {'color' : "#000000",
                    'type':"line",
                    'width' : "1.0"}

node_label_dict = {'alignment': 'center',
             'autoSizePolicy': "node_width",
             'backgroundColor': "#B7C9E3",
             'configuration': 'com.yworks.entityRelationship.label.name',
             'fontFamily': 'Consolas',
             'fontSize': '12',
             'fontStyle': 'bold',
             'hasLineColor': 'false',
             'height': '18.7',
             'horizontalTextPosition':'center',
             'iconTextGap': '4',
             'modelName': 'internal',
             'modelPosition':'t',
             'textColor': "#000000",
             "verticalTextPosition": 'bottom',
             'visible': 'true',
             'width':'200',
             'x': '0.0',
             'y': '4.0'}

node_content_dict = {'alignment': 'left',
             'autoSizePolicy': 'content',
             'BackgroundColor': "false",
             'configuration': 'com.yworks.entityRelationship.label.attributes',
             'fontFamily': 'Consolas',
             'fontSize': '12',
             'fontStyle': 'plane',
             'hasLineColor': 'false',
             'height': '40',
             'horizontalTextPosition':'center',
             'iconTextGap': '4',
             'modelName': 'internal',
             'modelPosition':'tl',
             'textColor': "#000000",
             "verticalTextPosition": 'bottom',
             'visible': 'true',
             'width':'43.5',
             'x': '0.0',
             'y': '4.0'}

style1_dict = {'class':"java.lang.Boolean",
               "name":"y.view.ShadowNodePainter.SHADOW_PAINTING",
               "value":"true"}

style2_dict = {'class':"java.lang.Boolean",
               "name":"doubleBorder",
               "value":"false"}

def prepare_graphml() -> etree._Element:
    """
    prepares graphml tag with parameters and all tags before graph tag
    :return: root element
    """
    attr_qname = etree.QName(scheme_loc, "schemaLocation")
    graphml_root = etree.Element("graphml",
                                 {attr_qname: scheme},
                                 nsmap=namespace_dict)
    for key in prepare_dict.keys():
        _ = etree.SubElement(graphml_root, 'key', id=key, **prepare_dict[key])
    return graphml_root

def create_graph(tree_root: etree._Element) -> etree._Element:
    """
    adds graph tag to root
    :param tree_root: root element of graphml
    :return: graph element
    """
    graph_node = etree.SubElement(tree_root, 'graph', **graph_dict)
    _ = etree.SubElement(graph_node, 'data', key='d0')
    return graph_node

def add_simple_node(parent: etree._Element, node_text: str, content: str, node_id: int,
                    h: int, w: int, x0: float, y0: float):
    """
    creates simple node with parameters
    :param parent:
    :param node_text: node labes
    :param content: node content
    :param node_id: node id
    :param h: height
    :param w: width
    :param x0: x of left upper cornet
    :param y0: y of lest upper cornet
    :return:
    """
    node = etree.SubElement(parent, "node", id="n%i" % node_id)

    data = etree.SubElement(node, "data", key="d4")
    data.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    data_full = etree.SubElement(node, "data", key="d6")
    nmspc_y = namespace_dict['y']

    generic_node = etree.SubElement(data_full, etree.QName(nmspc_y, "GenericNode"), configuration=configuration)
    _ = etree.SubElement(generic_node,  etree.QName(nmspc_y, "Geometry"),
                                height=str(h), width=str(w), x=str(x0), y=str(y0))
    _ = etree.SubElement(generic_node, etree.QName(nmspc_y, 'Fill'), **simple_node_color_dict)
    _ = etree.SubElement(generic_node, etree.QName(nmspc_y, 'BorderStyle'), **node_border_dict)

    nodelabel = etree.SubElement(generic_node, etree.QName(nmspc_y, 'NodeLabel'), **node_label_dict)
    nodelabel.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    nodelabel.text = node_text

    nodecontent = etree.SubElement(generic_node, etree.QName(nmspc_y, 'NodeLabel'), **node_content_dict)
    nodecontent.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    nodecontent.text = content

    nodestyle = etree.SubElement(generic_node, etree.QName(nmspc_y, 'StyleProperties'))
    _ = etree.SubElement(nodestyle, etree.QName(nmspc_y, 'Property'), **style1_dict)
    _ = etree.SubElement(nodestyle, etree.QName(nmspc_y, 'Property'), **style2_dict)


def finish_graphml(root: etree._Element):
    """
    creates finish tag
    :param root: root node
    :return:
    """
    data = etree.SubElement(root, 'data', key='d7')
    _ = etree.SubElement(data, etree.QName(namespace_dict['y'], 'Resources'))


if '__name__' == '__main__':
    root_node = prepare_graphml()
    graph = create_graph(root_node)
    add_simple_node(graph, 'idle', '\n\nlorem ipsum', 0, 100, 200, 259, 255)
    add_simple_node(graph, 'not_idle', '\n\nlorem ipsum', 1, 100, 200, 609, 250)

    finish_graphml(root_node)
    xml_tree = etree.ElementTree(root_node)
    xml_tree.write("test.graphml", xml_declaration=True, encoding="UTF-8")
