import os.path

import re
from graphml import *
from typing import List, Tuple
from stateclasses import State, Trigger

class CppFileWriter:
    id_to_name = {}

    def __init__(self, sm_name: str):
        self.sm_name = sm_name

    def write_to_file(self, f, start_node: str, start_action: str, states: List[State], notes: List[Dict[str, Any]]):
        self._insert_file_template(f, 'preamble_c.txt')
        for state in states:
            self.id_to_name[state.id] = state.name

        notes_dict = {note['id']: note for note in notes}

        self._insert_string(f, '/*.$define${SMs::STATE_MACHINE_CAPITALIZED_NAME_ctor} vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv*/\n')
        self._insert_string(f, '/*.${SMs::STATE_MACHINE_CAPITALIZED_NAME_ctor} ...............................................*/\n')
        self._insert_string(f, 'void STATE_MACHINE_CAPITALIZED_NAME_ctor(\n')
        constructor_fields: str = notes_dict['constructor_fields']['y:UMLNoteNode']['y:NodeLabel']['#text']
        self._insert_string(f, '    ' + ',\n    '.join(constructor_fields.replace(';', '').split('\n')[1:]) + ')\n')
        self._insert_string(f, '{\n')
        self._insert_string(f, '    STATE_MACHINE_CAPITALIZED_NAME *me = &STATE_MACHINE_NAME;\n')
        constructor_code: str = notes_dict['constructor_code']['y:UMLNoteNode']['y:NodeLabel']['#text']
        self._insert_string(f, '     ' + '\n    '.join(
            [v for v in constructor_code.replace('\r', '').split('\n')[1:] if v.strip() != '\n']
        ))
        self._insert_string(f, '\n')
        self._insert_string(f, '    QHsm_ctor(&me->super, Q_STATE_CAST(&STATE_MACHINE_CAPITALIZED_NAME_initial));\n')
        self._insert_string(f, '}\n')
        self._insert_string(f, '/*.$enddef${SMs::STATE_MACHINE_CAPITALIZED_NAME_ctor} ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^*/\n')

        self._insert_string(f, '/*.$define${SMs::STATE_MACHINE_CAPITALIZED_NAME} vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv*/\n')
        self._insert_string(f, '/*.${SMs::STATE_MACHINE_CAPITALIZED_NAME} ....................................................*/\n')
        self._insert_string(f, '/*.${SMs::STATE_MACHINE_CAPITALIZED_NAME::SM} ................................................*/\n')
        self._insert_string(f, 'QState STATE_MACHINE_CAPITALIZED_NAME_initial(STATE_MACHINE_CAPITALIZED_NAME * const me, void const * const par) {\n')
        self._insert_string(f, '    /*.${SMs::STATE_MACHINE_CAPITALIZED_NAME::SM::initial} */\n')
        self._insert_string(f, '    %s\n' % start_action)
        self._insert_string(f, '    return Q_TRAN(&STATE_MACHINE_CAPITALIZED_NAME_%s);\n' % self.id_to_name[start_node])
        self._insert_string(f, '}\n')


        self._write_state(f, states[0], 'SMs::%s::SM' % self._sm_capitalized_name())
        self._insert_file_template(f, 'footer_c.txt')

    def _write_guard_comment(self, f, state_path: str, event_name: str, guard: str):
        prefix = '            /*.${%s::%s::[' % (state_path, event_name)
        suffix = ']} */\n'
        guard_tokens = guard.replace('+', ' ').split(' ')
        shortened_guard = guard_tokens[0]
        i_token = 1
        while i_token < len(guard_tokens) and len(prefix) + len(shortened_guard) + len(guard_tokens[i_token]) + len(suffix) <= 121:
            shortened_guard = shortened_guard + guard_tokens[i_token]
            i_token = i_token + 1
        if i_token != len(guard_tokens):
            suffix = '~' + suffix[1:]

        return self._insert_string(f, prefix + shortened_guard + suffix)

    def _sm_capitalized_name(self) -> str:
        return self.sm_name[0].upper() + self.sm_name[1:]

    def _insert_string(self, f, s: str):
        f.write(re.sub('[ ]*\n', '\n',
                       s.replace('STATE_MACHINE_NAME', self.sm_name).replace('STATE_MACHINE_CAPITALIZED_NAME', self._sm_capitalized_name())))

    def _insert_file_template(self, f, filename: str):
        with open(os.path.join('templates', filename)) as input_file:
            for line in input_file.readlines():
                self._insert_string(f, line)

    def _write_state(self, f, state: State, state_path: str):
        state_path = state_path + '::' + state.name
        state_comment = '/*.${' + state_path + '} '
        state_comment = state_comment + '.' * (76 - len(state_comment)) + '*/\n'
        f.write(state_comment)
        self._insert_string(f, 'QState STATE_MACHINE_CAPITALIZED_NAME_%s(STATE_MACHINE_CAPITALIZED_NAME * const me, QEvt const * const e) {\n' % state.name)
        self._insert_string(f, '    QState status_;\n')
        self._insert_string(f, '    switch (e->sig) {\n')

        if state.name == 'global':
            self._insert_file_template(f, 'terminate_sig_c.txt')
        else:
            self._insert_string(f, '        /*.${' + state_path + '} */\n')
            self._insert_string(f, '        case Q_ENTRY_SIG: {\n')
            self._insert_string(f, '\n'.join(['            ' + line for line in state.entry.split('\n')])  + '\n')
            self._insert_string(f, '            status_ = Q_HANDLED();\n')
            self._insert_string(f, '            break;\n')
            self._insert_string(f, '        }\n')

            self._insert_string(f, '        /*.${' + state_path + '} */\n')
            self._insert_string(f, '        case Q_EXIT_SIG: {\n')
            self._insert_string(f, '\n'.join(['            ' + line for line in state.exit.split('\n')])  + '\n')
            self._insert_string(f, '            status_ = Q_HANDLED();\n')
            self._insert_string(f, '            break;\n')
            self._insert_string(f, '        }\n')

        triggers_merged: List[Tuple[str, List[Trigger]]] = []
        for trigger in state.trigs:
            if '?def' in trigger.name:
                continue
            if trigger.guard and len(triggers_merged) and triggers_merged[-1][0] == trigger.name:
                triggers_merged[-1][1].append(trigger)
            else:
                triggers_merged.append((trigger.name, [trigger]))

        for event_name, triggers in triggers_merged:
            self._insert_string(f, '        /*.${%s::%s} */\n' % (state_path, event_name))
            self._insert_string(f, '        case %s_SIG: {\n' % event_name)
            if len(triggers) == 1:
                self._write_trigger(f, triggers[0])
            elif len(triggers) == 2:
                if triggers[0].guard == 'else':
                    triggers[0], triggers[1] = triggers[1], triggers[0]
                self._write_guard_comment(f, state_path, event_name, triggers[0].guard)
                self._insert_string(f, '            if (%s) {\n' % triggers[0].guard)
                self._write_trigger(f, triggers[0], '    ')
                self._insert_string(f, '            }\n')
                self._write_guard_comment(f, state_path, event_name, triggers[1].guard)
                self._insert_string(f, '            else {\n')
                self._write_trigger(f, triggers[1], '    ')
                self._insert_string(f, '            }\n')
            else:
                self._insert_string(f, '!!! "else if" guards are not supported !!!')
            self._insert_string(f, '            break;\n')
            self._insert_string(f, '        }\n')

        self._insert_string(f, '        default: {\n')
        if state.parent:
            self._insert_string(f, '            status_ = Q_SUPER(&STATE_MACHINE_CAPITALIZED_NAME_%s);\n' % state.parent.name)
        else:
            self._insert_string(f, '            status_ = Q_SUPER(&QHsm_top);\n')
        self._insert_string(f, '            break;\n')
        self._insert_string(f, '        }\n')
        self._insert_string(f, '    }\n')
        self._insert_string(f, '    return status_;\n')
        self._insert_string(f, '}\n')

        for child_state in state.childs:
            self._write_state(f, child_state, state_path)

    def _write_trigger(self, f, trigger: Trigger, offset = ''):
        if trigger.action:
            self._insert_string(f, '\n'.join(
                [offset + '            ' + line for line in trigger.action.strip().split('\n')]) + '\n')
        if trigger.type == 'internal':
            self._insert_string(f, offset + '            status_ = Q_HANDLED();\n')
        elif trigger.type == 'external':
            self._insert_string(f,
                                offset + '            status_ = Q_TRAN(&STATE_MACHINE_CAPITALIZED_NAME_%s);\n' % self.id_to_name[
                                    trigger.target])
        else:
            self._insert_string(f, "// FIXME!!! Invalid trigger type\n")
