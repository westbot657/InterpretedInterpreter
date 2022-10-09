##########################################
# Run this for dynamic, interactive help #
##########################################

from numpy import isin
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

def get_largest(array):
    max_ = None
    max_vals = []
    for key, val in array:
        if max_ == None: max_ = key
        if key > max_:
            max_ = key
            max_vals = [val]
        elif key == max_:
            max_vals.append(val)
        
    return max_vals

REGEX_DEFAULT_COLOR    = "\033[38;2;80;80;20m"
REGEX_SET_COLOR        = "\033[38;2;220;220;50m"
REGEX_QUANTIFIER_COLOR = "\033[38;2;20;120;200m"
REGEX_ANCHOR_COLOR     = "\033[38;2;160;40;0m"
REGEX_ESCAPED_COLOR    = "\033[38;2;180;180;50m"
REGEX_ELIPSES_COLOR    = "\033[38;2;0;255;255m"

STRING_DEFAULT_COLOR = "\033[38;2;220;170;100m"
STRING_ESCAPED_COLOR = "\033[38;2;255;110;70m"
STRING_BRACKET_COLOR = "\033[38;2;20;80;190m"

JSON_KEY_COLOR = "\033[38;2;50;90;250m"
JSON_KEY_ESCAPED_COLOR = "\033[38;2;50;40;150m"

NUMBER_COLOR = "\033[38;2;50;230;100m"

TOKEN_COLOR = "\033[38;2;10;120;250m"
TOKEN_VALUE_COLOR = "\033[38;2;200;100;20m"

LEXER_L_CHAR_COLOR     = "\033[38;2;10;140;180m"
LEXER_L_ARROW_COLOR    = "\033[38;2;0;200;120m"
LEXER_L_REDIRECT_COLOR = "\033[38;2;200;100;20m"
LEXER_L_ERROR_COLOR    = "\033[38;2;200;50;10m"

FLAG_COLOR = "\033[38;2;100;100;100m"
RULE_NAME_COLOR = "\033[38;2;45;200;215m"
RULE_REF_COLOR = "\033[38;2;250;240;15m"
CAPTURE_COLOR = "\033[38;2;175;25;180m"

LEXER_P_HC_ARROW_COLOR = "\033[38;2;210;140;30m" # >>>
LEXER_P_HR_ARROW_COLOR = "\033[38;2;190;190;35m" # >->
LEXER_P_SR_ARROW_COLOR = "\033[38;2;60;145;40m" # >>

SEGMENT_LABEL_COLOR = "\033[38;2;255;200;10m"
SUBSEGMENT_LABEL_COLOR = "\033[38;2;255;150;5m"

NODE_COLOR = "\033[38;2;10;80;200m"
SYMBOL_COLOR = "\033[38;2;200;200;50m"
ARGS_COLOR = "\033[38;2;10;200;100m"


def colorize_regex(pattern:str):
    
    def paren_color(depth):
        v = max(min((depth*10)+100, 255), 100)
        return f"\033[48;2;0;{v};{v//2}m\033[38;2;255;255;255m"#\033[48;2;0;{v};0m"

    def color_segment(pat, depth=0, dc=REGEX_DEFAULT_COLOR): 
        res = ""
        c = pat[0]
        while c:
            if c in "}])":
                res += c + dc
                if c == ")":
                    res += "\033[0m"
                
                break
                
            elif m := re.match(r"(\\.)", pat):
                res += f"{REGEX_ESCAPED_COLOR}{m.group()}{dc}"
                pat = pat.replace(m.group(), " ", 1)

            elif re.match(r"\.\.\.", pat):
                res += f"{REGEX_ELIPSES_COLOR}...{dc}"
                pat = pat[2:]
            
            elif c == "(":
                res += paren_color(depth) + c
                pat = pat[1:] # remove the '('
                r, pat = color_segment(pat, depth+1, paren_color(depth))
                res += r + dc
                if len(pat) == 0: break
                    
            elif c == "{":
                res += REGEX_QUANTIFIER_COLOR + c
                pat = pat[1:] # remove the '{'
                r, pat = color_segment(pat, depth, dc=REGEX_QUANTIFIER_COLOR)
                res += REGEX_QUANTIFIER_COLOR + r + dc
                if len(pat) == 0: break
                    
            elif c == "[":
                res += REGEX_SET_COLOR + c
                pat = pat[1:] # remove the '['
                r, pat = color_segment(pat, depth, dc=REGEX_SET_COLOR)
                res += REGEX_SET_COLOR + r + dc
                if len(pat) == 0: break
                    
            elif c in "*?+":
                res += REGEX_QUANTIFIER_COLOR + c + dc
                
            elif c in "$^|":
                res += REGEX_ANCHOR_COLOR + c + dc
                
            else:
                res += c

            pat = pat[1:]
            if len(pat) == 0: break
            c = pat[0]
        
        return res, pat
    
    return REGEX_DEFAULT_COLOR + color_segment(pattern)[0] + "\033[0m"

def colorize_string(string:str):
    
    colored = STRING_DEFAULT_COLOR

    while string != "":
        if m := re.match(r"\\\d{1,3}", string):
            colored += f"{STRING_ESCAPED_COLOR}{m.group()}{STRING_DEFAULT_COLOR}"
            string = string.replace(m.group(), "", 1)
            
        elif m := re.match(r"\\.", string):
            colored += f"{STRING_ESCAPED_COLOR}{m.group()}{STRING_DEFAULT_COLOR}"
            string = string[2:]
            
        elif m := re.match(r"\{[a-zA-Z0-9_]*\}", string):
            colored += f"{STRING_BRACKET_COLOR}{m.group()}{STRING_DEFAULT_COLOR}"
            string = string.replace(m.group(), "", 1)
            
        else:
            colored += string[0]
            string = string[1:]

    colored += "\033[0m"

    #print(f"colorize_string: {colored=}")

    return colored
    
def colorize_number(number):
    return f"{NUMBER_COLOR}{number}\033[0m"

def colorize_lexer_literals(text:str):

    colored = ""
    
    for line in text.split("\n"):
        indent = re.match(r" *", line).group()
        #print(f"indent: '{indent}' ({len(indent)})")
        line = line.strip()
        sub = indent
        if "->" in line:
            #print("has arrow")
            
            c, p = line.split("->")
            if c.strip():
                #print("has char")
                sub += f"{LEXER_L_CHAR_COLOR}{c.strip()} "
                line = p.strip()
                
            line = line.replace("->", "")
            sub += f"{LEXER_L_ARROW_COLOR}-> "
            if "?" in line:
                #print("has error")
                path, err = line.split("?")
                path = path.strip()
                err = err.strip()
                sub += f"{LEXER_L_REDIRECT_COLOR}{path} {LEXER_L_ERROR_COLOR}?{err}\033[0m"
                
            else:
                #print("no error")
                sub += f"{LEXER_L_REDIRECT_COLOR}{line.strip()}\033[0m"
                
            colored += f"{sub}\n"

        elif " " in line:
            #print("char token")
            char, token = line.split(" ")
            colored += f"{indent}{LEXER_L_CHAR_COLOR}{char} {TOKEN_COLOR}{token}\033[0m\n"

        elif len(line) == 1:
            #print("char")
            colored += f"{indent}{LEXER_L_CHAR_COLOR}{line}\033[0m\n"
            
        else:
            #print("token")
            colored += f"{indent}{TOKEN_COLOR}{line}\033[0m\n"
    
    return colored.strip()

def colorize_flags(flags:str, hint:str=""):
    """
    `hint` can be:  
    "lexer" or "parser"
    or anything to color flags using smart-colorize
    """
    if flags.strip() == "": return ""
    colored = []
    
    for flag in flags.split(" "):
        #print(f"FLAG: {flag}")
        sub = ""
        if ":" in flag:
            #print("':' in flag")
            f, p = flag.split(":", 1)
            #print(f"{f=} | {p=}")
            sub += f"{FLAG_COLOR}{f}:"
            if hint.lower() == "lexer":
                sub += colorize_regex(p)
                
            elif hint.lower() == "parser":
                sub += colorize_nodes(p)
                
            else:
                sub += smart_colorize(p)
                
        else:
            #print("':' NOT in flag")
            sub += f"{FLAG_COLOR}{flag}\033[0m"
            
        #print(f"{sub=} ({sub})")
        colored.append(sub)

    return " ".join(colored).strip()
        
def colorize_lexer_patterns(text:str):

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
                colored += f"{RULE_NAME_COLOR}{rule_name}: {colorize_flags(flags, 'lexer')}\n"
            else:
                colored += f"{RULE_NAME_COLOR}{line}\033[0m\n"

        elif line.startswith(">>>"): # hc
            line = line.replace(">>>", "", 1).strip()
            colored += f"{indent}{LEXER_P_HC_ARROW_COLOR}>>> {colorize_regex(line)}\n"

        elif line.startswith(">->"): # hr
            line = line.replace(">->", "", 1).strip()
            colored += f"{indent}{LEXER_P_HR_ARROW_COLOR}>-> {colorize_regex(line)}\n"

        elif line.startswith(">>"): # sr
            line = line.replace(">>", "", 1).strip()
            colored += f"{indent}{LEXER_P_SR_ARROW_COLOR}>> {colorize_regex(line)}\n"

        elif line.startswith("->"):
            colored += f"{indent}{colorize_lexer_literals(line)}\n"

        else:
            if " " in line:
                token, flags = line.split(" ", 1)
                colored += f"{indent}{TOKEN_COLOR}{token}  {colorize_flags(flags.strip(), 'lexer')}\n"
            else:
                colored += f"{indent}{TOKEN_COLOR}{line}\033[0m\n"
            
    return colored.strip()

def colorize_lexer(text:str):
    text = text.strip()
    colored = ""
    if text.startswith("@Lexer"):
        text = text.replace("@Lexer", "", 1).strip()
        colored += f"{SEGMENT_LABEL_COLOR}@Lexer\033[0m\n"
    if text.startswith("#!literals"):
        text = text.replace("#!literals", "", 1).strip()
        colored += f"{SUBSEGMENT_LABEL_COLOR}#!literals\033[0m\n"
        if "\n#!patterns" in text:
            lit, pat = text.split("\n#!patterns")
            lit = lit.strip()
            pat = pat.strip()
            colored += colorize_lexer_literals(lit)
            colored += f"\n{SUBSEGMENT_LABEL_COLOR}#!patterns\033[0m\n"
            colored += colorize_lexer_patterns(pat)
            return colored.strip()

        else:
            return (colored + colorize_lexer_literals(text)).strip()

    elif text.startswith("#!patterns"):
        text = text.replace("#!patterns", "", 1).strip()
        colored += f"{SUBSEGMENT_LABEL_COLOR}#!patterns\033[0m\n"
        if "\n#!literals" in text:
            pat, lit = text.split("\n#!literals")
            pat = pat.strip()
            lit = lit.strip()
            colored += colorize_lexer_patterns(pat)
            colored += f"\n{SUBSEGMENT_LABEL_COLOR}#!literals\033[0m\n"
            colored += colorize_lexer_literals(lit)
            return colored.strip()
        
        else:
            return (colored + colorize_lexer_patterns(text)).strip()

    return text


def colorize_nodes(text:str):

    colored = ""

    for line in text.split("\n"):
        line = line.strip()
        if "(" in line:
            name, args = line.replace(")", "").split("(")
            name = name.strip()
            args = args.split(",")
            args = [arg.strip() for arg in args]
            args = ARGS_COLOR + (f"{SYMBOL_COLOR}, {ARGS_COLOR}".join(args))
            colored += f"{NODE_COLOR}{name}{SYMBOL_COLOR}({args}{SYMBOL_COLOR})\033[0m\n"

        else:
            colored += f"{NODE_COLOR}{line}\033[0m\n"
    
    return colored.strip()

def colorize_parser(text:str):

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
                colored += f"{RULE_NAME_COLOR}{line.split(' ',  1)[0]} {NODE_COLOR}{line.split(' ', 1)[1]}\033[0m\n"
            else:
                colored += f"{RULE_NAME_COLOR}{line}\033[0m\n"

        else:
            sub = indent
            if not line.startswith("|") and "|" in line:
                node = line.split("|", 1)[0].strip()
                line = line.split("|", 1)[1].strip()
                sub += f"{NODE_COLOR}{node} {REGEX_DEFAULT_COLOR}| "
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
                _sub = REGEX_DEFAULT_COLOR

                while piece != "":
                    if m := re.match(r"<[^>]+>", piece):
                        m = m.group()
                        if ":" in m:
                            _sub += colorize_regex(m).replace(REGEX_DEFAULT_COLOR, TOKEN_COLOR).replace(":", f":{TOKEN_VALUE_COLOR}").replace(">", f"{TOKEN_COLOR}>{REGEX_DEFAULT_COLOR}")
                        else:
                            _sub += colorize_regex(m).replace(REGEX_DEFAULT_COLOR, TOKEN_COLOR) + REGEX_DEFAULT_COLOR
                        piece = piece.replace(m, "", 1)
                    elif m := re.match(r"\[[^\]]+\]", piece):
                        m = m.group()
                        _sub += f"{RULE_REF_COLOR}{m}{REGEX_DEFAULT_COLOR}"
                        piece = piece.replace(m, "", 1)
                    elif m := re.match(r"[a-zA-Z_][a-zA-Z0-9_]*:", piece):
                        m = m.group()
                        _sub += f"{CAPTURE_COLOR}{m}{REGEX_DEFAULT_COLOR}"
                        piece = piece.replace(m, "", 1)
                    elif m := re.match(r"\{\d+(,\d*)?\}", piece):
                        m = m.group()
                        _sub += f"{REGEX_QUANTIFIER_COLOR}{m}{REGEX_DEFAULT_COLOR}"
                        piece = piece.replace(m, "", 1)
                    elif piece[0] in "+*?":
                        _sub += f"{REGEX_QUANTIFIER_COLOR}{piece[0]}{REGEX_DEFAULT_COLOR}"
                        piece = piece[1:]
                    else:
                        _sub += piece[0]
                        piece = piece[1:]

                col.append(_sub)
            
            colored += sub + (" ".join(col)) + "  " + FLAG_COLOR + colorize_flags(flags or "", 'parser') + "\033[0m\n"
    
    return colored.strip()

def colorize_json(obj:dict, indent=2):
    if isinstance(obj, dict):
        string = json.dumps(obj, indent=indent)
    elif isinstance(obj, str):
        string = obj

    colored = ""

    is_key = True

    #print(f"coloring json: '{string}'")
    for line in string.split("\n"):
        indent = re.match(" *", line).group()
        line = line.strip()

        colored += indent

        while line != "":
            #print(f"line: {line}")
            #print(f"{colored=}")

            if line.startswith("{") or line.startswith(":") or line.startswith("}") or line.startswith(","):
                colored += f"{SYMBOL_COLOR}{line[0]}\033[0m"
                line = line[1:]

            elif m := re.match(r"(\"((\\.)*[^\"\\]*)*\"|\'((\\.)*[^\'\\]*)*\')", line):
                m = m.group()
                line = line.replace(m, "", 1)
                if line.strip().startswith(":"):
                    colored += smart_colorize(m, ["regex", "string"]).replace(STRING_DEFAULT_COLOR, JSON_KEY_COLOR).replace(STRING_ESCAPED_COLOR, JSON_KEY_ESCAPED_COLOR)
                else:
                    colored += smart_colorize(m, ["regex", "string", "redirect"]) # string/regex

            elif m := re.match(r"((0b|0B|0o|0O|0e|0E)?\d+(\.\d+)?|\.\d+|(0x|0X)([0-9a-fA-F]+(_[0-9a-fA-F]+)*)|true|false|null)", line):
                m = m.group()
                line = line.replace(m, "", 1)
                colored += colorize_number(m)

            else:
                colored += line[0]
                line = line[1:]

        colored += "\n"

    return colored.strip()

def smart_colorize(text:str, lock=[]):
    # automatically detect the best coloring method?

    # detection methods:
    # count occurences of symbols/keywords?
    # check syntax structuring?
    # check for sector flags? (@Lexer, @Parser, ...)

    # basically, machine learning

    if isinstance(text, dict):
        if (lock == [] or "json" in lock):
            return colorize_json(text)
        else:
            text = str(text)

    if text.strip().startswith("@Lexer") and (lock == [] or "lexer" in lock):
        return colorize_lexer(text)

    elif text.strip().startswith("@Parser") and (lock == [] or "parser" in lock):
        return colorize_parser(text)

    elif re.fullmatch(r"((0b|0B|0e|0E|0o|0O)?\d+(\.\d+)?|\.\d+|(0x|0X)([0-9a-fA-F]+(_[0-9a-fA-F]+)*))", text) and (lock == [] or "number" in lock):
        return colorize_number(text)

    elif re.fullmatch(r"\"([a-zA-Z_][a-zA-Z0-9_]*(/\-/[a-zA-Z_][a-zA-Z0-9_]*)+)\"", text) and (lock == [] or "redirect" in lock):
        return f"{LEXER_L_REDIRECT_COLOR}{text}\033[0m"

    if "{" in text and "}" in text and ":" in text and (lock == [] or "json" in lock):
        try: # if json syntax is met, then it's most likely json
            json.loads(text) # this calls just to see if an error is thrown
            return colorize_json(text)
        except json.JSONDecodeError as e:
            pass #print(f"ERROR: {e}")

    # # json: occurances of "{", ":", and "}"
    # json_chance = text.count("{") +\
    #     text.count(":") +\
    #     text.count("}")
    
    # lexer: appearence of sub sectors + arrow occurances + pattern type declarations + redirect seperators + syntax patterns
    lexer_chance = text.count("#!literals") +\
        text.count("#!patterns") +\
        text.count("->") +\
        text.count(">>") +\
        text.count("/-/") +\
        len(re.findall(r"(\n.\n|. \w+|. \-> [a-zA-Z_][a-zA-Z0-9_]*(/\-/[a-zA-Z_][a-zA-Z0-9_]*)*)", text)) if (lock == [] or "lexer" in lock) else 0
    
    # parser: occurances of pattern declarations "|" + occurances of tokens + occurances of rule references + rule name/capture occurances
    parser_chance = len(re.findall(r"\n *\| ", text)) +\
        len(re.findall(r"\n *[a-zA-Z_][a-zA-Z0-9_]* \| ", text)) +\
        len(re.findall(r"<\([^>]\)>", text)) +\
        len(re.findall(r"\[[a-zA-Z_][a-zA-Z0-9_\-]*\]", text)) +\
        len(re.findall(r"\b\w+:", text)) if (lock == [] or "parser" in lock) else 0
    
    # regex: double backslash char + backslash escapes + regex quantifiers, anchors, and logic + set occurances + difference of "(" to ")" + "..." occurances - literal words seperated with spaces
    regex_chance = len(re.findall(r"(\\\\.|\\.|\^|\.|\*|\+|\?|\||\[[^\]]+\]|\{\d+(,\d*)?\})", text)) +\
        (text.count("(") - text.count(")")) +\
        text.count("...") -\
        len(re.findall(r"( \w+ ?| ?\w+ )", text)) if (lock == [] or "regex" in lock) else 0
    
    #string: starts/ends correctly + backslash escapes + "{}" occurances + literal words seperated with spaces - regex quanifiers
    string_chance = int(text.startswith(("f\"", "\"", "f'", "'"))) +\
        int(text.endswith(("'", "\""))) +\
        len(re.findall(r"(\\.|\{[a-zA-Z0-9_]*\})", text)) +\
        len(re.findall(r"( \w+ ?| ?\w+ )", text)) -\
        len(re.findall(r"(\*\?\+|\{\d+(,\d*)?\})", text)) if (lock == [] or "string" in lock) else 0

    print(f"lexer:{lexer_chance}  parser:{parser_chance}  regex:{regex_chance}  string:{string_chance}")

    total = lexer_chance + parser_chance + regex_chance + string_chance

    if total == 0:
        return text

    lexer_percent = round(lexer_chance/total * 100, 2)
    parser_percent = round(parser_chance/total * 100, 2)
    regex_percent = round(regex_chance/total * 100, 2)
    string_percent = round(string_chance/total * 100, 2)

    print(f"lexer:{lexer_percent}%  parser:{parser_percent}%  regex:{regex_percent}%  string:{string_percent}%")

    results = get_largest([
        [lexer_percent, colorize_lexer],
        [parser_percent, colorize_parser],
        [string_percent, colorize_string],
        [regex_percent, colorize_regex],
    ])
    print(results)

    return results[0](text)


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
lexer_test = f"""\
@Lexer
#!literals
{lexer_literal_test}

#!patterns
{lexer_pattern_test}\
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
json_test = {
    "string key": {
        "some list": [1, 2, 3, "four", 5.0],
        "regex": "(~/.../.../~)",
        "binary": 0b10101,
        "hex": 0x0fa
    },
    12.5: {
        "path-val": "patterns/-/string",
        True: False,
        "wut? ^": None
    }
}

def main():

    #print(colorize_regex(regex_test))
    
    #print(colorize_string(string_test))

    #print(colorize_number(number_test))
    
    #print(colorize_lexer_literals(lexer_literal_test))

    #print(colorize_lexer_patterns(lexer_pattern_test))

    #print(colorize_lexer(lexer_test))

    #print(colorize_nodes(node_test))

    #print(colorize_parser(parser_test))

    print(smart_colorize(json_test))
    

    # cmd = ""
    # while cmd != "exit()":
    #     cmd = input(": ")
    #     if cmd.strip() == "": continue

    #     print(smart_colorize(cmd))

    return

if __name__ == "__main__":
    main()
