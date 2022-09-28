# InterpretedInterpreter
an interpreter that reads instructions to create an interpreter to run code using your own syntax rules


## So...
basically, I got bored of writing the rules of a lexer, parser, etc, in pure code, so I'm factoring out most of it into a sort of data structure!

and now I'm just writing code to intepret the rules for a language!


example rules: (it's a bit completely impossible to tell exactly whats happening in this lol)
```
@Lexer
#!literals
+
  + INCREMENT
  = PLUSEQ
  PLUS
-
  - DECREMENT
  = MINUSEQ
  > RARROW
  MINUS
*
  *
    = POWEQ
    POW
  = MULEQ
  MUL
/
  /
    = FLOOREQ
    FLOOR
  = DIVEQ
  DIV
" -> patterns/-/string
' -> patterns/-/string

#!patterns
number: #redirect-from:[0-9]
  >>> ([1-9][0-9_]*|0[0_]*)
    >>> (\.[0-9][0-9_]*)
      FLOAT
    INT
string:
  >> ("...")
  >> ('...')
  >> (f"...")
  >> (f'...')
  STRING

@Nodes
StringNode(value)
IntegerNode(value)
FloatNode(value)
NullNode
BinOpNode(left, op, right)

@Parser
expr:
  BinOpNode | left:[comp-expr] op:<(AND|OR)> right:[comp-expr]
  | [comp-expr]

atom:
  StringNode | value:<STRING>
  

```

## syntax for rules in @Lexer - #!literal:
```
@Lexer
#!literals
<char> <token>
<char> -> <path-to-pattern>

<char>
  ...
  -> <path-to-pattern>
  <token>
```
(indentation is entirely optional for literals, newlines are required though)

## syntax for rules in @Lexer - #!patterns:  
`>>> pattern`  
\^ checks if the text from current position matches pattern  
if it does match, go to nested elements  
ex:  
```
#!patterns
>>> pattern
  ...
  TOKEN
```
`>> pattern`  
\^ checks if the text from current pos matches pattern  
if multiple lines of these are given, only 1 needs to match for token to be made  
ex:  
```
string:
  >> ("...")
  >> ('...')
  STRING
```
`>-> pattern`  
\^ causes nested patterns to start checking from the beginning of the match, instead of the end  
ex:
```
identifier:
  >-> (if|elif|else|and|or|not|while|for)
    >>> (and)
      AND #no-value
    >>> (or)
      OR #no-value
    >>> (not)
      NOT #no-value
    KEYWORD
  >>> ([a-zA-Z_][a-zA-Z0-9_]*)
    ID
```

## Syntax for nodes in @Nodes:
I think the syntax is pretty straight forward,  
you put the name of the node, and then if you want that node to have values,  
you put then names of those values in parenthesis after the name:  
ex:  
```
@Nodes
NullNode
StringNode(value)
BinOpNode(left, op, right)
```
the @Nodes section really wasn't necessary for me to add, but it will probably make it easier to locate typos in the rules of @Parser eventually

## Syntax for rules in @Parser:
this is the most complicated rule syntax so far.  
it's regex-based, but with some rules to be able to check for tokens and other parser rules  
ex: (I'm leaving the comp-expr rule undefined, as it is a large chain of rules)
```
@Parser
expr:
  BinOpNode | left:[comp-expr] op:<(AND|OR)> right:[comp-expr]
  | [comp-expr]
```
so whats happening here?  
the rule name is obviouse, it's there so that you can reference it from within a rule
`BinOpNode | left:...` makes a BinOpNode with values captured from the pattern  
`| [comp-expr]` assumes that a node is being made in the comp-expr rule






