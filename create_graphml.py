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


prepare_dict = {'d0': {'attr.name':"Description", 'attr.type':"string", 'for':'port'},
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

graph_dict = {'edgedefault':'directed', 'id': 'G'}


def prepare_graphml() -> etree._Element:
    """
    prepares graphml tag with parameters and all tags before graph tag
    :return:
    """
    attr_qname = etree.QName(scheme_loc, "schemaLocation")
    graphml_root = etree.Element("graphml",
                                 {attr_qname: scheme},
                                 nsmap=namespace_dict)
    for key in prepare_dict.keys():
        _ = etree.SubElement(graphml_root, 'key', id=key, **prepare_dict[key])
    return graphml_root

def create_graph(root: etree._Element) -> etree._Element:
    """
    adds graph tag to root
    :param root:
    :return:
    """
    graph = etree.SubElement(root, 'graph', **graph_dict)
    _ = etree.SubElement(graph, 'data', key='d0')
    return graph

def add_simple_node()

root = prepare_graphml()
create_graph(root)
xml_tree = etree.ElementTree(root)
xml_tree.write("test.graphml", xml_declaration=True, encoding="UTF-8")
