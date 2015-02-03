#! /bin/sh
""":"
exec python "$0" ${1+"$@"}
"""
__doc__ = """A FORM profiler."""

import sys
import re
import operator
import optparse

if sys.version_info[0] >= 3:
    def is_str(x):
        return isinstance(x, str)
else:
    def is_str(x):
        return isinstance(x, basestring)

def analyze_logfile(file):
    if is_str(file):
        with open(file, 'r') as f:
            return analyze_logfile(f)

    a = []
    old_time = 0.0

    index  = 0
    step   = 0
    expr   = None
    text   = None
    time   = 0.0
    ngens  = 0
    nterms = 0
    nbytes = 0

    while True:
        line = file.readline()
        if not line:
            break
        if step == 0:
            m = re.match(r'Time *= *([0-9.]+) *sec *Generated terms *= *([0-9]+)', line)
            if m:
                time = float(m.group(1))
                ngens = int(m.group(2))
                step = 1
        elif step == 1:
            m = re.match(r' *([^ ]+) *([0-9]+) *Terms left *= *([0-9]+)', line)
            if m:
                step = 0
                continue
            m = re.match(r' *([^ ]+) *Terms in output *= *([0-9]+)', line)
            if m:
                expr = m.group(1)
                nterms = int(m.group(2))
                step = 2
            else:
                raise RuntimeError('Unexpected stat line [' + line.strip() + ']')
        elif step == 2:
            m = re.match(r' *(.*?) *Bytes used *= *([0-9]+)', line)
            if m:
                text = m.group(1)
                nbytes = int(m.group(2))
                a.append(type('', (), {
                    'index': index,
                    'expr': expr,
                    'text': text,
                    'time': time - old_time,
                    'elapsed': time,
                    'ngens': ngens,
                    'nterms': nterms,
                    'nbytes': nbytes
                    })())
                step = 0
                index += 1
                old_time = time
            else:
                raise RuntimeError('Unexpected stat line [' + line.strip() + ']')
    return a

def print_stat(a):
    print('{:<20}{:<12}{:>10}{:>10}{:>12} ->{:>12}' \
          .format('', 'EXPR', 'TIME', 'ELAPSED', 'NGENS', 'NTERMS'))
    for x in a:
        print('{:<20}{:<12}{:>10.2f}{:>10.2f}{:>12} ->{:>12}' \
              .format(x.text[:20], x.expr[:12], x.time, x.elapsed, x.ngens, x.nterms))

def startup():
    parser = optparse.OptionParser(usage='%prog [options] log-files..')
    parser.add_option('-0', action='store_const', const='0', dest='sort',
                      help='do not sort')
    parser.add_option('-t', action='store_const', const='t', dest='sort',
                      help='sort by timing [default]')
    parser.set_defaults(sort='t')
    (options, args) = parser.parse_args()
    a = []
    for file in args:
        a += analyze_logfile(file)
    if options.sort == 't':
        a.sort(key=operator.attrgetter('time'), reverse=True)
    print_stat(a)

if __name__ == '__main__':
    startup()
