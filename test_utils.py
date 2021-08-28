import os
import shutil
import stat
import sys

def getQmWithArgs():
    if sys.platform == 'win32':
        potential_qm_path = [os.environ.get('SYSTEMDRIVE') + '/qp', os.environ.get('PROGRAMFILES(X86)')]
        for p in potential_qm_path:
            potential_qm_exe = p + '/qm/bin/qm.exe'
            print('Trying to find qm.exe here: ' + potential_qm_exe)
            if os.path.isfile(potential_qm_exe):
                print('qm.exe found at %s, using it' % potential_qm_exe)
                return [potential_qm_exe]
        raise NotImplementedError('QM not found in supported locations!')

    if sys.platform == 'linux':
        # 1. On Linux, QM installer just unpacks itself wherever it was run,
        #    and not in any standard folder. As for now we only use Linux on Github Actions,
        #    let's use some well-defined path where we can install QM to.
        # 2. We use qm.sh instead of qm as recommended by https://www.state-machine.com/qm/gs_run.html#gs_run_linux
        # 3. We add xvfb-run so it can run in screen-less environments (e.g. Github Actions)
        return ['xvfb-run', '--auto-servernum', '--server-num=1', './qm/bin/qm.sh']

    raise NotImplementedError('Only windows and linux are supported')

def is_boring_line(line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    if line.startswith('/*'):
        return True
    return False

def remove_boring_lines(code: str) -> str:
    return '\n'.join([line for line in code.split('\n') if not is_boring_line(line)])

def removeOutputFolder():
    if (os.path.exists('testdata/test_output')):
        # Special magic is required to delete read-only files on Windows.
        # See https://bugs.python.org/issue19643 and https://hg.python.org/cpython/rev/31d63ea5dffa
        def remove_readonly(action, name, exc):
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)

        shutil.rmtree('testdata/test_output', onerror=remove_readonly)
