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
" -> patterns/-/string
' -> patterns/-/string

#!patterns
number:
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
NullNode

@Parser
expr:
  BinOpNode | [comp-expr] <(AND|OR)> [comp-expr]
  | [comp-expr]

atom:
  StringNode | value:<STRING>
  

```




