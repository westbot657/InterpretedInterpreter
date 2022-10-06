# InterpretedInterpreter
an interpreter that reads instructions to create an interpreter to run code using your own syntax rules

#### jump to:
[Example Rules](#example-rules) | [Lexer](#Lexer)

## So...
basically, I got bored of writing the rules of a lexer, parser, etc, in pure code, so I'm factoring out most of it into a sort of data structure!

and now I'm just writing code to intepret the rules for a language!


### <a id="example-rules" name="example-rules">Example Rules</a>
(it's a bit completely impossible to tell exactly whats happening in this lol)

```ruby
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
```
```ruby Lexer-patterns
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
```html
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
```ruby
#!patterns
>>> pattern
  ...
  TOKEN
```
`>> pattern`  
\^ checks if the text from current pos matches pattern  
if multiple lines of these are given, only 1 needs to match for token to be made  
ex:  
```ruby
string:
  >> ("...")
  >> ('...')
  STRING
```
`>-> pattern`  
\^ causes nested patterns to start checking from the beginning of the match, instead of the end  
ex:
```ruby
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
```ruby
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

```ruby
@Parser
expr:
  BinOpNode | left:[comp-expr] op:<(AND|OR)> right:[comp-expr]
  | [comp-expr]
```
so whats happening here?  
the rule name is obviouse, it's there so that you can reference it from within a rule
`BinOpNode | left:...` makes a BinOpNode with values captured from the pattern  
`| [comp-expr]` assumes that a node is being made in the comp-expr rule

parts of a pattern should be seperated by spaces.  
Ex:
```ruby
VarAssignNode | <KEYWORD:var> name:<ID> (<LT> type:<ID> <RT>)? <EQ> value:[expr]  #type:NullNode
                             ^         ^     ^         ^      ^    ^
```
set-val flags should start with #, and have a 2-space gap after a pattern:
```ruby
VarAssignNode | ... value:[expr]  #type:NullNode
                                ^^
```
parenthesis do work (ish), if you use them,  
it's best to not nest them more than needed,  
it's generally better to do multiple patterns instead.  
putting a quantifier after parenthesis does work, but  
if you have captures inside, also put a set-val flag  
for that capture (depending on the quantifier type)
```ruby
VarAssignNode | <KEYWORD:var> name:<ID> (<LT> type:<ID> <RT>)? <EQ> value:[expr]  #type:NullNode
                                        ^                   ^^
```

multiple rules:  
while making the parser-generator, an issue was found  
where having the same sub-rule as the start of 2 patterns  
caused it to take a very long time to evaluate
```ruby
expr:
  BinOpNode | left:[comp-expr] ...
  | [comp-expr]    ^^^^^^^^^^^
    ^^^^^^^^^^^
```
this issue has been fixed now! when looking for patterns,  
it stores the result of the first element of a pattern,  
(in this case, the result of `[comp-expr]`), and if the  
rest of the pattern fails, then if the next pattern consists  
of only that same first element (`[comp-expr]`), then the stored  
value is returned, rather than trying to re-parse the text  
that made that value






