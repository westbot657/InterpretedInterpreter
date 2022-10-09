##########################################
# Run this for dynamic, interactive help #
##########################################

from Util import DebugPrint

import re, json

def make_escape_char_pattern(char_to_escape:str) -> str:
    """
    pass any `char`, and this will generate a pattern to capture
    anything between two chars
    ex: passing `"` will generate a pattern that can capture any
    string even if it has backslash-escaped chars:
    matches:\n
    "",\n
    "\\\\"with escaped quotes\\\\"",\n
    "\\\\\\\\", # single backslash\n
    "\\\\\\\\\\\\"or this\\\\\\\\\\\\""\n
    """
    _chars = { # this is to escape any regex special chars
        "$": "\\$",
        "^": "\\^",
        "(": "\\(",
        ")": "\\)",
        "[": "\\[",
        "]": "\\]",
        "{": "\\{",
        "}": "\\}",
        "*": "\\*",
        "-": "\\-",
        "+": "\\+",
        ".": "\\.",
        "?": "\\?"
    }
    char:str = _chars.get(char_to_escape, char_to_escape)
    # ^ this grabs the escaped regex char, or the plain char
    
    return f"{char}((\\\\.)*[^{char}\\\\]*)*{char}"

def colorize_regex(pattern:str):
    
    default_color = "\033[38;2;80;80;20m"
    set_color = "\033[38;2;220;220;50m"
    quantifier_color = "\033[38;2;20;120;200m"
    anchor_color = "\033[38;2;160;40;0m"
    escaped_color = "\033[38;2;180;180;50m"
    elipses_color = "\033[38;2;0;255;255m"
    
    def paren_color(depth):
        v = max(min((depth*10)+100, 255), 100)
        return f"\033[48;2;0;{v};{v//2}m\033[38;2;255;255;255m"#\033[48;2;0;{v};0m"

    def color_segment(pat, depth=0, dc=default_color): 
        res = ""
        c = pat[0]
        while c:
            if c in "}])":
                res += c + dc
                if c == ")":
                    res += "\033[0m"
                
                break
                
            elif m := re.match("(\\\\.)", pat):
                res += f"{escaped_color}{m.group()}{dc}"
                pat = pat.replace(m.group(), " ", 1)

            elif re.match("\.\.\.", pat):
                res += f"{elipses_color}...{dc}"
                pat = pat[2:]
            
            elif c == "(":
                res += paren_color(depth) + c
                pat = pat[1:] # remove the '('
                r, pat = color_segment(pat, depth+1, paren_color(depth))
                res += r + dc
                if len(pat) == 0: break
                    
            elif c == "{":
                res += quantifier_color + c
                pat = pat[1:] # remove the '{'
                r, pat = color_segment(pat, depth, dc=quantifier_color)
                res += quantifier_color + r + dc
                if len(pat) == 0: break
                    
            elif c == "[":
                res += set_color + c
                pat = pat[1:] # remove the '['
                r, pat = color_segment(pat, depth, dc=set_color)
                res += set_color + r + dc
                if len(pat) == 0: break
                    
            elif c in "*?+":
                res += quantifier_color + c + dc
                
            elif c in "$^|":
                res += anchor_color + c + dc
                
            else:
                res += c

            pat = pat[1:]
            if len(pat) == 0: break
            c = pat[0]
        
        return res, pat
    
    return default_color + color_segment(pattern)[0] + "\033[0m"

def colorize_string(string:str):
    
    default_color = "\033[38;2;220;170;100m"
    escaped_color = "\033[38;2;255;110;70m"
    bracket_color = "\033[38;2;20;80;190m"
    colored = default_color

    while string != "":
        if m := re.match("\\\\\d{1,3}", string):
            colored += f"{escaped_color}{m.group()}{default_color}"
            string = string.replace(m.group(), "", 1)
            
        elif m := re.match("\\\\.", string):
            colored += f"{escaped_color}{m.group()}{default_color}"
            string = string[2:]
            
        elif m := re.match("\{[a-zA-Z0-9_]*\}", string):
            colored += f"{bracket_color}{m.group()}{default_color}"
            string = string.replace(m.group(), "", 1)
            
        else:
            colored += string[0]
            string = string[1:]

    colored += "\033[0m"

    return colored
    
def colorize_number(number):
    return f"\033[38;2;20;100;240m{number}\033[0m"

def colorize_lexer_literals(text:str):

    char_color = "\033[38;2;10;140;180m"
    token_color = "\033[38;2;10;120;250m"
    arrow_color = "\033[38;2;0;200;120m"
    redirect_color = "\033[38;2;200;100;20m"
    error_color = "\033[38;2;200;50;10m"
    colored = ""
    
    for line in text.split("\n"):
        indent = re.match(" *", line).group()
        #print(f"indent: '{indent}' ({len(indent)})")
        line = line.strip()
        sub = indent
        if "->" in line:
            #print("has arrow")
            
            c, p = line.split("->")
            if c.strip():
                #print("has char")
                sub += f"{char_color}{c.strip()} "
                line = p.strip()
                
            line = line.replace("->", "")
            sub += f"{arrow_color}-> "
            if "?" in line:
                #print("has error")
                path, err = line.split("?")
                path = path.strip()
                err = err.strip()
                sub += f"{redirect_color}{path} {error_color}?{err}\033[0m"
                
            else:
                #print("no error")
                sub += f"{redirect_color}{line.strip()}\033[0m"
                
            colored += f"{sub}\n"

        elif " " in line:
            #print("char token")
            char, token = line.split(" ")
            colored += f"{indent}{char_color}{char} {token_color}{token}\033[0m\n"

        elif len(line) == 1:
            #print("char")
            colored += f"{indent}{char_color}{line}\033[0m\n"
            
        else:
            #print("token")
            colored += f"{indent}{token_color}{line}\033[0m\n"
    
    return colored.strip()

def colorize_flags(flags:str, hint:str=""):
    """
    `hint` can be:  
    "lexer" or "parser"
    or anything to color flags using smart-colorize
    """
    
    flag_color = "\033[28;2;230;25;225m"
    colored = []
    
    for flag in flags.split(" "):
        sub = ""
        if ":" in flag:
            f, p = flag.split(":", 1)
            sub += f"{flag_color}{f}:"
            if hint.lower() == "lexer":
                sub += colorize_regex(p)
                
            elif hint.lower() == "parser":
                sub += colorize_nodes(p)
                
            else:
                sub += smart_colorize(p)
                
        else:
            sub += f"{flag_color}{flag}\033[0m"
            
        colored.append(sub)

    return " ".join(colored).strip()
        

def colorize_lexer_patterns(text:str):

    rule_name_color = "\033[38;2;45;200;215m"
    token_color = "\033[38;2;10;120;250m"
    hc_arrow_color = "\033[38;2;210;140;30m" # >>>
    hr_arrow_color = "\033[38;2;190;190;35m" # >->
    sr_arrow_color = "\033[38;2;60;145;40m" # >>
    colored = ""
    
    for line in text.split("\n"):
        indent = re.match(" *", line).group()
        dent = len(indent)
        line = line.strip()
        
        if dent == 0 and line.split(" ")[0].endswith(":"):
            if "#" in line:
                rule_name, flags = line.split(":", 1)
                rule_name = rule_name.strip()
                flags = flags.strip()
                colored += f"{rule_name_color}{rule_name}: {colorize_flags(flags, 'lexer')}\n"
            else:
                colored += f"{rule_name_color}{line}\033[0m\n"

        elif line.startswith(">>>"): # hc
            line = line.replace(">>>", "", 1).strip()
            colored += f"{indent}{hc_arrow_color}>>> {colorize_regex(line)}\n"

        elif line.startswith(">->"): # hr
            line = line.replace(">->", "", 1).strip()
            colored += f"{indent}{hr_arrow_color}>-> {colorize_regex(line)}\n"

        elif line.startswith(">>"): # sr
            line = line.replace(">>", "", 1).strip()
            colored += f"{indent}{sr_arrow_color}>> {colorize_regex(line)}\n"

        elif line.startswith("->"):
            colored += f"{indent}{colorize_lexer_literals(line)}\n"

        else:
            if " " in line:
                token, flags = line.split(" ", 1)
                colored += f"{indent}{token_color}{token}  {colorize_flags(flags.strip(), 'lexer')}\n"
            else:
                colored += f"{indent}{token_color}{line}\033[0m\n"
            
    return colored.strip()

def colorize_nodes(text:str):

    node_name_color = "\033[38;2;10;80;200m"
    symbol_color = "\033[38;2;200;200;50m"
    args_color = "\033[38;2;10;200;100m"
    colored = ""

    for line in text.split("\n"):
        line = line.strip()
        if "(" in line:
            name, args = line.replace(")", "").split("(")
            name = name.strip()
            args = args.split(",")
            args = [arg.strip() for arg in args]
            args = args_color + (f"{symbol_color}, {args_color}".join(args))
            colored += f"{node_name_color}{name}{symbol_color}({args}{symbol_color})\033[0m\n"

        else:
            colored += f"{node_name_color}{line}\033[0m\n"
    
    return colored.strip()

def colorize_parser(text:str):

    node_name_color = "\033[38;2;10;80;200m"

    default_color = "\033[38;2;80;80;20m"
    #set_color = "\033[38;2;220;220;50m"
    quantifier_color = "\033[38;2;20;120;200m"
    rule_name_color = "\033[28;2;250;170;15m"
    rule_color = "\033[38;2;250;240;15m"
    token_color = "\033[38;2;10;120;250m"
    token_value_color = "\033[38;2;200;100;20m"
    capture_color = "\033[38;2;175;25;180m"
    flag_color = "\033[28;2;230;25;225m"
    colored = ""
    
    #anchor_color = "\033[38;2;160;40;0m"
    #escaped_color = "\033[38;2;180;180;50m"
    #elipses_color = "\033[38;2;0;255;255m"
    
    # def paren_color(depth):
    #     v = max(min((depth*10)+100, 255), 100)
    #     return f"\033[48;2;0;{v};{v//2}m\033[38;2;255;255;255m"#\033[48;2;0;{v};0m"

    for line in text.split("\n"):
        indent = re.match(" *", line).group()
        dent = len(indent)
        line = line.strip()

        if dent == 0 and line.split(" ", 1)[0].endswith(":"):
            if " " in line:
                colored += f"{rule_name_color}{line.split(' ',  1)[0]} {node_name_color}{line.split(' ', 1)[1]}\033[0m\n"
            else:
                colored += f"{rule_name_color}{line}\033[0m\n"

        else:
            sub = indent
            if not line.startswith("|") and "|" in line:
                node = line.split("|", 1)[0].strip()
                line = line.split("|", 1)[1].strip()
                sub += f"{node_name_color}{node} {default_color}| "
            elif "|" not in line:
                pass

            pattern = line.split("  ")
            flags = None
            if len(pattern) == 2:
                flags = pattern[1]
                pattern = pattern[0]
            else:
                pattern = pattern[0]

            col = []
            for piece in pattern.split(" "):
                _sub = default_color

                while piece != "":
                    if m := re.match("<[^>]+>", piece):
                        m = m.group()
                        if ":" in m:
                            _sub += colorize_regex(m).replace(default_color, token_color).replace(":", f":{token_value_color}").replace(">", f"{token_color}>{default_color}")
                        else:
                            _sub += colorize_regex(m).replace(default_color, token_color) + default_color
                        piece = piece.replace(m, "", 1)
                    elif m := re.match("\\[[^\\]]+\\]", piece):
                        m = m.group()
                        _sub += f"{rule_color}{m}{default_color}"
                        piece = piece.replace(m, "", 1)
                    elif m := re.match("[a-zA-Z_][a-zA-Z0-9_]*:", piece):
                        m = m.group()
                        _sub += f"{capture_color}{m}{default_color}"
                        piece = piece.replace(m, "", 1)
                    elif m := re.match("\{\d+(,\d*)?\}", piece):
                        m = m.group()
                        _sub += f"{quantifier_color}{m}{default_color}"
                        piece = piece.replace(m, "", 1)
                    elif piece[0] in "+*?":
                        _sub += f"{quantifier_color}{piece[0]}{default_color}"
                        piece = piece[1:]
                    else:
                        _sub += piece[0]
                        piece = piece[1:]

                col.append(_sub)
            
            colored += sub + (" ".join(col)) + "  " + flag_color + colorize_flags(flags or "", 'parser') + "\033[0m\n"
    
    return colored.strip()

def colorize_json(obj:dict, indent=2):
    return json.dumps(obj, indent=indent)

def smart_colorize(text:str):
    # automatically detect the best coloring method?
    return text


regex_test = "(~/.../.../~) \"(\\\\.|[^\\\"])*\""
string_test = "\"\\033[38;2;255;255;0mthis is test number {test}!\\nyay\""
number_test = "15.6"
lexer_literal_test = """\
~
    / -> patterns/-/regex
    = -> TILDEEQ
    TILDE\
"""
lexer_pattern_test = """\
regex:
    >> (~/.../.../~)
    >> (~/.../~)
    >> (~/~)
    REGEX
identifier: #redirect-from:[_a-zA-Z]
    >-> (if|elif|else|switch|case|while|for|in|is|throw|catch|and|or|not|true|false|null)
        >>> (and)
            AND #no-value
        >>> (or)
            OR #no-value
        >>> (not)
            NOT #no-value
        >>> (true|false)
            BOOLEAN
        >>> (null)
            NULL #no-value
        KEYWORD #regex-value
    >-> ([_a-zA-Z][_a-zA-Z0-9]*)
        >-> (f("|'))
            -> patterns/-/string
        ID\
"""
node_test = """\
NullNode
EmptyNode
IntegerNode(value)
RegexNode(pattern, flags)
BinOpNode(left, op, right)\
"""
parser_test = """\
statements: BodyNode
    | <(NEWLINE|SEMICOLON)>* statements:[statement]*
statement:
    ReturnNode | <KEYWORD:return> value:[expr]?  #value:NullNode
    BreakNode | <KEYWORD:break>
    ContinueNode | <KEYWORD:continue>
    | [expr]
expr:
    BinOpNode | left:[comp-expr] op:<(AND|OR)> right:[comp-expr]
    | [comp-expr]
comp-expr:
    | left:[arith-expr] op:<(EE|LT|GT|LTE|GTE)> right:[arith-expr]
    | [arith-expr]

atom:
    IntegerNode | value:<INT>
    FloatNode | value:<FLOAT>
    BooleanNode | value:<BOOLEAN>
    | [class-def]
    | [var-def]
    | [func-def]
    | [import-expr]
    | [var-access]

var-def: VarAssignNode
    | mods:[mods]? name:[aliases] (<LT> clamp:[names] <GT>)? <EQ> value:[expr]  #mods:NullNode #clamp:NullNode
    | mods:[mods]? name:[aliases] (<LT> clamp:[names] <GT>)? <SEMICOLON>  #mods:NullNode #clamp:NullNode #value:NullNode\
"""

def main():

    #print(colorize_regex(regex_test))
    
    #print(colorize_string(string_test))

    #print(colorize_number(number_test))
    
    #print(colorize_lexer_literals(lexer_literal_test))

    #print(colorize_lexer_patterns(lexer_pattern_test))

    #print(colorize_nodes(node_test))

    print(colorize_parser(parser_test))
    
    return

if __name__ == "__main__":
    main()
