#!/usr/bin/env python3
"""Indent the recipe lines that are indented with spaces with a tab.

Make wants a recipe line to start with a tab. A line that starts with
spaces is a syntax error:

    Makefile:27: *** missing separator (did you mean TAB instead of 8
    spaces?).  Stop.

A few of the module trees have such lines. They are only noticed when the
branch of the makefile that holds them is taken, so the wlan tree built
nothing until the symbol list of the tree it depends on was there.

The fix is mechanical. A line is a recipe line when the line before it
starts a rule, or is a recipe line itself. The lines of a variable
assignment, of a conditional and of a define block are not recipe lines
and are left alone.
"""

import os
import re
import sys

DIRECTIVE = re.compile(
    r'^(ifeq|ifdef|ifequal|ifneq|else|endif|include|-include|sinclude|'
    r'export|unexport|override|define|endef|private|undefine|vpath|load|-load)\b')

ASSIGNMENT = re.compile(r'^[A-Za-z0-9_.$()/-]+\s*(:=|::=|=|\?=|\+=|-=)')

TARGET = re.compile(r'^[A-Za-z0-9_.$()/-]+([[:space:]]+[A-Za-z0-9_.$()/-]+)*\s*:')


def fix(path):
    """Return the number of lines that were fixed in the given file."""
    with open(path, errors='replace') as f:
        lines = f.read().split('\n')

    fixed = 0
    # none    no rule is open
    # rule    a rule was started, the next line is a recipe
    # recipe  the last line was a recipe
    # cont    the last line ended with a backslash, it continues
    # define  inside a define block, the lines are text
    state = 'none'
    depth = 0
    for i, line in enumerate(lines):
        text = line.strip()
        if not text:
            # a blank line ends the recipe, but not inside a conditional
            if depth == 0:
                state = 'none'
            continue

        indented = line[0] in ' \t'
        if not indented and text.startswith('define'):
            state = 'define'
            continue
        if state == 'define':
            if text.startswith('endef'):
                state = 'none'
            continue

        if DIRECTIVE.match(text):
            # a conditional or an include does not end the rule
            if text.startswith(('ifdef', 'ifeq', 'ifneq', 'ifequal')):
                depth += 1
            elif text.startswith('endif'):
                depth = max(0, depth - 1)
            continue

        if ASSIGNMENT.match(text):
            state = 'cont' if text.endswith('\\') else 'none'
            continue

        if TARGET.match(text):
            state = 'rule'
            continue

        # what is left is a command, it is a recipe line when a rule is open
        if state in ('rule', 'recipe'):
            # only a line that is indented with spaces is wrong, a line in
            # column zero is never a recipe line and a comment is not a
            # command
            if line.startswith(' ') and not text.startswith('#'):
                lines[i] = '\t' + text
                fixed += 1
            state = 'cont' if text.endswith('\\') else 'recipe'
        else:
            # a command without a rule, make will not take it either, leave
            # it alone
            state = 'none'

    if fixed:
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
    return fixed


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for name in filenames:
            if name not in ('Makefile', 'Kbuild', 'Makefile.include'):
                continue
            path = os.path.join(dirpath, name)
            n = fix(path)
            if n:
                print('%s: %d line(s)' % (path, n))
                total += n
    print('%d line(s) fixed' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
