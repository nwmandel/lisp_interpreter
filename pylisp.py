import math
import operator as op 
import re
import sys

class procedure(object):
	def __init__(self, params, body, env):
		self.params, self.body, self.env = params, body, env
	def __call__(self, *args):
		return eval(self.body, Env(self.params, args, self.env))

class Env(dict):
	"an environment is a dict of var,val pairs with and outer environment"
	def __init__(self, params=(), args=(), outer=None):
		self.update(zip(params, args))
		self.outer = outer
	def find(self, var):
		"find inner most environment where var is"
		return self if (var in self) else self.outer.find(var)

class Symbol(str): pass

eof_object = Symbol('#<eof-object>')


def Sym(s, symbol_table={}):
	"find or create symbol entry for str s in sym table"
	if s not in symbol_table: symbol_table[s] = Symbol(s)
	return symbol_table[s]

_quote, _if, _set, _lambda, _begin, _define, _definemacro = map(Sym, 
"quote if set! lambda begin define define-macro".split())

_quasiquote, _unquotesplicing, _unquote = map(Sym, 
"quasiquote, unquote-splicing, unquote".split())

class Input(object):
	"holds line of chars"
	_token = r'''\s*(,@|[('`,)]|"(?:[\\].|[^\\"])*"|;.*|[^\s('"`,;)]*)(.*)'''
	def __init__(self, file):
		self.file = file;
		self.line = ''
	def next_token(self):
		"return next token while reading text into line buffer"
		while True:
			if self.line == '': self.line = self.file.readline()
			if self.line == '': return eof_object
			token, self.line = re.match(Input._token, self.line).groups()
			if token != '' and not token.startswith(';'):
				return token


#Env = dict
#Symbol = str
List = list
Number = (int, float)
args = None

def stand_env():
	env = Env()
	env.update(vars(math))
	env.update({
		'+':op.add, '-':op.sub, '*':op.mul, '/':op.floordiv,
		'>':op.gt, '<':op.lt, '>=':op.ge, '<=':op.le, '=':op.eq,
		'abs':abs, 'append':op.add, 
		'begin':  lambda *x:x[-1],
		'car':    lambda x: x[0],
		'cdr':    lambda x:x[1:],
		'cons':   lambda x,y: [x] + y,
		'eq?':    op.is_,
		'equal?': op.eq,
		'length': len,
		'list':   lambda *x: list(x),
		'list?':  lambda x:isinstance(x,list),
		'map':    map,
		'max':    max,
		'min':    min,
		'not':    op.not_,
		'null?':  lambda x: x == [],
		'number?': lambda x: isinstance(x,Number),
		'procedure?': callable,
		'round':   round,
		'symbol?':  lambda x: isinstance(x,Symbol),
		})
	return env

global_env = stand_env()

def eval(x, env=global_env):
	"evaluate an expression in an environment"
	if isinstance(x, Symbol):
		return env.find(x)[x]
	elif not isinstance(x, List):
		return x
	elif x[0] == 'quote':
		(_,exp) = x
		return exp
	elif x[0] == 'if':
		(_,test,conseq,alt) = x
		exp = (conseq if eval(test,env) else alt)
		return eval(exp, env)
	elif x[0] == 'define':
		(_,var,exp) = x
		env[var] = eval(exp, env)
	elif x[0] == 'set!':
		(_,var,exp) = x
		env.find(var)[var] = eval(exp,env)
	elif x[0] == 'lambda':
		(_,params,body) = x
		return procedure(params, body, env)
	else:
		proc = eval(x[0], env)
		args = [eval(arg, env) for arg in x[1:]]
		return proc(*args)

def readchar(inp):
	"read next char from input buffer"
	if inp.line != '':
		ch, inp.line = inp.line[0], inp.line[1:]
		return ch
	else:
		return inp.file.read(1) or eof_object

def read(inp):
	"read expression from input buffer"
	def readahead(tok):
		if '(' == tok:
			L = []
			while True:
				tok = inp.next_token()
				if tok == ')': return L
				else: L.append(readahead(tok))
		elif ')' == tok: raise SyntaxError('unexpected )')
		elif tok in quotes: return [quotes[tok], read(inp)]
		elif tok is eof_object: raise SyntaxError('unexpected EOF in list')
		else: return atom(tok)
	next_tok = inp.next_token()
	return eof_object if next_tok is eof_object else readahead(next_tok)


def atom(token):
	"numbers become numbers, every other token is a symbol"
	if token == '#t': return True
	elif token == '#f': return False
	elif token[0] == '"': return token[1:-1].decode('string_escape')
	try: return int(token)
	except ValueError:
		try: return float(token)
		except ValueError:
			try: return complex(token.replace('i','j',1))
			except ValueError:
				return Symbol(token)

def to_string(x):
	"convert python object to lisp readable string"
	if x is True: return "#t"
	elif x is False: return "#f"
	elif isa(x, Symbol): return x
	elif isa(x, str): return '"%s"' % x.encode('string_escape').replace('"',r'\"')
	elif isa(x, list): return '(' + ' '.join(map(to_string, x)) + ')'
	elif isa(x, complex): return str(x).replace('j', 'i')
	else: return str(x)

def load(filename):
	repl(None, Input(open(filename)), None)

def repl(prompt='pylisp> ', inport=Input(sys.stdin), out=sys.stdout):
	while True:
		try:
			if prompt: sys.stderr.write(prompt)
			x = parse(inport)
			if x is eof_object: return
			val = eval(x)
			if val is not None and out: print >> out, to_string(val)
		except Exception as e:
			print('%s: %s' % (type(e).__name__, e))


