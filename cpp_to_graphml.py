import os
import sys
from dataclasses import dataclass

import clang.cindex
from lxml import etree

import create_graphml

try:
    clang_index = clang.cindex.Index.create()
except:
    # Hack to support linux (e.g. Travis)
    clang.cindex.Config.set_library_file('/usr/lib/llvm-8/lib/libclang.so.1')
    clang_index = clang.cindex.Index.create()

# Зависимости:
# - clang/llvm
#   Можно установить через 'choco install llvm'.
# - clang python bindings
#   Можно установить через 'pip install clang'.
#
# Запуск:
#   py -3 cpp_to_graphml.py <путь к cpp-файлу диаграммы>

class ParsingContext:
    state_machine_name: str
    file_path: float

    _file_content: str

    def __init__(self, file_path: str):
        filename = os.path.splitext(os.path.basename(file_path))[0]
        self.state_machine_name = filename[:1].upper() + filename[1:]
        with open(file_path, 'r', newline='') as f:
            self._file_content = ''.join(f.readlines())

    def GetNodeText(self, node: clang.cindex.Cursor) -> str:
        source_range = node.extent
        return self._file_content[source_range.start.offset:source_range.end.offset + 1]


class StateMachineParser:
    def __init__(self, file_path: str):
        translationUnit = clang_index.parse(file_path)
        self.ctx = ParsingContext(file_path)
        self.root_node = translationUnit.cursor
        self.states = {}

    def Parse(self):
        self._TraverseAST(self.root_node)
        self._UpdateChilds()
        self._OutputDiagram()

    def _UpdateChilds(self):
        for state_name in self.states:
            state = self.states[state_name]
            if state.parent_state_name:
                self.states[state.parent_state_name].child_states.append(state)

    def node_name(self, state_name):
        return 'n%d' % self.node_ids[state_name]

    def _OutputDiagram(self):
        root_node = create_graphml.prepare_graphml()
        self.graph = create_graphml.create_graph(root_node)
        self.node_ids = {}
        self.node_id = 0
        self.edge_id = 0

        for state_name in self.states:
            self._OutputState(self.states[state_name])

        for state_name in self.states:
            state = self.states[state_name]
            for name in state.handlers:
                h = state.handlers[name]
                if not h.target_state_name:
                    continue
                if h.state_name == h.target_state_name:
                    continue
                self._OutputEdge(h)

        create_graphml.finish_graphml(root_node)
        xml_tree = etree.ElementTree(root_node)
        xml_tree.write("test.graphml", xml_declaration=True, encoding="UTF-8")

    def _OutputEdge(self, h):
        link_caption = h.event_type
        if h.statements:
            link_caption = link_caption + '/' + '\n'.join(h.statements)
        create_graphml.add_edge(self.graph, "e%d" % self.edge_id,
                                self.node_name(h.state_name),
                                self.node_name(h.target_state_name),
                                link_caption,
                                0, 0, 0, 0)
        self.edge_id += 1

    def _OutputState(self, state):
        state_content = list()
        for name in state.handlers:
            h = state.handlers[name]
            if h.state_name != h.target_state_name:
                continue

            event_type = h.event_type
            if event_type == 'Q_ENTRY_SIG':
                event_type = 'entry'
            if event_type == 'Q_EXIT_SIG':
                event_type = 'exit'
            state_content.append('%s/' % event_type)
            for statement in h.statements:
                for line in statement.split('\n'):
                    state_content.append('  ' + line)

        self.node_ids[state.state_name] = self.node_id
        create_graphml.add_simple_node(self.graph, state.state_name, '\n'.join(
            state_content), "n%i" % self.node_id, 100, 200, 259, 255)
        self.node_id += 1

    def _TraverseAST(self, node):
        if self._IsStateFunction(node):
            state = StateParser(self.ctx, node).Parse()
            self.states[state.state_name] = state
#            print('''
# State discovered:
# name = %s, parent = %s, handlers = %s
#            ''' % (state.state_name, state.parent_state_name, state.handlers.keys()))

        for childNode in node.get_children():
            self._TraverseAST(childNode)

    def _IsStateFunction(self, node):
        # and node.spelling.startswith('OregonPlayer_dead')
        return (node.kind == clang.cindex.CursorKind.FUNCTION_DECL and
                node.spelling.startswith(self.ctx.state_machine_name + '_') and
                not node.spelling.endswith('_ctor'))


class StateParser:
    def __init__(self, ctx: ParsingContext, root_node):
        self.ctx = ctx
        self.root_node = root_node
        self.state_name = root_node.spelling
        self.handlers = {}
        self.parent_state_name = None
        self.child_states = []

    def Parse(self):
        self._TraverseAST(self.root_node)
        return self

    def _TraverseAST(self, node):
        if node.kind == clang.cindex.CursorKind.CASE_STMT:
            h = EventHandlerParser(self.ctx, node, self.state_name).Parse()
#            print('''EventHandler:
# Event: %s, direction: %s --> %s, Code:
# %s
#            ''' % (h.event_type, h.state_name, h.target_state_name, '\n'.join(h.statements)))
            self.handlers[h.event_type] = h

        if node.kind == clang.cindex.CursorKind.DEFAULT_STMT:
            # That's how subtree of such node is expected to look like (generated by 'clang -Xclang -ast-dump <filename>.cpp')
            # `-DefaultStmt 0x7ffff3a84a08 <line:599:9, line:602:9>
            #     `-CompoundStmt 0x7ffff3a849e8 <line:599:18, line:602:9>
            #     |-BinaryOperator 0x7ffff3a849b8 <line:600:13, ./qhsm.h:72:26> 'QState':'int' lvalue '='
            #     | |-DeclRefExpr 0x7ffff3a84628 <oregonPlayer.cpp:600:13> 'QState':'int' lvalue Var 0x7ffff3a82dd0 'status_' 'QState':'int'
            #     | `-ParenExpr 0x7ffff3a84998 <./qhsm.h:71:5, line:72:26> 'QState':'int'
            #     |   `-BinaryOperator 0x7ffff3a84970 <line:71:6, line:72:25> 'QState':'int' ','
            #     |     |-BinaryOperator 0x7ffff3a84880 <line:71:6, line:63:56> 'QStateHandler':'QState (*)(void *const, const QEvt *const)' lvalue '='
            #     |     | |-MemberExpr 0x7ffff3a84758 <line:71:6, col:26> 'QStateHandler':'QState (*)(void *const, const QEvt *const)' lvalue ->effective_ 0x7ffff3a1b3a8
            #     |     | | `-ParenExpr 0x7ffff3a84738 <col:6, col:23> 'QHsm *'
            #     |     | |   `-ParenExpr 0x7ffff3a84718 <line:62:26, col:39> 'QHsm *'
            #     |     | |     `-CStyleCastExpr 0x7ffff3a846f0 <col:27, col:38> 'QHsm *' <BitCast>
            #     |     | |       `-ImplicitCastExpr 0x7ffff3a846d8 <col:35, col:38> 'OregonPlayer *' <LValueToRValue>
            #     |     | |         `-ParenExpr 0x7ffff3a846b8 <col:35, col:38> 'OregonPlayer *const' lvalue
            #     |     | |           `-DeclRefExpr 0x7ffff3a84650 <line:71:20> 'OregonPlayer *const' lvalue ParmVar 0x7ffff3a82c10 'me' 'OregonPlayer *const'
            #     |     | `-ParenExpr 0x7ffff3a84860 <line:63:31, col:56> 'QStateHandler':'QState (*)(void *const, const QEvt *const)'
            #     |     |   `-CStyleCastExpr 0x7ffff3a84838 <col:32, col:55> 'QStateHandler':'QState (*)(void *const, const QEvt *const)' <BitCast>
            #     |     |     `-ParenExpr 0x7ffff3a84818 <col:47, col:55> 'QState (*)(OregonPlayer *const, const QEvt *const)'
            #     |     |       `-UnaryOperator 0x7ffff3a847b8 <oregonPlayer.cpp:600:31, col:32> 'QState (*)(OregonPlayer *const, const QEvt *const)' prefix '&'
            #     |     |         `-DeclRefExpr 0x7ffff3a84790 <col:32> 'QState (OregonPlayer *const, const QEvt *const)' lvalue Function 0x7ffff3a692b0 'OregonPlayer_global' 'QState (OregonPlayer *const, const QEvt *const)'
            #     |     `-CStyleCastExpr 0x7ffff3a84948 <./qhsm.h:72:5, col:25> 'QState':'int' <NoOp>
            #     |       `-ImplicitCastExpr 0x7ffff3a84930 <col:13, col:25> 'QState':'int' <IntegralCast>
            #     |         `-ParenExpr 0x7ffff3a84910 <col:13, col:25> '(anonymous enum at ./qhsm.h:46:1)'
            #     |           `-DeclRefExpr 0x7ffff3a848a8 <col:14> '(anonymous enum at ./qhsm.h:46:1)' EnumConstant 0x7ffff3a1b090 'Q_RET_SUPER' '(anonymous enum at ./qhsm.h:46:1)
            #     `-BreakStmt 0x7ffff3a849e0 <oregonPlayer.cpp:601:13>
            compound_stmt = list(node.get_children())[0]
            assert compound_stmt.kind == clang.cindex.CursorKind.COMPOUND_STMT, self.ctx.GetNodeText(
                compound_stmt)
            binary_op = list(compound_stmt.get_children())[0]
            assert binary_op.kind == clang.cindex.CursorKind.BINARY_OPERATOR, self.ctx.GetNodeText(
                binary_op)
            rhs = list(binary_op.get_children())[1]
            assert rhs.kind == clang.cindex.CursorKind.PAREN_EXPR, self.ctx.GetNodeText(rhs)
            # GetText(rhs) should look like Q_SUPER(&OregonPlayer_global);
            self.parent_state_name = self.ctx.GetNodeText(rhs)[len('Q_SUPER(&'):-len(');')]
            if self.parent_state_name == 'QHsm_top':
                self.parent_state_name = None

        for childNode in node.get_children():
            self._TraverseAST(childNode)


class EventHandlerParser:
    def __init__(self, ctx: ParsingContext, root_node, state_name):
        self.ctx = ctx
        assert root_node.kind == clang.cindex.CursorKind.CASE_STMT, root_node.kind
        # That's how subtree of such node is expected to look like (generated by 'clang -Xclang -ast-dump <filename>.cpp')
        # |-CaseStmt 0x7ffff3a83de8 <line:589:9, line:593:9>
        # | |-ImplicitCastExpr 0x7ffff3a84a80 <line:589:14> 'QSignal':'int' <IntegralCast>
        # | | `-DeclRefExpr 0x7ffff3a83dc0 <col:14> 'PlayerSignals' EnumConstant 0x7ffff3a28b28 'PILL_RESET_SIG' 'PlayerSignals'
        # | `-CompoundStmt 0x7ffff3a84318 <col:30, line:593:9>
        children = list(root_node.get_children())
        self.event_type = list(children[0].get_children())[0].spelling
        self.root_node = children[1]
        assert self.root_node.kind == clang.cindex.CursorKind.COMPOUND_STMT, self.root_node.kind
        self.level = 0
        self.state_name = state_name
        self.target_state_name = None
        self.statements = []

    def Parse(self):
        self._TraverseAST(self.root_node)
        return self

    def _TraverseAST(self, node):
        if self.level == 1:
            # There is no support for other statements / flow control (e.g. for (...)).
            # So let's fail fast if something unexpected was encountered.
            assert (node.kind == clang.cindex.CursorKind.CALL_EXPR or  # Example: Foo(bar, 6);
                    # Example: me->value = Bar(e)
                    node.kind == clang.cindex.CursorKind.BINARY_OPERATOR or
                    node.kind == clang.cindex.CursorKind.BREAK_STMT or       # break;
                    node.kind == clang.cindex.CursorKind.IF_STMT), node.kind  # if (...) {...} else {...}
            # print(GetText(node))
            if node.kind == clang.cindex.CursorKind.IF_STMT:
                # TODO: Support branching.
                pass

            if node.kind == clang.cindex.CursorKind.BREAK_STMT:
                return

            if node.kind == clang.cindex.CursorKind.IF_STMT:
                return

            # It's a bit hacky:
            # 1) BINARY_OPERATOR doesn't necessarily mean equality operator. Can be some weird dangling statement like 'a < Foo(5);'
            # 2) It would be better to check if it is a status_ assignment by checking first child, which should be DECL_REF_EXPR node
            if node.kind == clang.cindex.CursorKind.BINARY_OPERATOR and self.ctx.GetNodeText(node).startswith('status_ = '):
                # That's how subtree of such node is expected to look like (generated by 'clang -Xclang -ast-dump <filename>.cpp')
                # |-BinaryOperator 0x7ffff3a845d0 <line:596:13, ./qhsm.h:66:45> 'QState':'int' lvalue '='
                # | |-DeclRefExpr 0x7ffff3a844c0 <oregonPlayer.cpp:596:13> 'QState':'int' lvalue Var 0x7ffff3a82dd0 'status_' 'QState':'int'
                # | `-ParenExpr 0x7ffff3a845b0 <./qhsm.h:66:21, col:45> 'QState':'int'
                # |   `-CStyleCastExpr 0x7ffff3a84588 <col:22, col:44> 'QState':'int' <NoOp>
                # |     `-ImplicitCastExpr 0x7ffff3a84570 <col:30, col:44> 'QState':'int' <IntegralCast>
                # |       `-ParenExpr 0x7ffff3a84550 <col:30, col:44> '(anonymous enum at ./qhsm.h:46:1)'
                # |         `-DeclRefExpr 0x7ffff3a844e8 <col:31> '(anonymous enum at ./qhsm.h:46:1)' EnumConstant 0x7ffff3a1b120 'Q_RET_HANDLED' '(anonymous enum at ./qhsm.h:46:1)'
                rhs = list(node.get_children())[1]
                if self.ctx.GetNodeText(rhs) == 'Q_HANDLED();':
                    self.target_state_name = self.state_name
                else:
                    # Cut state name from a string like 'Q_TRAN(&OregonPlayer_ghoul_wounded);'
                    self.target_state_name = self.ctx.GetNodeText(
                        rhs)[len('Q_TRAN(&'):-len(');')]
                return

            self.statements.append(self.ctx.GetNodeText(node))

        self.level = self.level + 1
        for childNode in node.get_children():
            self._TraverseAST(childNode)
        self.level = self.level - 1

parser = StateMachineParser(file_path = sys.argv[1])
parser.Parse()
