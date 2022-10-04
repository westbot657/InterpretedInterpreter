'''
import re


class DebugPrint:
    #__slots__ = ("name", "active", "color")

    def __init__(self, name, r, g, b):
        self.name = name
        self.active = False
        self.color = f"\033[38;2;{r};{g};{b}m"
        self.disabled_ = []

    def toggle(self, x=None):
        if x:
            if x in self.disabled_:
                self.disabled_.remove(x)
            else:
                self.disabled_.append(x)
        else:
            self.active = not self.active
    
    def __call__(self, *args, **kwargs):
        if len(args) == 0: return
        x = kwargs.get("x", None)
        if x: kwargs.pop("x")
        c = kwargs.get("c", None)
        if c:
            kwargs.pop("c")
            c = f"\033[38;2;{c[0]};{c[1]};{c[2]}m"
        else: c = ""
        if self.active and (x == None or x not in self.disabled_):
            args = list(args)
            args.insert(0, f"{self.color}[{self.name}]\033[0m: {c}")
            args.append("\033[0m")
            print(*args, **kwargs)
        if len(args) == 1:
            return args[0]
        else:
            return tuple(args)

tprint = DebugPrint("Tree", 10, 200, 10)
class Tree:
    def __init__(self, init={}):
        self.tree = init
        self.current_branch = self.tree
        self.current_branch_str = ""
        self.locked = False

    def goto(self, path):
        if isinstance(path, list):
            path = "/-/".join(path)
        self.current_branch_str = path
        pieces = path.split("/-/")
        self.current_branch = self.tree
        tprint(f"goto: '{path}'", x="movement")
        for p in pieces:
            if b := self.current_branch.get(p, None):
                if not isinstance(b, dict):
                    raise Exception(f"path '{path}' is not valid")
                self.current_branch = b
            else:
                if self.locked: raise Exception(f"path does not exist: '{path}'")
                self.current_branch.update({p: {}})
                self.current_branch = self.current_branch.get(p)

        # if self.get_branch_name() == "class-def" and self.locked:
        #     input()
    
    def lock(self):
        self.locked = True
    
    def get_path(self):
        if self.current_branch_str == "": x = []
        x = self.current_branch_str.split("/-/")
        tprint(f"get-path: '{'/-/'.join(x)}'")
        return x

    def get_branch_name(self):
        
        tprint("get-branch-name: (next get-path last item)")
        x = self.get_path()
        if len(x) == 0: return ""
        return x[-1]
    
    def into(self, path):
        if isinstance(path, str): path = path.split("/-/")
        tprint(f"into: '{'/-/'.join(path)}'", x="movement")
        self.goto(self.get_path() + path)

    def into_raw(self, key):
        tprint(f"into-raw: '{key}'", x="movement")
        self.current_branch = self.current_branch.get(key)
    
    def back_out(self):
        path = self.get_path()
        tprint("back-out! (next goto)", x="movement")
        if len(path) > 1:
            path.pop(-1)
            self.goto(path)

    def set(self, key, value):
        tprint(f"setting '{key}' to: {value}", x="get/set")
        self.current_branch.update({key: value})

    def get(self, key):
        tprint(f"get: getting '{key}' from current branch", x="get/set")
        return self.current_branch.get(key)

    def contains(self, key):
        x = key in self.current_branch.keys()
        tprint(f"contains: 'key' => {x}", x="get/set")
        return x
    
    def into_set(self, key, value:dict):
        tprint(f"into-set: valid value? {isinstance(value, dict)}")
        assert isinstance(value, dict)
        
        self.set(key, value)
        self.into(key)

literal_raw = """
#!literals
>
    >
        > CLASSDEF
        = RBITSHIFTEQ
        RBITSHIFT
    = GTE
    GT
~
    / -> patterns/-/regex
    TILDE
"""
literl_struct = {
    ">": {
        "value": "GT",
        ">": {
            "value": "RBITSHIFT",
            ">": {
                "value": "CLASSDEF"
            },
            "=": {
                "value": "RBITSHIFTEQ"
            }
        },
        "=": {
            "value": "GTE"
        }
    },
    "~": {
        "value": "TILDE",
        "/": {
            "redirect": {
                "target": "patterns/-/regex",
                "error": None
            }
        }
    }
}

patterns_raw = """
#!patterns
number: #redirect-from:[0-9]
    >>> ([1-9][_0-9]*|(0+_?)+)
        >>> (\.[0-9][0-9_]*)
            FLOAT
        >>> (x[0-9][0-9_]*)
            BASENUM
        INT

string: #redirect-only
    >> ("...")
    >> ('...')
    >> (f"...")
    >> (f'...')
    STRING

regex: #redirect-only
    >> (~/.../.../~)
    >> (~/.../~)
    >> (~/~)
    REGEX

    
"""

pattern_struct = {
    "number": {
        "flags": {
            "redirect-from": r"[0-9]"
        },
        r"([1-9][_0-9]*|(0+_?)+)": {
            "value": "INT",
            r"(\.[0-9][0-9_]*)": {
                "value": "FLOAT"
            },
            r"(x[0-9][0-9_]*)": {
                "value": "BASENUM"
            }
        }
    },
    "string": {
        "flags": {
            "redirect-only": None
        },
        "soft-matches": [
            r"(\"...\")",
            r"('...')",
            r"(f\"...\")",
            r"(f'...')"
        ],
        "value": "STRING"
    }
}

class Segmentor:

    def __init__(self, text):
        self.text = text
        self.ErrorSegment = ""
        self.LexerSegment = ""
        self.NodesSegment = ""
        self.ParserSegment = ""
        self.ObjectsSegment = ""
        self.InterpreterSegment = ""
        self.CodeSegment = ""

        self.UndeterminedSegment = ""

    def segment(self):
        lines = self.text.split("\n")

        build = []
        _segment = "UndeterminedSegment"
        for line in lines:
            if line.strip() == "@Lexer":
                setattr(self, _segment, "\n".join(build))
                build = []
                _segment = "LexerSegment"
            elif line.strip() == "@Nodes":
                setattr(self, _segment, "\n".join(build))
                build = []
                _segment = "NodesSegment"
            elif line.strip() == "@Errors":
                setattr(self, _segment, "\n".join(build))
                build = []
                _segment = "ErrorSegment"
            elif line.strip() == "@Parser":
                setattr(self, _segment, "\n".join(build))
                build = []
                _segment = "ParserSegment"
            elif line.strip() == "@Objects":
                setattr(self, _segment, "\n".join(build))
                build = []
                _segment = "ObjectsSegment"
            elif line.strip() == "@Interpreter":
                setattr(self, _segment, "\n".join(build))
                build = []
                _segment = "InterpreterSegment"
            elif line.strip() == "@Code":
                setattr(self, _segment, "\n".join(build))
                build = []
                _segment = "CodeSegment"
            else:
                build.append(line)

        if build:
            setattr(self, _segment, "\n".join(build))

lbprint = DebugPrint("LexerBuilder", 200, 0, 50)

class LexerBuilder:

    def __init__(self, text):
        self.text = text
        self.tree = Tree({"literals": {"\n": {"value": "NEWLINE"}}, "patterns": {}})

    def parse_flags(self, raw:str) -> dict:
        flags = {}
        curr = raw
        lbprint(f"parse-flags: '{raw}'", x="parse")
        while curr != "":
            if curr.startswith("#"): # this should always be true on first runthrough
                curr = curr[1:]
                flag_name = re.match(r"[\w\-]+", curr).group()
                curr = curr.replace(flag_name, "", 1)
                if curr.startswith(":"):
                    curr = curr[1:]
                    flag_value = curr.split(" ", 1)[0]
                    curr = curr.replace(flag_value, "", 1).strip()
                else:
                    flag_value = None
                    curr = curr.strip()
                flags.update({flag_name: flag_value})
        lbprint(f"parse-flags: {flags=}")
        return flags

    def _gen_pattern(self, char:str) -> str:
        """
        generate a regex pattern that accepts all characters except for un-escaped `char` (hopefully)
        """
        chars = {
            "\\": r"\\\\",
            "|": r"\|",
            "?": r"\?",
            "*": r"\*",
            "(": r"\(",
            ")": r"\)",
            "[": r"\[",
            "]": r"\]",
            "{": r"\{",
            "}": r"\}",
            "$": r"\$",
            "^": r"\^",
            "+": r"\+",
            "-": r"\-",
            ".": r"\."
        }

        c = chars.get(char, char)
        
        return f"(((\\\\.)*[^{c}\\\\]*)*)"
    
    def parse_pattern(self, pattern:str) -> str:
        #idx = 0
        escaped = False
        prev_chars = "" # ?...  \...
        result = ""
        lbprint(f"parse-pattern: '{pattern}'", x="parse")
        for c in pattern:
            #print(f"----> {prev_chars=}")
            if len(prev_chars) > 4:
                result += prev_chars[0]
                prev_chars = prev_chars[1:]

            if prev_chars.startswith("..."):
                if len(prev_chars) == 3:
                    prev_chars += c
                    continue
                v = prev_chars[3]
                #print(f"generating pattern for '{v}'")
                result += self._gen_pattern(v) + v
                prev_chars = c
                #print(f"{prev_chars=}")
                continue
                
            if escaped:
                result += prev_chars
                prev_chars = c
                escaped = False
                continue
            
            if c == "\\" and not escaped:
                escaped = True
            else:
                escaped = False
                
            prev_chars += c
        lbprint(f"parse-pattern: prev chars is left as: {prev_chars}", x="gen")

        if prev_chars.startswith("...") and len(prev_chars) == 4:
            v = prev_chars[3]
            lbprint(f"parse-pattern: generating pattern for '{v}'", x="gen")
            result += self._gen_pattern(v) + v
            prev_chars = ""
            lbprint(f"parse-pattern: {prev_chars=}", x="gen")
        
        
        return result + prev_chars
    
    def build(self) -> Tree:
        current_subsec = ""
        for line_ in self.text.split("\n"):
            line = line_.strip()
            if line == "": continue
            
            if line == "#!literals":
                current_subsec = "literals"
                self.tree.goto("literals")
            elif line == "#!patterns":
                current_subsec = "patterns"
                self.tree.goto("patterns")

            elif current_subsec == "literals":
                pieces = re.split(r" +", line)
                if len(pieces) == 1: # either a char or an end-value
                    p1 = pieces[0]
                    if len(p1) == 1: # char
                        self.tree.into_set(p1, {})
                    else:
                        self.tree.set("value", p1)
                        self.tree.back_out()

                elif len(pieces) == 2: # one-line rule or errorless end-redirect
                    p1, p2 = pieces
                    if p1 == "->": # redirect without error
                        self.tree.set("redirect", {"target": p2, "error": None})
                    else: # one-line rule
                        self.tree.set(p1, {"value": p2})

                elif len(pieces) == 3: # end-redirect with error or one-line errorless redirect rule
                    p1, p2, p3 = pieces
                    if p1 == "->": # end-redirect with error
                        self.tree.set("redirect", {"target": p2, "error": p3})
                        self.tree.back_out()
                    elif p2 == "->": # one-line errorless redirect rule
                        self.tree.set(p1, {"redirect": {"target": p3, "error": None}})
                    else:
                        raise Exception(f"could not parse: '{' '.join(pieces)}'")
                elif len(pieces) == 4: # one-line redirect rule with error
                    p1, p2, p3, p4 = pieces
                    if p2 == "->" and p4.startswith("?"): # just make sure syntax is correct(ish) before continuing
                        self.tree.set(p1, {"redirect": {"target": p3, "error": p4}})
                    else:
                        raise Exception(f"could not parse: '{' '.join(pieces)}'")

                else:
                    raise Exception(f"could not parse: '{' '.join(pieces)}'")
            
            elif current_subsec == "patterns":
                if (not line_.startswith(" ")) and line.split(" ")[0].endswith(":"): # pattern rule name, possibly with flag(s)
                    self.tree.goto("patterns")
                    rule_name = line.split(":", 1)[0]
                    flags_raw = ':'.join(line.split(":", 1)[1:]).strip()
                    flags = self.parse_flags(flags_raw)
                    self.tree.into_set(rule_name, {"flags": flags})
                elif line.startswith(">>>"): # hard-continuation-match
                    if self.tree.get_branch_name() != "matches":
                        self.tree.into("matches")
                    pattern = self.parse_pattern(line.replace(">>>", "", 1).strip())
                    self.tree.into(pattern)
                    self.tree.set("type", "hc-match")
                    #if self.tree.get_branch_name() in ["hc-match", "hr-match", "sc-match"]: self.tree.back_out()
                    # self.tree.into("hc-match")
                    # pattern = self.parse_pattern(line.replace(">>>", "", 1).strip())
                    # self.tree.into(pattern)
                    
                elif line.startswith(">->"): # hard-reset-match
                    # if self.tree.get_branch_name() in ["hc-match", "hr-match", "sc-match"]: self.tree.back_out()
                    # self.tree.into("hr-match")
                    if self.tree.get_branch_name() != "matches":
                        self.tree.into("matches")
                    pattern = self.parse_pattern(line.replace(">->", "", 1).strip())
                    self.tree.into(pattern)
                    self.tree.set("type", "hr-match")
                    
                elif line.startswith(">>"): # soft-continuation-match
                    if self.tree.get_branch_name() != "matches":
                        self.tree.into("matches")
                    # if not self.tree.contains("sc-match"):
                    #     self.tree.set("sc-match", [])
                    pattern = self.parse_pattern(line.replace(">>", "", 1).strip())
                    
                    # self.tree.get("sc-match").append(pattern)
                    self.tree.into(pattern)
                    self.tree.set("type", "sr-match")
                    self.tree.back_out()

                elif len(line.split(" ")) == 3: # -> target error
                    if self.tree.get_branch_name() == "matches": self.tree.back_out()
                    l1, l2, l3 = line.split(" ")
                    if l1 == "->":
                        self.tree.set("redirect", {"target": l2, "error": l3})
                        self.tree.back_out()
                        
                    else:
                        raise Exception(f"unrecognized in lexer rules: '{line}'")
                    
                elif len(line.split(" ")) == 2: # most likely: <tok-type> <flag>
                    if self.tree.get_branch_name() == "matches": self.tree.back_out()
                    l1, l2 = line.split(" ")
                    if l2.startswith("#"):
                        self.tree.set("value", l1)
                        self.tree.set("flags", [l2])
                        self.tree.back_out()
                        #if self.tree.get_branch_name() in ["hc-match", "hr-match", "sc-match"]: self.tree.back_out()

                    elif l1 == "->":
                        self.tree.set("redirect", {"target": l2, "error": None})
                        self.tree.back_out()
                        
                    else:
                        raise Exception(f"unrecognized in lexer rules: '{line}'")
                
                elif len(line.split(" ")) == 1: # <tok-type>
                    if self.tree.get_branch_name() == "matches": self.tree.back_out()
                    self.tree.set("value", line)
                    self.tree.back_out()
                    #if self.tree.get_branch_name() in ["hc-match", "hr-match", "sc-match"]: self.tree.back_out()
                    
        return self.tree

pprint = DebugPrint("Position", 255, 127, 0)
#pprint.toggle()
class Position:
    def __init__(self, index, column, line, file_name):
        self.index = index
        self.column = column
        self.line = line
        self.file_name = file_name

    def advance(self, char=None):
        pprint(f"[{id(self)}] advance: (1) idx:{self.index} col:{self.column} ln:{self.line} {char=}")
        self.index += 1
        self.column += 1

        if char == "\n":
            self.column = 0
            self.line += 1

        pprint(f"[{id(self)}] advance: (2) idx:{self.index} col:{self.column} ln:{self.line}")
        return self

    def __repr__(self):
        return f"ln {self.line}, col {self.column}"
    
    def copy(self):
        return Position(self.index, self.column, self.line, self.file_name)

class Token:
    def __init__(self, token_type, token_value=None, pos_start=None, pos_end=None, regex_value=False):
        self.token_type = token_type
        self.token_value = token_value
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.regex_value = regex_value

    def regex(self):
        if self.regex_value:
            return f"<{self.token_type}:{self.token_value}>"
        return f"<{self.token_type}>"

    def __repr__(self):
        if self.token_value:
            return f"{self.token_type}:{self.token_value}"# [{self.pos_start}-{self.pos_end}]"
        else:
            return f"{self.token_type}"# [{self.pos_start}-{self.pos_end}]"
    
    def __add__(self, other):
        if isinstance(other, Token):
            return Token(self.token_type, ((self.token_value or "") + (other.token_value or "") or None), self.pos_start, other.pos_end, self.regex_value or other.regex_value)
        elif isinstance(other, str):
            ps = self.pos_end.copy()
            for l in other:
                ps.advance(l)
            return Token(self.token_type, (self.token_value or "") + other, self.pos_start, ps, self.regex_value)

    def __radd__(self, other):
        if isinstance(other, str):
            return Token(self.token_type, other + (self.token_value or ""), self.pos_start, self.pos_end, self.regex_value)

lprint = DebugPrint("Lexer", 0, 200, 200)
#lprint.toggle()
class Lexer:

    def __init__(self, file_name, text, tree:Tree):
        self.reset(file_name, text)

        self.tree = tree

        self.redirect_from_checks = {}
        self.checks = []
        for key in tree.tree["patterns"].keys():
            tree.goto(f"patterns/-/{key}")
            if tree.contains("flags"):
                if pat := tree.current_branch["flags"].get("redirect-from", None):
                    self.redirect_from_checks.update({pat: f"patterns/-/{key}"})
                    self.checks.append(pat)

    def reset(self, file_name, text):
        self.text = text
        self.text_len = len(text)
        self.current_char = None
        self.pos = Position(-1, -1, 0, file_name)
        self.idx = -1
        self.diff = 0
        self._diff = 0
        self.advance()
    
    def formatError(self, error:str, failed_token=None):
        if error is None: return error
        if not error.startswith("?"): return error
        err_name = error.replace("?", "", 1)
        ft = ""
        if failed_token:
            ft = f": {failed_token}"
        return f"{err_name}: failed to generate token{ft}"
    
    def advance(self, n=1):
        while n >= 1:
            self.pos.advance(self.current_char)
            self.idx += 1
            if self.idx >= self.text_len:
                self.current_char = None
            else:
                self.current_char = self.text[self.idx]
    
            lprint(f"advance: {n=} text-length:{self.text_len}  current-char:{self.current_char}")
            n -= 1
            

    def gdx(self):
        return self.idx + self.diff
    
    def ghost_advance(self, n=1):
        lprint(f"ghost-advance: {n=} text-length:{self.text_len}", x="ghost")
        self.diff += n
        if self.gdx() < self.text_len:
            self.current_char = self.text[self.gdx()]
        else:
            self.current_char = None

    def ghost_save(self):
        lprint("ghost-save", x="ghost")
        self._diff = self.diff
    
    def ghost_reset(self):
        lprint("ghost-reset", x="ghost")
        self.diff = self._diff
        self._diff = 0
        if self.gdx() < self.text_len:
            self.current_char = self.text[self.gdx()]
        else:
            self.current_char = None

    def ghost_get(self):
        lprint(f"ghost-get: {self.diff}", x="ghost")
        return self.diff

    def ghost_set(self, val):
        lprint(f"ghost-set: {val}", x="ghost")
        self.ghost_reset()
        self.ghost_advance(val)
    
    def solidify(self):
        lprint("solidify", x="ghost")
        self.advance(self.diff)
        self.diff = 0
        self._diff = 0

    def text_from_ghost(self, length=None):
        x = self.gdx()
        if length:
            length = x+length
        lprint(f"text-from-ghost: (up to 30 chars) '{self.text[x:x+30]}'", x="ghost")
        return self.text[x:length]
        
    def text_from_real(self, length=None):
        if length:
            length = self.idx + length
        lprint(f"text-from-real: (up to 30 chars) '{self.text[self.idx:self.idx+30]}'")
        return self.text[self.idx:length]

    def _explore_pattern(self, rules):
        found_match = False
        soft_value = None
        
        if matches := rules.get("matches", None):
            lprint("exploring matches", x="ep")
            value = None
            for pattern in matches.keys():
                lprint(f"testing {pattern=} against text: {self.text_from_ghost()}", x="ep")
                if m := re.match(pattern, self.text_from_ghost()):
                    
                    pos_start = self.pos.copy()
                    m_rules = matches.get(pattern)
                    match_type = m_rules["type"] # either `hr-match`, `hc-match`, or `sr-match`
                    value = m.group()
                    lprint(f"found a match!  {value=}", x="ep")
                    n = self.ghost_get()
                    self.ghost_advance(len(value))
                    lprint(f"\033[38;2;20;200;20midx={self.pos.index}  ghost-offset={n}\033[0m", x="ep")
                    
                    if match_type == "sr-match" and not found_match:
                        lprint("match is an sr-match", x="ep")
                        soft_value = value, rules.get("value", False)
                        found_match = True
                        #self.solidify()
                        #break
                        continue
                    elif match_type == "hr-match":
                        lprint("match is an hr-match", x="ep")
                        found_match = True
                        lprint(f"exploring in {m_rules=}", x="ep")
                        #self.solidify()
                        self.ghost_reset() # <- uncommenting causes some kind of recursive loop that seems to not be able to hit the recursion limit
                        #self.ghost_set(n)
                        val, err = self._explore_pattern(m_rules)
                        #self.solidify()
                        lprint(f"{value=}  {val=}  {err=}", x="ep")
                        
                        if err == "#no-value":
                            value = ""
                            val.token_value = None
                            err = None
                        elif err == "#regex-value":
                            val.regex_value = True
                            err = None
                        elif err == "plz advance":
                            err = None
                            if value:
                                self.ghost_advance(len(value))
                        elif err:
                            lprint("\033[38;2;255;0;0m<--here?\033[0m", x="ep")
                            lprint(rules, x="ep")
                            lprint("\033[38;2;255;0;0m<--here?\033[0m", x="ep")
                            
                            if val_ := rules.get("value", None):
                                if flags := rules.get("flags", None):
                                    if "#no-value" in flags: value = None
                                self.solidify()
                                lprint(f"value!! {value=}", x="ep")
                                if value:
                                    self.ghost_advance(len(value))
                                else:
                                    self.ghost_advance()
                                return Token(val_, value, pos_start, self.pos.copy()), None
                            
                            
                            found_match = False
                            return val, self.formatError(err)
                        if val.token_value:
                            tok = val
                        else:
                            tok = value+val

                        #self.ghost_reset()
                        
                        tok.pos_start = pos_start
                        #self.solidify()
                        return tok, self.formatError(err)

                    elif match_type == "hc-match":
                        lprint("match is an hc-match", x="ep")
                        found_match = True
                        #self.solidify()
                        lprint(f"exploring {m_rules=}", x="ep")
                        val, err = self._explore_pattern(m_rules)
                        
                        #self.solidify()
                        lprint(f"{value=}  {val=}  {err=}", x="ep")

                        if err == "plz advance":
                            err = None
                            if value:
                                self.solidify()
                                #self.ghost_advance(len(value))
                            
                        elif err:
                            if val_ := m_rules.get("value", None):
                                if flags := m_rules.get("flags", None):
                                    if "#no-value" in flags: value = None
                                self.solidify()
                                return Token(val_, value, pos_start, self.pos.copy()), None
                            #found_match = False
                            self.ghost_reset()
                            return val, self.formatError(err)

                        tok = value + val
                        tok.pos_start = pos_start
                        lprint(f"{tok=}", x="ep")
                        flag = None
                        if flags := m_rules.get("flags", None):
                            flag = flags[0]
                        self.solidify()
                            
                        return tok, flag

            if soft_value:
                val, tok_type = soft_value
                lprint(f"using soft-match: {val=}  {tok_type=}", x="ep")
                #self.solidify()
                lprint("soft value", x="ep")
                if tok_type is False:
                    return val, f"No Token Type Given for value: {val}"
                self.solidify()
                ps = self.pos.copy()
                if val:
                    for l in val:
                        ps.advance(l)
                return Token(tok_type, val, self.pos.copy(), ps), None

            elif redirect := rules.get("redirect", None):
                self.ghost_reset()
                lprint("REDIRECT", x="ep")
                target = redirect["target"]
                error = redirect["error"]
                val, err = self.explore_pattern(target, solidify=False)
                if err:
                    if error:
                        return val, self.formatError(error)

                else:
                    self.solidify()
                return val, self.formatError(err)
            
            elif tok_type := rules.get("value", None):
                lprint(f"value?? {value=}")
                #self.solidify()
                #lprint("\033[38;2;20;255;20msolidifying position!\033[0m", x="ep")
                lprint(f"text-from-real: \033[38;2;200;30;30m'{self.text_from_real()}'\033[0m", x="ep")
                lprint(f"text-from-ghost: \033[38;2;200;30;30m'{self.text_from_ghost()}'\033[0m")
                pos_start = self.pos.copy()
                # if value:
                #     self.ghost_advance(len(value))
                # else:
                #     self.ghost_advance()
                return Token(tok_type, value, pos_start, self.pos.copy()), "plz advance"

            else:
                return None, "No Token Type Given!"

        elif redirect := rules.get("redirect", None):
            target = redirect["target"]
            error = redirect["error"]
            lprint(f"redirect!\n{self.pos.index}\n{self.text_from_ghost()}", x="ep")
            
            self.ghost_reset()
            lprint(f"after ghost-reset: {self.text_from_ghost()}", x="ep")
            val, err = self.explore_pattern(target, False)

            lprint(f"{val=}  {err=}", x="ep")
            
            if err:
                if error:
                    return None, self.formatError(error)
                elif tok_type := rules.get("value", None):
                    self.solidify()
                    return Token(tok_type, None, self.pos.copy(), self.pos.copy()), None
                    
            return val, self.formatError(err)

        elif tok_type := rules.get("value", None):
            lprint("raw value", x="ep")
            self.solidify()
            return Token(tok_type, None, self.pos.copy(), self.pos.copy()), None

        else:
            return None, f"No Value Error: {self.pos.copy()}"

    def explore_pattern(self, path, solidify=True):
        self.tree.goto(path)
        rules = self.tree.current_branch

        lprint(f"exploring '{path}'", x="ep")
        ret = self._explore_pattern(rules)
        if solidify:
            self.solidify()
        return ret

    def _explore_literal(self, branch):
        pos_start = self.pos.copy()
        lprint(f"{self.current_char=}", x="el")
        self.ghost_advance()
        for key in branch.keys():
            lprint(f"checking '{self.current_char}' against '{key}'", x="el")
            if self.current_char == key:
                lprint(f"exploring literal: '{self.current_char}'", x="el")
                val, err = self._explore_literal(branch[key])
                return val, self.formatError(err)
            elif key == "redirect":
                redirect = branch["redirect"]
                target = redirect["target"]
                error = redirect["error"]
                lprint("ghost reset", x="el")
                self.ghost_reset()
                val, err = self.explore_pattern(target)
                if err:
                    if error:
                        return val, self.formatError(error)
                lprint(f"{val=}, {err=}, {branch=}", x="el")
                return val, self.formatError(err)
            elif key == "value":
                lprint(f"value = {branch[key]}", x="el")
                return Token(branch[key], None, pos_start, self.pos.copy()), None
    
    def explore_literal(self, char):
        self.tree.goto("literals")
        if branch := self.tree.current_branch.get(char, None):
            lprint(f"exploring literal: '{char}'\n{branch=}", x="el")
            val, err = self._explore_literal(branch)
            self.solidify()
            return val, err

        else:
            return char, self.formatError("?InvalidCharacter")
    
    def make_tokens(self) -> list:
        tokens = []

        while self.current_char != None:
            lprint(f"\033[38;2;20;200;200m{self.pos.index=}   char={self.current_char}\033[0m", x="mt")
            if self.current_char == " ":
                #self.solidify()
                self.advance()
                continue
                
            for check in self.checks:
                if re.match(check, self.current_char):
                    val, err = self.explore_pattern(self.redirect_from_checks[check])
                    
                    if err:
                        return val, self.formatError(err)
                    tokens.append(val)
                    #self.advance()
                    break
            else:
                val, err = self.explore_literal(self.current_char)
                if err:
                    return val, self.formatError(err)
                tokens.append(val)

                #self.advance()

            #self.advance()

        tokens.append(Token("EOF", None, self.pos.copy(), self.pos.copy()))

        return tokens, None

Nprint = DebugPrint("Node", 0, 255, 255)
#Nprint.toggle()
class Node:
    _nodes = []

    class NodeInstance:

        def __init__(self, parent, **values):

            for v in parent.values:
                setattr(self, v, None)
            self._vals = [k for k in values.keys()]
            for key in self._vals:
                setattr(self, key, values[key])
            
            self._parent_node = parent
        
        def __repr__(self):
            res = []
            for v in self._vals:
                res.append(f"{v}={str(getattr(self, v))}")

            return f"{self._parent_node.name}({', '.join(res)})"

    @classmethod
    def get(cls, name):
        Nprint(f"looking for node: '{name}'")
        for node in cls._nodes:
            if node.name == name:
                return node
        return None
    
    def __init__(self, name, values:list):
        self.name = name
        self.values = values
        Node._nodes.append(self)

    def __call__(self, **kwargs):
        return Node.NodeInstance(self, **kwargs)
    
    def __repr__(self):
        return self.name + " " + str(self.values)

nbprint = DebugPrint("NodeBuilder", 0, 50, 200)
class NodeBuilder:

    def __init__(self, text):
        self.text = text

    def build(self):
        for line_ in self.text.split("\n"):
            line = line_.strip()
            if line == "": continue
            nbprint(f"{line=}")
            if "(" in line:
                name, vals = line.replace(")", "").split("(")
                name = name.strip()
                values = [v.strip() for v in vals.split(",")]
                nbprint(f"new node: {name} ({', '.join(values)})")

            else:
                name = line
                values = []
                nbprint(f"new node: {name}")

            Node(name, values)
        print(Node._nodes)
        
"""
@Nodes
Null                  # Converts to ~ Node { name="NullNode" }
Empty                               # Node { name="EmptyNode" }
Integer(value)                      # Node { name="IntegerNode", value=None }
Float(value)                        # Node { name="FloatNode", value=None }
Basenum(base, value)                # Node { name="BasenumNode", base=None, value=None }
String(value)                       # Node { name="StringNode", value=None }
Regex(pattern,flags)                # Node { name="RegexNode", pattern=None, flags=None }

"""



"""
parser rules:
```
@Parser
rule-name: NodeType                    # all patterns will be set as this node
    | <token> node_attribute:[rule]    # possible pattern to match against

rule:                                  # a rule that may give different node types
    NodeType | ...                     # pattern that if matched, givess the specified node type
    AltNodeType | ...                  # ^^
    | ...                              # pattern that is usually a single [rule], where that rule (or nested nodes) determines the given node
```

cases:
```
rule-name: (GlobalNode)?
    (AltNode)? | (pattern)
    ...
```
AltNode will override GlobalNode
putting *, ?, +, or {...} after a rule/token works the same as regex
using (...|...) works the same as regex

"""

"""
@Nodes
NullNode
BooleanNode(value)
BodyNode(statements)
ReturnNode(value)
BreakNode
ContinueNode
BinOpNode(left, op, right)
UnaryOpNode(op, value)
VarAssignNode(name, aliases, clamp, value)
ClampNode(types, nullable)

@Parser
statements: BodyNode
    | statements:[statement]*
statement:
    ReturnNode | <KEYWORD:return> value:[expr]?
    BreakNode | <KEYWORD:break>
    ContinueNode | <KEYWORD:continue>
    | [expr]
expr:
    BinOpNode | left:[comp-expr] op:<(AND|OR)> right:[comp-expr]
    | [comp-expr]
comp-expr:
    UnaryOpNode | op:<NOT> value:[comp-expr]
    BinOpNode | left:[arith-expr] op:<(EE|NE|GT|LT|GTE|LTE)> right:[arith-expr]
    | [arith-expr]
arith-expr:
    BinOpNode | left:[term] op:<(PLUS|MINUS)> right:[term]
    | [term]
var-def: VarAssignNode
    | <(VLINE|HASH|DOLLAR)>? name:<ID> (<ALIAS> aliases:<ID>)* <SEMICOLON>  #clamp:Clamp([],True) #value:Null
    | <(VLINE|HASH|DOLLAR)>? name:<ID> (<ALIAS> aliases:<ID>)* clamp:[clamp]? <EQ> value:[expr]
"""
parser_struct = {
    "statements": {
        "node": "Body",
        "patterns": {
            "0": {
                "pattern": "[statement]",
                "quantifier": "+",
                "capture": "statements"
            }
        }
    },
    "statement": {},
    "expr": {
        "patterns": {
            "0": {
                "0": {
                    "pattern": "[comp-expr]",
                    "capture": "left"
                },
                "1": {
                    "pattern": "<(AND|OR)>",
                    "capture": "op"
                },
                "2": {
                    "pattern": "[comp-expr]",
                    "capture": "right"
                },
                "node": "BinOp"
            }
        }
    },
    "var-def": {
        "node": "VarAssign",
        "patterns": {
            "0": {
                "0": {
                    "pattern": "<(VLINE|HASH|DOLLAR)>",
                    "quantifier": "?"
                },
                "1": {
                    "pattern": "<ID>",
                    "capture": "name"
                },
                "2": {
                    "0": {
                        "pattern": "<ALIAS>"
                    },
                    "1": {
                        "pattern": "<ID>",
                        "capture": "aliases"
                    },
                    "quantifier": "*"
                },
                "3": {
                    "pattern": "<SEMICOLON>"
                },
                "set-values": {
                    "clamp": "Clamp([],True)",
                    "value": "Null"
                }
            },
            "1": {
                "0": {
                    "pattern": "<(VLINE|HASH|DOLLAR)>",
                    "quantifier": "?"
                },
                "1": {
                    "pattern": "<ID>",
                    "capture": "name"
                },
                "2": {
                    "0": {
                        "pattern": "<ALIAS>"
                    },
                    "1": {
                        "pattern": "<ID>",
                        "capture": "aliases"
                    },
                    "quantifier": "*"
                },
                "3": {
                    "pattern": "[clamp]",
                    "capture": "clamp",
                    "quantifier": "?"
                },
                "4": {
                    "pattern": "<EQ>"
                },
                "5": {
                    "pattern": "[expr]",
                    "capture": "value"
                }
            }
        }
    }
}

pbprint = DebugPrint("ParserBuilder", 200, 10, 200)
class ParserBuilder:

    def __init__(self, text):
        self.text = text
        self.tree = Tree()
        self.entry_point = None

    def _parse(self, pattern):
        """
        returns a tuple of:
        list of pattern components
        and any leftover string or ""
        """
        result = []
        escaped = False
        curr = ""
        while pattern != "":

            if m := re.match("\\\\.", pattern):
                curr += pattern[0:2]
                pattern = pattern[2:]
                continue

            if " " in pattern or "<" in pattern or "[" in pattern:
                sec = pattern.split(" ")[0]
                if sec.count("(") == sec.count(")"):
                    result.append(sec)
                    pattern = pattern.replace(sec, "", 1)
                    if pattern == "":
                        break
                

            if pattern[0] == "(":
                result.append(curr.strip() or curr)
                curr = ""
                res, pattern = self._parse(pattern[1:])
                result.append(res)

            elif pattern[0] == ")":
                if curr:
                    return result + [curr.strip() or curr], pattern[1:]
                else:
                    return result, pattern[1:]

            else:
                curr += pattern[0]
                pattern = pattern[1:]

        if curr:
            result.append(curr.strip() or curr)
        return result, ""

    def format_components(self, components):
        index = 0
        pattern = {}
        # if len(components) == 1:
        #     comp = components[0]
        #     if (not re.match("\w+:", comp)) and (not comp.endswith(("?", "*", "+"))) and (not re.search("\\{\d+(,\d*)?\\}", comp)):
        #         return comp
        pbprint(f"format-components: {components}", x="format")
        for comp in components:
            if isinstance(comp, list):
                pbprint(f"format-components: component is a list: {comp}", x="format")
                pattern.update({str(index): self.format_components(comp)})
                
            elif isinstance(comp, str):
                if comp.strip() == "": continue
                pbprint(f"format-components: component is a string: {comp}", x="format")
                if m := re.match("\w+:", comp):
                    temp = {}
                    name = m.group().replace(":", "")
                    patt = comp.split(":", 1)[1]
                    if patt.endswith(("?", "*", "+")):
                        temp.update({"quantifier": patt[-1]})
                        patt = patt[:-1]
                    elif g := re.search("\\{\d+(,\d*)?\\}$", patt):
                        q = g.group()
                        patt = patt.replace(q, "")
                        temp.update({"quantifier": q})
                    temp.update({"pattern": patt, "capture": name})
                    pattern.update({str(index): temp})
                    pbprint(f"format-components: set pattern:{index} to: {temp}", x="format")

                elif comp.endswith(("?", "*", "+")) and comp not in ("?", "*", "+"):
                    pbprint(f"format-components: component has a quantifier: '{comp}'", x="format")
                    pattern.update({
                        str(index): {
                            "pattern": comp[:-1],
                            "quantifier": comp[-1]
                        }
                    })

                elif m := re.search("\\{\d+(,\d*)?\\}$", comp) and not re.match("\\{\d+(,\d*)?\\}", comp):
                    pbprint(f"format-components: components has a quantifier: '{comp}'", x="format")
                    pattern.update({
                        str(index): {
                            "pattern": comp.replace(m.group(), ""),
                            "quantifier": m.group()
                        }
                    })
                
                elif comp in ("?", "*", "+"):
                    pbprint(f"format-components: component is a quantifier: '{comp}'", x="format")
                    pattern[str(index-1)].update({"quantifier": comp})
                    index -= 1

                elif re.match("\\{\d+(,\d*)?\\}", comp):
                    pbprint(f"format-components: component is a quantifier: '{comp}'", x="format")
                    pattern[str(index-1)].update({"quantifier": comp})
                    index -= 1
                        
                else:
                    pbprint(f"format-components: set pattern:{index} to: '{comp}'", x="format")
                    pattern.update({str(index): comp})

            index += 1

        return pattern
    
    def build(self):
        index = 0
        for line_ in self.text.split("\n"):
            line = line_.strip()
            pieces = line.split(" ")

            if line.startswith("#!entry-point:"):

                self.entry_point = line.replace("#!entry-point:", "").strip()
                pbprint(f"entry-point: '{self.entry_point}'")
                continue
            
            if (not line_.startswith(" ")) and pieces[0].endswith(":"):
                if len(pieces) >= 1: # rule-name:
                    self.tree.goto(pieces[0].replace(":", ""))
                    index = 0

                if len(pieces) == 2: # rule-name: Node
                    self.tree.set("node", pieces[1])

                elif len(pieces) > 2:
                    raise Exception(f"un-recognized: '{line}'")

            elif len(pieces) >= 2:
                # | ...
                # altNode | ...
                alt = None
                if pieces[0] == "|":
                    pieces.pop(0) # remove '|'

                elif pieces[1] == "|":
                    alt = pieces.pop(0)
                    pieces.pop(0) # remove '|'

                res, _ = self._parse(" ".join(pieces))

                if "" in res: # this is where the pattern is seperated from the flags if present
                    i = res.index("")
                    components, flags = res[:i], res[i+1:]
                else:
                    flags = None
                    components = res

                if self.tree.get_branch_name() != "patterns":
                    self.tree.into("patterns")
                self.tree.set(str(index), self.format_components(components))
                if alt:
                    self.tree.into(str(index))
                    self.tree.set("node", alt)
                    self.tree.back_out()
                if flags:
                    self.tree.into(str(index))
                    self.tree.into("set-value")
                    for flag in flags:
                        self.tree.set(flag.split(":", 1)[0].replace("#", ""), flag.split(":", 1)[1])

                    self.tree.back_out()
                    self.tree.back_out()
                
                index += 1


Qprint = DebugPrint("Quantifier", 255, 255, 20)
#Qprint.toggle()
class Quantifier:

    def __init__(self, quant=None):
        self.current = 0
        self.min_val = 1
        self.max_val = 1
        self._valid = True
        if quant == None:
            pass # this way no error occures from trying to get NoneType.startswith
        elif quant == "?":
            self.min_val = 0
        elif quant == "*":
            self.min_val = 0
            self.max_val = -1
        elif quant == "+":
            self.min_val = 1
            self.max_val = -1
        elif quant.startswith("{") and quant.endswith("}"):
            quant = quant.replace("{", "").replace("}", "")
            if "," in quant:
                mn, mx = quant.split(",")
                self.min_val = int(mn)
                self.max_val = int(mx)
            else:
                self.min_val = self.max_val = int(quant)
        else:
            raise Exception(f"Invalid quantifier: '{quant}'")
        Qprint(f"new: '{quant}' ({self.min_val}:{self.max_val})", c=(255,255,0))

    def check(self, value):
        if value:
            self.next()
            if self.max_val == -1:
                if self.current < self.min_val:
                    Qprint(f"[{id(self)}] check: need more values! min:{self.min_val} current:{self.current}", x="check")
                    return "need"
                Qprint(f"[{id(self)}] check: valid value! min:{self.min_val} current:{self.current}", x="check")
                return "valid"
                
            elif self.current == self.max_val:
                Qprint(f"[{id(self)}] check: max values reached! {self.min_val}<={self.current}<={self.max_val}", x="check")
                return "done"

            elif self.current > self.max_val:
                Qprint(f"[{id(self)}] check: max values exceeded!? max:{self.max_val} current:{self.current}", x="check")
                raise Exception("quantifier went over!")

        else:
            if self.current < self.min_val:
                Qprint(f"[{id(self)}] check: not enough values! current:{self.current} min:{self.min_val}", x="check")
                return "not-enough"
            Qprint(f"[{id(self)}] check: quantifier satisfied! {self.min_val}<={self.current} max:{self.max_val}", x="check")
            return "done"

    def next(self):
        Qprint(f"[{id(self)}] next")
        self.current += 1

    def valid(self):
        if self.min_val <= self.current:
            if self.max_val == -1 or self.current <= self.max_val: return True
            else: return False
        else: return False

    def get_err(self): # if this is being called, there was an error
        if self.min_val <= self.current:
            return f"too many values given!? expected at most: {self.max_val} match{'es' * (self.max_val!=1)}"
        else:
            return f"not enough values! expected at least: {self.min_val} match{'es' * (self.min_val!=1)}"


Pprint = DebugPrint("Parser", 0, 220, 220)
Pprint.toggle()
class Parser:

    def __init__(self, tokens, builder):
        self.tree: Tree = builder.tree
        self.tree.lock() # locking the tree stops goto from creating new branches
        self.entry_point = builder.entry_point
        self.tokens = tokens
        self.tok_len = len(tokens)
        self.idx = -1
        self.diff = 0
        self._diff = 0
        self.ghost_stack = []
        self.current_tok = None
        Pprint(f"creating new Parser", x="init", c=(255,0,0))
        self.advance()

    def gdx(self):
        return self.idx + self.diff

    def advance(self, n=1):
        Pprint(f"advance: {n=}  current-token:{self.current_tok}", x="advance")
        while n >= 1:
            self.idx += 1
            if self.idx < self.tok_len:
                self.current_tok = self.tokens[self.idx]
            else:
                self.current_tok = self.tokens[-1] # this item should be EOF
            n -= 1
        Pprint(f"advance: current-token changed to: {self.current_tok}", x="advance")

    def ghost_advance(self, n=1):
        Pprint(f"ghost-advance: {n=}  current-token:{self.current_tok}", x="ghost")
        self.diff += n
        if self.idx + self.diff < self.tok_len:
            self.current_tok = self.tokens[self.idx + self.diff]
        else:
            self.current_tok = self.tokens[-1] # < EOF
        Pprint(f"ghost-advance: current-token changed to: {self.current_tok}", x="ghost")

    def ghost_save(self):
        self.ghost_stack.insert(0, self.diff)
        Pprint(f"ghost-save: stack:{self.ghost_stack}", x="ghost", c=(255,127,0))
    
    def ghost_unsave(self):
        if len(self.ghost_stack) > 0:
            self.ghost_stack.pop(0)

        Pprint(f"ghost-unsave: stack:{self.ghost_stack}", x="ghost", c=(255,127,0))

    def ghost_reset(self):
        Pprint(f"ghost-reset: current-token:{self.current_tok}", x="ghost")
        self.diff = self.ghost_stack.pop(0) if len(self.ghost_stack) > 0 else 0
        if self.gdx() < self.tok_len:
            self.current_tok = self.tokens[self.gdx()]
        else:
            self.current_tok = self.tokens[-1] # < EOF

        Pprint(f"ghost-reset: current-token changed to: {self.current_tok}", x="ghost")
        Pprint(f"ghost-reset: stack:{self.ghost_stack}", x="ghost", c=(255,127,0))

    def solidify(self):
        Pprint("solidify!", x="ghost")
        self.advance(self.diff)
        self.diff = 0
        self._diff = 0
        self.ghost_stack = []
    
    # def get_segment(self, start, endsegment_toks=["NEWLINE"]):
    #     seg = []
    #     Pprint("get-segment", c=(0,255,127))
    #     if start > self.tok_len:
    #         return []

    #     i = start
    #     while True:
    #         tok = self.tokens[i]
    #         seg.append(tok)
    #         if tok.token_type == "EOF" or tok.token_type in endsegment_toks:
    #             return seg
    #         i += 1
    #         if i > self.tok_len:
    #             raise Exception("no EOF found!")

    def parse(self): 
        self.tree.goto(self.entry_point)
        return self._parse()

    def _parse_node(self, node_str):
        node = None
        values = []
        name = ""
        Pprint(f"parsing-node: '{node_str}'", x="parse-node", c=(127,127,0))
        while node_str != "":
            
            if node_str[0] == "(":
                #name = node_str.split("(", 1)[0]
                node = Node.get(name)
                name = ""
                Pprint(f"current char is '(', {name=}, after='{node_str[1:]}'", x="parse-node")
                _node, node_str = self._parse_node(node_str[1:])
                values.append(_node)
                
            elif node_str[0] == ")":
                node_str = node_str[1:]
                if node_str[0] == ",": node_str = node_str[1:]
                Pprint(f"current char is ')', node is '{node.name}', {node_str=}", x="parse-node")
                return node(**dict(zip(node.values, values))), node_str

            elif node_str[0] == ",":
                _node = Node.get(name)()
                values.append(_node)
                Pprint(f"current char is ',', name is '{name}'", x="parse-node")
                name = ""
                node_str = node_str[1:]

            else:
                name += node_str[0]
                node_str = node_str[1:]

        if name:
            Pprint(f"making node: {name=}", x="parse-node", c=(0,200,0))
            return Node.get(name)(), None
        
    def parse_node(self, node_str):
        node, _ = self._parse_node(node_str)
        return node
    
    def explore_pattern(self, pattern, node):
        node = pattern.get("node", None) or node
        node_captures = {}
        set_values = {}
        val1 = None

        if self.tree.get_branch_name() in ["var-def", "alias"] and self.current_tok.token_type == "EQ":
            pass

        if not self.current_tok:
            return None, "EOF", "EOF"
        if self.current_tok.token_type == "EOF":
            return None, "EOF", "EOF"
        
        Pprint(f"exp-pattern: {node=}", x="exp")
        if set_vals := pattern.get("set-value", None):
            for key in set_vals:
                _node = self.parse_node(set_vals[key])
                Pprint(f"set-val: '{key}': {_node}", x="exp")
                set_values.update({key: _node})

        self.ghost_save() # 0 -> []  =>  0  [0]
        #do_unsave = True
        for i in list(pattern.keys()): # iterate through portions of a pattern
            Pprint(f"iteration key: '{i}'", x="exp")
            if i == "node": continue
            if i == "set-value": continue
            if i == "quantifier": continue
            patt = pattern[i]
            Pprint(f"current-tok: {self.current_tok}", c=(0,127,255))
            if isinstance(patt, str):
                Pprint(f"is string, pattern={patt}")
                if patt.startswith("[") and patt.endswith("]"):
                    branch = self.tree.get_path()
                    Pprint(f"saving branch: '{'/-/'.join(branch)}'")
                    self.tree.goto(patt.replace("[", "").replace("]", ""))
                    Pprint(f"moved to branch: '{'/-/'.join(self.tree.get_path())}', parsing", c=(0,255,255))
                    Pprint(f"contents of branch: {self.tree.current_branch}", c=(200,200,0))
                    #self.ghost_save()
                    value, error, eof = self._parse()
                    #if eof: return value, error, eof
                    
                    Pprint(f"returning to branch: '{'/-/'.join(branch)}'")
                    self.tree.goto(branch)
                    Pprint(f"{value=}  {error=}")
                    if error:
                        self.ghost_reset() # X<-[0]  =>  0  []
                        #self.ghost_unsave()
                        return value, error, None
                    if not value:
                        if not isinstance(val1, tuple): self.ghost_reset() # X<-[0]  =>  0  []
                        #self.ghost_unsave()
                        return val1, f"Expected: {patt}", None
                    #self.ghost_unsave()
                    if i == "0": val1 = (patt, value)
                    # if value is present, then nothing needs to be done

                elif patt.startswith("<") and patt.endswith(">"):
                    # if not self.current_tok:
                    #     return None, "EOF", "EOF"
                    # if self.current_tok.token_type == "EOF":
                    #     return None, "EOF", "EOF"
                    Pprint(f"testing: '{self.current_tok.regex()}' against pattern: '{patt}'", c=(255,0,0))
                    if not re.match(patt, self.current_tok.regex()):
                        #self.ghost_reset() # X<-[0]  =>  0  []
                        self.ghost_unsave()
                        return val1, f"Expected Token: {patt}", None
                    #if i == "0": val1 = self.current_tok
                    self.ghost_advance() # X+=1  [0]

            elif isinstance(patt, dict):
                # either a nested pattern
                # or a pattern with a capture and/or quantifier
                if "pattern" in patt.keys(): # ^ option 2
                    Pprint("key 'pattern' found in pattern rules")
                    pat = patt["pattern"]
                    quantifier = Quantifier(patt.get("quantifier", None))
                    capture = patt.get("capture", None)
                    captures = []
                    if pat.startswith("[") and pat.endswith("]"): # [atom]+
                        Pprint("pattern is a sub-rule")
                        branch = self.tree.get_path()
                        Pprint(f"saving branch: '{'/-/'.join(branch)}'")
                        do_loop = True
                        self.ghost_save() # 1->[0]  =>  1  [1, 0]
                        while do_loop:
                            self.tree.goto(pat.replace("[", "").replace("]", ""))
                            Pprint(f"moving to branch: '{pat.replace('[', '').replace(']', '')}'")
                            Pprint("parsing")
                            value, error, eof = self._parse() # IntegerNode | value:<INT> -> IntegerNode(<INT>), None
                            Pprint(f"returning to branch: '{'/-/'.join(branch)}'", c=(255,255,0))
                            self.tree.goto(branch)
                            Pprint(f"{value=}  {error=}  {eof=}")
                            #if eof: return value, error, eof
                            # if error:
                            #     return value, error
                            if value and capture:
                                captures.append(value)

                            #quantifier.next()
                            state = quantifier.check(value)
                            # if value: # this is a sub-rule, rules advance at the end automatically
                            #     self.ghost_advance()
                            if state == "done":
                                #self.ghost_save()
                                #self.solidify()
                                self.ghost_unsave() # 2  [1, 0]  =>  2  [0]
                                break
                                #return value, error # quantifier has reached an end
                            elif state in ["need", "valid"]:
                                pass # continue iterating
                            elif state == "not-enough":
                                self.ghost_reset() # 2<-[1,0]  =>  1  [0]
                                self.ghost_reset() # 1<-[0]  =>  0  []
                                return value, f"Expected: {pat}", None # quantifier did not recieve enough values

                        #if not do_loop: break
                        
                        if not quantifier.valid():
                            if not isinstance(val1, tuple): self.ghost_reset() # 2<-[0]  =>  0  []
                            return val1, quantifier.get_err(), None
                        if capture:
                            if len(captures) == 0:
                                node_captures.update({capture: set_values.get(capture, None)})
                            elif len(captures) == 1:
                                node_captures.update({capture: captures[0]})
                            else:
                                node_captures.update({capture: captures})

                        if i == "0": val1 = (pat, node_captures[capture])
                        # 2  [0]
                            
                    elif pat.startswith("<") and pat.endswith(">"):
                        do_loop = True
                        self.ghost_save() # 1->[0]  =>  1  [1, 0]
                        while do_loop:
                            # if not self.current_tok:
                            #     return None, "EOF", "EOF"
                            # if self.current_tok.token_type == "EOF":
                            #     return None, "EOF", "EOF"

                            Pprint(f"testing: '{self.current_tok.regex()}' against pattern: '{pat}'", c=(255,0,0))
                            value = re.match(pat, self.current_tok.regex())
                            if value:
                                value = value.group()

                                if capture:
                                    captures.append(self.current_tok)


                            #quantifier.next()
                            state = quantifier.check(value)
                            if value:
                                self.ghost_advance() # X+=1  [1, 0]

                            if state == "done":
                                #self.solidify()
                                #self.ghost_save()
                                self.ghost_unsave() # 2  [1, 0]  =>  2  [0]
                                break
                                #return value, None
                            elif state in ["need", "valid"]:
                                pass
                            elif state == "not-enough":
                                self.ghost_reset() # 2<-[1, 0]  =>  1  [0] # reset to before while loop
                                self.ghost_reset() # 1<-[0]  =>  0  []     # reset to beginning of pattern
                                return value, f"Expected: {pat}", None

                        #if not do_loop: break
                        
                        if not quantifier.valid():
                            if not isinstance(val1, tuple): self.ghost_reset() # 2<-[0]  =>  0  []
                            return val1, quantifier.get_err(), None
                        if capture:
                            node_captures.update({capture: captures})

                        # 2  [0]

                else:
                    Pprint(f"Exploring sub-pattern: {patt}")

                    q = Quantifier(patt.get("quantifier", None))
                    values = []
                    self.ghost_save() # 1->[0]  =>  1  [1, 0]
                    while True:
                        val, err, eof = self.explore_pattern(patt, node)
                        #if eof: return val, err, eof

                        # if err:
                        #     return err

                        state = q.check(val)

                        if val:
                            values.append(val)

                        if state == "done":
                            if capture := patt.get("capture", None):
                                node_captures.update({capture: values})
                            self.ghost_unsave() # 2  [1, 0]  =>  2  [0]
                            break

                        elif state in ["need", "valid"]:
                            pass

                        elif state == "not-enough":
                            self.ghost_reset() # 2<-[1, 0]  =>  1  [0] # reset to before this while loop
                            self.ghost_reset() # 1<-[0]  =>  0  []     # reset to before the entire pattern
                            return value, err, None

                    if not q.valid():
                        if not isinstance(val1, tuple): self.ghost_reset() # 2<-[0]  =>  0  []
                        return val1, q.get_err(), None
                        
                    # 2  [0]
                    
                    #if val or err:
                    #    return val, err

        # Pprint(f"{node_captures=}  {Value=}  {Error=}", c=(255,0,255))
        # # if this point is reached, a pattern has successfully matched!
        # state = global_quantifier.check(node_captures or Value)

        # Pprint(f"global: {state=}")
        # if state == "done":
        #     self.solidify()
        #     return Value or Node.get(node)(**node_captures), Error
        # elif state in ["need", "valid"]:
        #     pass
        # elif state == "not-enough":
        #     self.ghost_reset()
        #     return Value, Error

        # Value, Error = None, None

        self.ghost_unsave() # 3  [0]  =>  3  []
        # if self.current_tok.token_type in ["INT", "EOF"]:
        #     pass
        Pprint(f"{node=}  {node_captures=}")
        return Node.get(node)(**node_captures), None, None
    
    
    def _parse(self):
        # [expr]: global-node:None
        global_node = self.tree.current_branch.get("node", None)
        # ^ get global node if present
        Pprint(f"global-node: {global_node}", x="parse")
        if patterns := self.tree.current_branch.get("patterns", None):
            error = None
            Pprint(f"KEYS: {patterns.keys()}", c=(255,0,0))
            #quantifier = Quantifier(patterns.get)
            save = None
            for key in patterns.keys(): # keys: ['0', '1', '2', 'quantifier'?]
                Pprint(f"_parse: {key=}  rules: {patterns[key]}")
                pk = patterns[key].keys()
                if ("0" in pk) and ("1" not in pk) and ("quantifier" not in pk) and save:
                    # if pk looks like: ["0"] or ["0", "capture"] then it has 1 pattern element
                    if pk[0] == save[0]:
                        # if a failed rule happens to be the rule of this pattern, then return that node
                        return save[1], None, None
                    else:
                        save = None
                        self.ghost_reset()
                elif save:
                    save = None
                    self.ghost_reset()
                node, error, eof = self.explore_pattern(patterns[key], global_node)
                Pprint(f"_parse: {node=}  {error=}  {eof=}", c=(255,255,0))
                if isinstance(node, tuple): # if node is tuple, that means the pattern failed,
                    save = node # but returned the pattern and node made from it's first element,
                    node = None # this way, if a following pattern is a 1-element pattern that
                    # is the same pattern as the failed one, it can skip parsing it again
                    # this will hopefully prevent the fractal-branch parsing
                    # NOTE: if the node was a tuple, then self.ghost_reset() will need to be called, if it's pattern isn't used
                
                if node:# or eof:
                    return node, error, eof

            if error:
                return None, error, eof
                
        else: # no patterns given (wierd)
            raise Exception("rule has no patterns!")

        return node, None, None

import json
def main():
    text = ""
    with open("test.txt", "r") as file:
        text = file.read()
    
    segments = Segmentor(text)
    segments.segment()
    lexBuild = LexerBuilder(segments.LexerSegment)
    tree = lexBuild.build()
    
    print(json.dumps(tree.tree, indent=2))
    lexer = Lexer("<stdin>", "", tree)
    parseBuild = ParserBuilder(segments.ParserSegment)
    parseBuild.build()

    print(json.dumps(parseBuild.tree.tree, indent=2))
    #lexer = Lexer("test.txt", segments.CodeSegment, tree)
    #print(lexer.redirect_from_checks)
    #print(segments.CodeSegment)
    #tokens = lexer.make_tokens()

    nodeBuild = NodeBuilder(segments.NodesSegment)
    nodeBuild.build()
    
    #print(tokens)
    cmd = ""
    while cmd != "exit()":
        cmd = input(">>> ")
        if cmd == "exit()": break
        if cmd.strip() == "": continue

        lexer.reset("<stdin>", cmd)
        tokens, error = lexer.make_tokens()

        if error:
            print(error)
            continue

        print(tokens)

        parser = Parser(tokens, parseBuild)
        nodes, error, eof = parser.parse()

        if error:
           print(error)
           continue
        print(nodes)

'''

from Lexer import LexerBuilder, Lexer
from Parser import ParserBuilder, Parser
from Util import Segmentor
from Node import NodeBuilder

def main():
    text = ""
    with open("test.txt", "r") as file:
        text = file.read()

    segments = Segmentor(text)
    segments.segment()

    lexer_builder = LexerBuilder(segments.LexerSegment)
    lexer_tree = lexer_builder.build()
    lexer = Lexer("<stdin>", "", lexer_tree)
    parser_builder = ParserBuilder(segments.ParserSegment)
    parser_builder.build()
    node_builder = NodeBuilder(segments.NodesSegment)
    Node = node_builder.build()

    cmd = ""
    while cmd != "exit()":
        cmd = input(">>> ")
        if cmd == "exit()": break
        if cmd.strip() == "": continue

        lexer.reset("<stdin>", cmd)
        tokens, error = lexer.make_tokens()
        if error:
            print(error)
            continue

        print(tokens)
        
        parser = Parser(tokens, parser_builder, Node)
        nodes, error, eof = parser.parse()

        if error:
            print(error)
            continue

        print(nodes)

if __name__ == "__main__":
    main()

"""
testing:

from main import ParserBuilder
pb = ParserBuilder("")
pb._parse("<(VLINE|HASH|DOLLAR)>? name:<ID> (<ALIAS> aliases:<ID>)* <SEMICOLON>")

"""
    

    

