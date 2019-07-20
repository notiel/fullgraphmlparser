from typing import List
from string import Template
import os


def create_keystrokes(signals: list) -> str:
    """
    creates text for service.c
    :param signals: list of signals
    :return: text of keystrokes
    """
    max_len: int = max([len(signal) for signal in signals])
    data = [(signal+'_SIG,'+' '*(5 + max_len - len(signal)) + '"%s"' % signal + ',' + ' '*(5 + max_len - len(signal))
             + "'%s'" % signal[0].lower()) for signal in signals]
    res = '},\n{    '.join(data)
    res = "{    " + res + '},'
    return res


def create_main(sm_name: str, path: str):
    """
    create main file from template
    :param path: path to put main.cpp
    :param sm_name:name of sm
    :return:
    """
    with open(os.path.join(path, "main.cpp"), "w") as f:
        with open(r"templates/main_c.txt") as templ:
            modelname = sm_name[0].lower() + sm_name[1:]
            Modelname = sm_name[0].upper() + sm_name[1:]
            text = Template(templ.read()).safe_substitute({"include": r'#include "%s.h"' % modelname + '\n',
                                                      "machine": r'"%s State Machines"\n' % Modelname,
                                                      "ctor_call": "%s_ctor()\n" % Modelname,
                                                      "sm_call": "the_%s" % modelname,
                                                      "event": "%sQEvt e" % modelname})

            f.write(text)


def create_files(path: str, signals: List[str], modelname: str):
    """
    creates necessary service files
    :param modelname: name of mmdel
    :param path: path to service.c
    :param signals: lost of signals
    :return:
    """
    with open(os.path.join(path, "service.cpp"), "w") as f:
        with open(r"templates/service_c.txt") as templ:
            keystrokes = create_keystrokes(signals)
            text = Template(templ.read()).substitute({"keystrokes": keystrokes})
            f.write(text)
    with open(os.path.join(path, "cheetcodes.txt"), "w") as g:
        g.write(keystrokes)
    create_main(modelname, path)
