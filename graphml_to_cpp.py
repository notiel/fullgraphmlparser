import os.path

import re
from graphml import *
from typing import List, Tuple
from stateclasses import State, Trigger

class CppFileWriter:
    id_to_name = {}
    notes_dict = {}
    f = None

    def __init__(self, sm_name: str, start_node: str, start_action: str, states: List[State], notes: List[Dict[str, Any]]):
        self.sm_name = sm_name
        for state in states:
            self.id_to_name[state.id] = state.name
            self.notes_dict = {note['id']: note for note in notes}
            self.start_node = start_node
            self.start_action = start_action
            self.states = states

    def write_to_file(self, folder: str):
        with open(os.path.join(folder, '%s_new.cpp' % self.sm_name), 'w') as f:
            self.f = f
            self._insert_file_template('preamble_c.txt')
            self._write_constructor()
            self._write_initial()
            self._write_states_recursively(f, self.states[0], 'SMs::%s::SM' % self._sm_capitalized_name())
            self._insert_file_template('footer_c.txt')

        self.f = None

    def _write_constructor(self):
        self._write_full_line_comment('.$define${SMs::STATE_MACHINE_CAPITALIZED_NAME_ctor}', 'v')
        self._write_full_line_comment('.${SMs::STATE_MACHINE_CAPITALIZED_NAME_ctor}', '.')
        self._insert_string('void STATE_MACHINE_CAPITALIZED_NAME_ctor(\n')
        constructor_fields: str = self.notes_dict['constructor_fields']['y:UMLNoteNode']['y:NodeLabel']['#text']
        self._insert_string('    ' + ',\n    '.join(constructor_fields.replace(';', '').split('\n')[1:]) + ')\n')
        self._insert_string('{\n')
        self._insert_string('    STATE_MACHINE_CAPITALIZED_NAME *me = &STATE_MACHINE_NAME;\n')
        constructor_code: str = self.notes_dict['constructor_code']['y:UMLNoteNode']['y:NodeLabel']['#text']
        self._insert_string('     ' + '\n    '.join(constructor_code.replace('\r', '').split('\n')[1:]))
        self._insert_string('\n')
        self._insert_string('    QHsm_ctor(&me->super, Q_STATE_CAST(&STATE_MACHINE_CAPITALIZED_NAME_initial));\n')
        self._insert_string('}\n')
        self._write_full_line_comment('.$enddef${SMs::STATE_MACHINE_CAPITALIZED_NAME_ctor}', '^')

    def _write_initial(self):
        self._write_full_line_comment('.$define${SMs::STATE_MACHINE_CAPITALIZED_NAME}', 'v')
        self._write_full_line_comment('.${SMs::STATE_MACHINE_CAPITALIZED_NAME}', '.')
        self._write_full_line_comment('.${SMs::STATE_MACHINE_CAPITALIZED_NAME::SM}', '.')
        self._insert_string(
            'QState STATE_MACHINE_CAPITALIZED_NAME_initial(STATE_MACHINE_CAPITALIZED_NAME * const me, void const * const par) {\n')
        self._insert_string('    /*.${SMs::STATE_MACHINE_CAPITALIZED_NAME::SM::initial} */\n')
        self._insert_string('    %s\n' % self.start_action)
        self._insert_string(
            '    return Q_TRAN(&STATE_MACHINE_CAPITALIZED_NAME_%s);\n' % self.id_to_name[self.start_node])
        self._insert_string('}\n')

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

        return self._insert_string(prefix + shortened_guard + suffix)

    def _write_full_line_comment(self, text: str, filler: str):
        self._insert_string(('/*' + text.replace('STATE_MACHINE_NAME', self.sm_name).replace('STATE_MACHINE_CAPITALIZED_NAME', self._sm_capitalized_name()) + ' ').ljust(76, filler) + '*/\n')

    def _sm_capitalized_name(self) -> str:
        return self.sm_name[0].upper() + self.sm_name[1:]

    def _insert_string(self, s: str):
        self.f.write(re.sub('[ ]*\n', '\n',
                       s.replace('STATE_MACHINE_NAME', self.sm_name).replace('STATE_MACHINE_CAPITALIZED_NAME', self._sm_capitalized_name())))

    def _insert_file_template(self, filename: str):
        with open(os.path.join('templates', filename)) as input_file:
            for line in input_file.readlines():
                self._insert_string(line)

    def _write_states_recursively(self, f, state: State, state_path: str):
        state_path = state_path + '::' + state.name
        state_comment = '/*.${' + state_path + '} '
        state_comment = state_comment + '.' * (76 - len(state_comment)) + '*/\n'
        f.write(state_comment)
        self._insert_string('QState STATE_MACHINE_CAPITALIZED_NAME_%s(STATE_MACHINE_CAPITALIZED_NAME * const me, QEvt const * const e) {\n' % state.name)
        self._insert_string('    QState status_;\n')
        self._insert_string('    switch (e->sig) {\n')

        if state.name == 'global':
            self._insert_file_template('terminate_sig_c.txt')
        else:
            self._insert_string('        /*.${' + state_path + '} */\n')
            self._insert_string('        case Q_ENTRY_SIG: {\n')
            self._insert_string('\n'.join(['            ' + line for line in state.entry.split('\n')])  + '\n')
            self._insert_string('            status_ = Q_HANDLED();\n')
            self._insert_string('            break;\n')
            self._insert_string('        }\n')

            self._insert_string('        /*.${' + state_path + '} */\n')
            self._insert_string('        case Q_EXIT_SIG: {\n')
            self._insert_string('\n'.join(['            ' + line for line in state.exit.split('\n')])  + '\n')
            self._insert_string('            status_ = Q_HANDLED();\n')
            self._insert_string('            break;\n')
            self._insert_string('        }\n')

        triggers_merged: List[Tuple[str, List[Trigger]]] = []
        for trigger in state.trigs:
            if '?def' in trigger.name:
                continue
            if trigger.guard and len(triggers_merged) and triggers_merged[-1][0] == trigger.name:
                triggers_merged[-1][1].append(trigger)
            else:
                triggers_merged.append((trigger.name, [trigger]))

        for event_name, triggers in triggers_merged:
            self._insert_string('        /*.${%s::%s} */\n' % (state_path, event_name))
            self._insert_string('        case %s_SIG: {\n' % event_name)
            if len(triggers) == 1:
                self._write_trigger(f, triggers[0])
            elif len(triggers) == 2:
                if triggers[0].guard == 'else':
                    triggers[0], triggers[1] = triggers[1], triggers[0]
                self._write_guard_comment(f, state_path, event_name, triggers[0].guard)
                self._insert_string('            if (%s) {\n' % triggers[0].guard)
                self._write_trigger(f, triggers[0], '    ')
                self._insert_string('            }\n')
                self._write_guard_comment(f, state_path, event_name, triggers[1].guard)
                self._insert_string('            else {\n')
                self._write_trigger(f, triggers[1], '    ')
                self._insert_string('            }\n')
            else:
                self._insert_string('!!! "else if" guards are not supported !!!')
            self._insert_string('            break;\n')
            self._insert_string('        }\n')

        self._insert_string('        default: {\n')
        if state.parent:
            self._insert_string('            status_ = Q_SUPER(&STATE_MACHINE_CAPITALIZED_NAME_%s);\n' % state.parent.name)
        else:
            self._insert_string('            status_ = Q_SUPER(&QHsm_top);\n')
        self._insert_string('            break;\n')
        self._insert_string('        }\n')
        self._insert_string('    }\n')
        self._insert_string('    return status_;\n')
        self._insert_string('}\n')

        for child_state in state.childs:
            self._write_states_recursively(f, child_state, state_path)

    def _write_trigger(self, f, trigger: Trigger, offset = ''):
        if trigger.action:
            self._insert_string('\n'.join(
                [offset + '            ' + line for line in trigger.action.strip().split('\n')]) + '\n')
        if trigger.type == 'internal':
            self._insert_string(offset + '            status_ = Q_HANDLED();\n')
        elif trigger.type == 'external':
            self._insert_string(offset + '            status_ = Q_TRAN(&STATE_MACHINE_CAPITALIZED_NAME_%s);\n' % self.id_to_name[
                                    trigger.target])
        else:
            self._insert_string("// FIXME!!! Invalid trigger type\n")
