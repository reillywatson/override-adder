#!/usr/bin/env python
import os
import codecs
import sys

# You probably want to change this!
# I guess ideally this will come as a command-line parameter,
# but I only want this for one project so I can't be bothered.
BASE_DIR = "/Users/reilly/Nickel/src/"

def header_files(dir):
    files = []
    for root, dir, filenames in os.walk(dir):
        for f in filenames:
            if f.endswith('.h'):
                files.append(os.path.join(root, f))
    return files

def get_includes(lines, path, visited = []):
    visited.append(path)
    includes = set()
    for line in lines:
        if '#include' in line:
            includePath = ''
            if '"' in line:
                includePath = path + '/' + line.split('"')[1]
            else:
                includePath = BASE_DIR + line.split('<')[1][:-1]
            incLines = get_lines(includePath)
            if len(incLines) > 0:
                includes.add(includePath)
                includes = includes.union(get_includes(incLines, '/'.join(includePath.split('/')[:-1]), visited))
    return includes

def get_base_classes(lines):
    parents = []
    for line in lines:
        if 'public ' in line and ' slots' not in line:
            start = 0
            parents = line.split('public ')[1:]
            parents = [a.split('<')[0].split(',')[0].split(' ')[0] for a in parents]
    return parents

def get_lines(f):
    try:
        return codecs.open(f, 'r', 'utf-8').read().split('\n')
    except:
        return []

def get_virtual_functions(lines):
    funcs = []
    for line in lines:
        if 'virtual ' in line:
            funcName = line.split('(')[0].split(' ')[-1]
            if len(funcName) == 0:
                continue
            if funcName[0] == '*' or funcName[0] == '&':
                funcName = funcName[1:]
            funcs.append(funcName)
    return funcs

def add_override(filename, linesToAdd):
    import envoy
    import multiprocessing
    import shutil
    if len(linesToAdd) > 0:
        oldLines = get_lines(filename)
        shutil.copyfile(filename, 'test.tmp')
        newfile = codecs.open(filename, 'w', 'utf-8')
        for lineNo in linesToAdd:
            line = oldLines[lineNo]
            if '{' in line:
                line = line.replace('{', 'override {')
            else:
                 line = line[:-1] + ' override;'
            oldLines[lineNo] = line
        if oldLines[-1] == '\n':
            oldLines = oldLines[:-1]
        newfile.write('\n'.join(oldLines))
        newfile.close()
        ret = envoy.run('make -j%d' % multiprocessing.cpu_count())
        if ret.status_code == 0:
            print 'added some overrides! ' + filename
        else:
            print 'failed, backing it out! ' + filename
            print 'error: ' + ret.std_err
            shutil.copyfile('test.tmp', filename)
            return False
    else:
        print 'no changes needed! ' + filename
    return True

def testSubsets(filename, l):
    import itertools
    for numtoremove in range(len(l), 0, -1):
        for test in itertools.combinations(l, numtoremove):
            print 'testing: ', filename, test
            if add_override(filename, test):
                return

def testRemovingIncludes(filename):
	unused = override_candidates(filename)
	testSubsets(filename, unused)

def override_candidates(header):
    lines = get_lines(header)
    supers = get_base_classes(lines)
    includes = get_includes(lines, '/'.join(header.split('/')[:-1]))
    base_files = []
    for s in supers:
        for include in includes:
            if s in include:
                base_files.append(include)
    candidates = set()
    for base in base_files:
        for virtual in get_virtual_functions(get_lines(base)):
            for lineNo, line in enumerate(lines):
                if virtual + '(' in line and ';' in line and 'override' not in line and ' ' in line and ' = 0;' not in line and 'typedef' not in line:
                    candidates.add(lineNo)
    return candidates

def add_overrides_recursive(dirName):
	files = header_files(dirName)
	for f in files:
		testRemovingIncludes(f)

def main():
	if len(sys.argv) < 2:
		print 'Usage: override <paths>'
		return -1
	for path in sys.argv[1:]:
		add_overrides_recursive(path)

if __name__ == '__main__':
	sys.exit(main())
