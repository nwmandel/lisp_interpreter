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
		self.outer = outer
		if isa(params, Symbol):
			self.update({params:list(args)})
		else: 
			if len(args) != len(params):
				raise TypeError('expected %s, given %s, '
								% (to_string(params), to_string(args)))
			self.update(zip(params,args))
	def find(self, var):
		"find inner most environment where var is"
		if var in self: return self
		elif self.outer is None: raise LookupError(var)
		else: return self.outer.find(var)
		#return self if (var in self) else self.outer.find(var)

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

def require(x, predicate, message="incorrect length"):
	"error handling"
	if not predicate: raise SyntaxError(to_string(x)+': '+message)

def let(*args):
	args = list(args)
	x = cons(_let, args)
	require(x, len(args)>1)
	bindings, body = args[0], args[1:]
	require(x, all(isa(b,list) and len(b)==2 and isa(b[0], Symbol)
		for b in bindings), "illegal bindings")
	vars, vals = zip(*bindings)
	return [[_lambda, list(vars)] + map(expand, body)] + map(expand, vals)

_append, _cons, _let = map(Sym("append cons let".split))
macro_table = {_let:let} 


def eval(x, env=global_env):
	"evaluate an expression in an environment"
	if isinstance(x, Symbol):	#variable
		return env.find(x)[x]
	elif not isinstance(x, List):	# const literal
		return x
	elif x[0] == 'quote':			# (quote exp)
		(_,exp) = x
		return exp
	elif x[0] == 'if':				# (if test conseq alt)
		(_,test,conseq,alt) = x
		exp = (conseq if eval(test,env) else alt)
		return eval(exp, env)
	elif x[0] == 'define':			# (define var exp)
		(_,var,exp) = x
		env[var] = eval(exp, env)
	elif x[0] == 'set!':			# (set! var exp)
		(_,var,exp) = x
		env.find(var)[var] = eval(exp,env)
	elif x[0] == 'lambda':			# (lambda (var*) exp)
		(_,params,body) = x
		return procedure(params, body, env)
	elif x[0] is _begin:			# (begin exp+)
		for exp in x[1:-1]:
			eval(exp, env)
		x = x[-1]
	else:							# (proc exp*)
		proc = eval(x[0], env)
		args = [eval(arg, env) for arg in x[1:]]
		return proc(*args)

def parse(inport):
	if isinstance(inport, str): inport = Input(StringIO.StringIO(inpot))
	return expand(read(inport), toplevel=True)

def expand(x, toplevel=False):
	"iterate over tree and type check"
	require(x,x!=[])						# () is an error
	if not isa(x,list):						# constand is unchanged
		return x	
	elif x[0] is _quote:					# (quote exp)
		require(x,len(x)==2)
		return x
	elif x[0] is _if:
		if len(x) == 3: x = x + [None]		# (if t c)# (if t c None)
		require(x, len(x)==4)
		return map(expand, x)
	elif x[0] is _set:
		require(x, len(x)==3)
		var = x[1]							# (set! non-var exp) is an error
		require(x, isa(var, Symbol), "can only set! a symbol")
		return [_set, var, expand(x[2])]
	elif x[0] is _define or x[0] is _definemacro:
		require(x, len(x)>=3)
		_def, v, body, = x[0], x[1], x[2:]
		if isa(v, list) and v:				# (define (f args) body)
			f, args = v[0], v[1:]			# is (define f (lambda (args) body))
			return expand([_def, f, [_lambda, args]+body])
		else: 
			require(x,len(x)==3)			# (define non-var/list exp) is an error
			require(x, isa(v, Symbol), "can only define a symbol")
			exp = expand(x[2])
			if _def is _definemacro:
				require(x, toplevel, "define-macro can only be at top level")
				proc = eval(exp)
				require(x, callable(proc), "macro must be procedure")
				macro_table[v] = proc 		# (define-macro v proc)
				return None					# is None and put v:proc in macro_table
			return [_define, v, exp]
	elif x[0] is _begin:					# (begin) is None
		if len(x) == 1: return None
		else: return [expand(xi, toplevel) for xi in x]
	elif x[0] is _lambda:					# (lambda (x) e1 e2)
		require(x, len(x)>=3)				# is (lambda (x) (begin e1 e2))
		vars, body = x[1], x[2:]
		require(x, (isa(vars, list) and all(isa(v, Symbol) for v in vars))
			or isa(vars, Symbol), "illegal lambda arguments")
		exp = body[0] if len(body) == 1 else [_begin] + body
		return [_lambda, vars, expand(exp)]
	elif x[0] is _quasiquote:
		require(x, len(x)==2)
		return expand_quasiquote(x[1])
	elif isa(x[0], Symbol) and x[0] in macro_table:
		return expand(macro_table[x[0]](*x[1:]), toplevel) 
	else:
		return map(expand, x)

def expand_quasiquote(x):
	if not is_pair(x):
		return [_quote, x]
	require(x, x[0] is not _unquotesplicing, "can't splice")
	if x[0] is _unquote:
		require(x, len(x)==2)
		return x[1]
	elif is_pair(x[0]) and x[0][0] is _unquotesplicing:
		require(x[0], len(x[0])==2)
		return [_append, x[0][1], expand_quasiquote(x[1:])]


def readchar(inport):
	"read next char from inportut buffer"
	if inport.line != '':
		ch, inport.line = inport.line[0], inport.line[1:]
		return ch
	else:
		return inport.file.read(1) or eof_object

def read(inport):
	"read expression from inport buffer"
	def readahead(tok):
		if '(' == tok:
			L = []
			while True:
				tok = inport.next_token()
				if tok == ')': return L
				else: L.append(readahead(tok))
		elif ')' == tok: raise SyntaxError('unexpected )')
		elif tok in quotes: return [quotes[tok], read(inport)]
		elif tok is eof_object: raise SyntaxError('unexpected EOF in list')
		else: return atom(tok)
	next_tok = inport.next_token()
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


