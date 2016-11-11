#!/bin/sh
""":" .

exec python "$0" "$@"
"""

from __future__ import print_function

import argparse
import re
import sys

__doc__ = """\
FORM log profiler.

Python versions
---------------
2.7, 3.2, 3.3, 3.4, 3.5

Example
-------
$ formprof.py myformprogram.log
$ formprof.py -m myformprogram.log
$ formprof.py -e myformprogram.log
"""

if sys.version_info[0] >= 3:
    string_types = str,
else:
    string_types = basestring,


class Stat(object):
    """Statistics object."""

    __slots__ = (
        'name',             # module name (str)
        'expr',             # expression name (str)
        'start',            # starting time (float)
        'end',              # end time (float)
        'elapsed',          # elapsed time (float)
        'count',            # number of occurrence (int)
        'generated_terms',  # number of generated terms (int)
        'terms_in_output',  # number of terms in output (int)
        'bytes_used',       # number of bytes used in output (int)
    )

    def __str__(self):
        """Return the string representation."""
        fmt = ('[Stat name={0}, expr={1}, start={2}, end={3}, elapsed={4}, '
               'count={5}, generated_terms={6}, terms_in_output={7}, '
               'bytes_used={8}]')
        return fmt.format(self.name, self.expr, self.start, self.end,
                          self.elapsed, self.count, self.generated_terms,
                          self.terms_in_output, self.bytes_used)


def analyze_logfile(file):
    """Generator of Stat objects from a file."""
    if isinstance(file, string_types):
        with open(file, 'r') as f:
            for s in analyze_logfile(f):
                yield s
            return

    SEARCH_TIME = 0  # noqa: N806
    SKIP_TIME = 1    # noqa: N806
    SEARCH_EXPR = 2  # noqa: N806
    SEARCH_NAME = 3  # noqa: N806

    state = SEARCH_TIME
    name = None
    expr = None
    time = 0.0
    old_time = 0.0
    generated_terms = 0
    terms_in_output = 0
    bytes_used = 0

    for line in file:
        line = line.rstrip()

        if state == SEARCH_TIME:
            m = re.match('\s*(?:Thread|Process) \d+ reporting', line)
            if m:
                state = SKIP_TIME
                continue

            m = re.match('W?Time =\s*([0-9.]+) sec \s*'
                         'Generated terms =\s*(\d+)', line)
            if m:
                time = float(m.group(1))
                generated_terms = int(m.group(2))
                state = SEARCH_EXPR
        elif state == SKIP_TIME:
            m = re.match('W?Time =\s*[0-9.]+ sec \s*'
                         'Generated terms =\s*\d+', line)
            if m:
                state = SEARCH_TIME
        elif state == SEARCH_EXPR:
            m = re.search('[0-9]+ Terms (?:left|active)', line)
            if m:
                state = SEARCH_TIME

            m = re.match('\s*(\S+?)\s* Terms in output =\s*(\d+)', line)
            if m:
                expr = m.group(1)
                terms_in_output = int(m.group(2))
                state = SEARCH_NAME
        elif state == SEARCH_NAME:
            m = re.match('(.+?)Bytes used \s*=\s*(\d+)', line)
            if m:
                name = m.group(1).strip()
                if not name:
                    name = '<unnamed>'
                bytes_used = int(m.group(2))
                state = SEARCH_TIME

                stat = Stat()
                stat.name = name
                stat.expr = expr
                stat.start = old_time
                stat.end = time
                stat.elapsed = time - old_time
                stat.count = 1
                stat.generated_terms = generated_terms
                stat.terms_in_output = terms_in_output
                stat.bytes_used = bytes_used
                old_time = time
                yield stat


def print_normal(stats):
    """Print statistics in the normal mode."""
    total_time = stats[-1].end

    # Sort.
    stats.sort(key=lambda s: -s.elapsed)

    # Stringification.
    stats = [(
        s.name,
        s.expr,
        '{0:.2f}'.format(s.elapsed),
        '{0:.2%}'.format(s.elapsed / total_time),
        '{0:.2f}'.format(s.start),
        '{0:.2f}'.format(s.end),
        str(s.generated_terms),
        str(s.terms_in_output),
        str(s.bytes_used),
    ) for s in stats]

    # Construct the format.
    columns = [
        'module  ',
        'expr    ',
        'time',
        ' ',
        'start',
        'end',
        'genterms',
        'outterms',
        'bytes',
    ]

    column_widths = [
        max(max(len(s[i]) for s in stats), len(columns[i]))
        for i in range(len(columns))
    ]

    fmt = (
        '{{0:<{0}}}  {{1:<{1}}}  {{2:>{2}}}  {{3:>{3}}}  {{4:>{4}}}  '
        '{{5:>{5}}}  {{6:>{6}}}  {{7:>{7}}}  {{8:>{8}}}'
    ).format(*column_widths)

    # Print the result.
    print(fmt.format(*columns))
    for s in stats:
        print(fmt.format(*s))


def print_module(stats):
    """Print statistics combined for each module."""
    total_time = stats[-1].end

    # Combine.
    new_stats = {}
    for s in stats:
        if s.name not in new_stats:
            t = Stat()
            t.name = s.name
            t.count = 1
            t.elapsed = s.elapsed
            new_stats[s.name] = t
        else:
            t = new_stats[s.name]
            t.count += 1
            t.elapsed += s.elapsed
    stats = list(new_stats.values())

    # Sort.
    stats.sort(key=lambda s: -s.elapsed)

    # Stringification.
    stats = [(
        s.name,
        str(s.count),
        '{0:.2f}'.format(s.elapsed),
        '{0:.2%}'.format(s.elapsed / total_time),
    ) for s in stats]

    # Construct the format.
    columns = [
        'module  ',
        'count',
        'time',
        ' ',
    ]

    column_widths = [
        max(max(len(s[i]) for s in stats), len(columns[i]))
        for i in range(len(columns))
    ]

    fmt = (
        '{{0:<{0}}}  {{1:>{1}}}  {{2:>{2}}}  {{3:>{3}}}'
    ).format(*column_widths)

    # Print the result.
    print(fmt.format(*columns))
    for s in stats:
        print(fmt.format(*s))


def print_expr(stats):
    """Print statistics combined for each expression."""
    total_time = stats[-1].end

    # Combine.
    new_stats = {}
    for s in stats:
        if s.expr not in new_stats:
            t = Stat()
            t.expr = s.expr
            t.count = 1
            t.elapsed = s.elapsed
            new_stats[s.expr] = t
        else:
            t = new_stats[s.expr]
            t.count += 1
            t.elapsed += s.elapsed
    stats = list(new_stats.values())

    # Sort.
    stats.sort(key=lambda s: -s.elapsed)

    # Stringification.
    stats = [(
        s.expr,
        str(s.count),
        '{0:.2f}'.format(s.elapsed),
        '{0:.2%}'.format(s.elapsed / total_time),
    ) for s in stats]

    # Construct the format.
    columns = [
        'expr    ',
        'count',
        'time',
        ' ',
    ]

    column_widths = [
        max(max(len(s[i]) for s in stats), len(columns[i]))
        for i in range(len(columns))
    ]

    fmt = (
        '{{0:<{0}}}  {{1:>{1}}}  {{2:>{2}}}  {{3:>{3}}}'
    ).format(*column_widths)

    # Print the result.
    print(fmt.format(*columns))
    for s in stats:
        print(fmt.format(*s))


def main():
    """Entry point."""
    from signal import signal, SIGPIPE, SIG_DFL
    signal(SIGPIPE, SIG_DFL)

    # Parse the command line arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('logfile',
                        type=str,
                        metavar='LOGFILE',
                        help='log file to be analyzed')
    parser.add_argument('-m',
                        '--module',
                        action='store_const',
                        const=True,
                        help='print statistics combined for each module')
    parser.add_argument('-e',
                        '--expr',
                        action='store_const',
                        const=True,
                        help='print statistics combined for each expression')
    args = parser.parse_args()

    # Parse the log file.
    stats = list(analyze_logfile(args.logfile))
    if not stats:
        print('empty log', file=sys.stderr)
        return

    # Print statistics.
    if args.module:
        print_module(stats)
    elif args.expr:
        print_expr(stats)
    else:
        print_normal(stats)


if __name__ == '__main__':
    main()
