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
    data = [(signal+'_SIG,'+' '*(5 + max_len - len(signal)) + '"%s"' % signal + ','+ ' '*(5 + max_len - len(signal))
             + "'%s'" % signal[0].lower()) for signal in signals]
    res = '},\n{    '.join(data)
    res = "{    " + res + '},'
    return res


def create_files(path: str, signals: List[str]):
    """
    creates necessary service files
    :param path: path to service.c
    :param signals: lost of signals
    :return:
    """
    with open(os.path.join(path, "service.cpp"), "w") as f:
        with open(r"templates\service_c.txt") as templ:
            keystrokes = create_keystrokes(signals)
            text = Template(templ.read()).substitute({"keystrokes": keystrokes})
            f.write(text)