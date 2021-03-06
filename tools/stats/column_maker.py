# this is a tool that creates another column
import sys, sets, re

def get_wrap_func(value):
    try:
        check = float(value)
        return 'float(%s)'
    except:
        return 'str(%s)'

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

# we expect 4 parameters
if len(sys.argv) != 4:
    print sys.argv
    stop_err('Usage: python column_maker.py input_file ouput_file condition')
#debug 
#cond_text = "(c2-c3) < 115487120 and c1=='chr7' "
#sys.argv.extend( [ 'a.txt', 'b.txt', cond_text ])

inp_file  = sys.argv[1]
out_file  = sys.argv[2]
cond_text = sys.argv[3]

# replace if input has been escaped
mapped_str = {
    '__lt__': '<',
    '__le__': '<=',
    '__gt__': '>',
    '__ge__': '>=',
    '__sq__': '\'',
    '__dq__': '"',

}
for key, value in mapped_str.items():
    cond_text = cond_text.replace(key, value)

#
# safety measures
#
safe_words = sets.Set( "c chr str float int split map lambda and or len".split() )
try:
    # filter on words
    patt = re.compile('[a-z]+')
    for word in patt.findall(cond_text):
        if word not in safe_words:
            raise Exception, word
except Exception, e:
    stop_err("Cannot recognize the word %s in condition %s" % (e, cond_text) )

#
# guess how many columns there are and what wrappers are appropriate for each
#
elems = []
fp = open(inp_file)
while 1:
    line = fp.readline().strip()
    if line and line[0] != '#':
        elems = line.split('\t')
        break
fp.close()

if not elems:
    stop_err('Empty file?')    

if len(elems) == 1:
    if len(line.split()) != 1:
        stop_err('This tool can only be run on tab delimited files')

#
# prepare the variable names and wrappers
#
cols, funcs = [], []
for ind, elem in enumerate(elems):
    name = 'c%d' % ( ind + 1 )
    cols.append(name)
    funcs.append(get_wrap_func(elem) % name)

col   = ', '.join(cols)
func  = ', '.join(funcs)
assign = "%s = line.split('\\t')" % col
wrap   = "%s = %s" % (col, func)

cols = []
code = '''
for line in file(inp_file):
    line = line.strip()
    if line and line[0] != '#':
        %s
        %s
        cols.append(%s)
    else:
        cols.append('')
''' % (assign, wrap, cond_text)

#
# execute code
#
try:
    exec code
except Exception, e:
    stop_err('Code %s raised error: %s' % (code, e))

#
# create output
#
fp = open(out_file, 'wt')
for value, line in zip(cols, file(inp_file)):
    line = line.strip()
    line = '%s\t%s\n' % (line, value)
    fp.write(line)
fp.close()

print 'Creating column %d with expression %s' % (len(elems)+1, cond_text)

