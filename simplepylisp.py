import math
import operator as op 

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

#Env = dict
Symbol = str
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

def tokenize(c):
	"convert a string of characters into a list of tokens"
	return c.replace('(', ' ( ').replace(')', ' ) ').split()

def parse(program):
	"read expression from a string"
	return read_from_toks(tokenize(program))

def read_from_toks(tokens):
	"read an expression from a sequence of tokens"
	if len(tokens) == 0:
		raise SyntaxError('unexpected EOF while reading')
	token = tokens.pop(0)
	if '(' == token:
		L = []
		while tokens[0] != ')':
			L.append(read_from_toks(tokens))
		tokens.pop(0)
		return L
	elif ')' == token:
		raise SyntaxError('unexpected \')\'')
	else:
		return atom(token)

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
	try: return int(token)
	except ValueError:
		try: return float(token)
		except ValueError:
			return Symbol(token)


def repl(prompt='pylisp> '):
	while True:
		val = eval(parse(input(prompt)))
		if val is not None:
			print(schemestr(val))

def schemestr(exp):
	"convert a python object into scheme string"
	if isinstance(exp, List):
		return '(' + ' '.join(map(schemestr,exp)) + ')'
	else:
		return str(exp)


