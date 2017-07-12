import math
import operator as op 

#TODO procedure and env classes then redefine evaluation

Env = dict
Symbol = str
List = list
Number = (int, float)

def stand_env():
	env = Env()
	env.update(vars(math))
	env.update({
		'+':op.add, '-':op.sub, '*':op.mul, 
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
		return env[x]
	elif not isinstance(x, List):
		return x
	elif x[0] == 'if':
		(_,test, conseq, alt) = x
		exp = (conseq if eval(test, env) else alt)
		return eval(exp, env)
	elif x[0] == 'define':
		(_,var, exp) = x
		env[var] = eval(exp, env)
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
