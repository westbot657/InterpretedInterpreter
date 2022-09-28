
import re


class DebugPrint:

    def __init__(self, name):
        self.name = name
        self.active = False

    def toggle(self):
        self.active = not self.active

    def __call__(self, *args, **kwargs):
        args = list(args)

        args.insert(0, f"\033[38;2;0;200;100m[{self.name}]\033[0m:")

        print(*args, **kwargs)

class Tree:
    def __init__(self, init={}):
        self.tree = init
        self.current_branch = self.tree
        self.current_branch_str = ""

    def goto(self, path):
        if isinstance(path, list):
            path = "/-/".join(path)
        self.current_branch_str = path
        pieces = path.split("/-/")
        self.current_branch = self.tree
        for p in pieces:
            if b := self.current_branch.get(p, None):
                if not isinstance(b, dict):
                    raise Exception(f"path '{path}' is not valid")
                self.current_branch = b
            else:
                self.current_branch.update({p: {}})
                self.current_branch = self.current_branch.get(p)

    def get_path(self):
        if self.current_branch_str == "": return []
        return self.current_branch_str.split("/-/")

    def get_branch_name(self):
        return self.get_path()[-1]
    
    def into(self, path):
        if isinstance(path, str): path = path.split("/-/")
        self.goto(self.get_path() + path)

    def into_raw(self, key):
        self.current_branch = self.current_branch.get(key)
    
    def back_out(self):
        path = self.get_path()
        if len(path) > 1:
            path.pop(-1)
            self.goto(path)

    def set(self, key, value):
        #print(f"Tree: setting '{key}' to: {value}")
        self.current_branch.update({key: value})

    def get(self, key):
        return self.current_branch.get(key)

    def contains(self, key):
        if key in self.current_branch.keys(): return True
        return False
    
    def into_set(self, key, value:dict):
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


class LexerBuilder:

    def __init__(self, text):
        self.text = text
        self.tree = Tree({"literals": {"\n": {"value": "NEWLINE"}}, "patterns": {}})

    def parse_flags(self, raw:str) -> dict:
        flags = {}
        curr = raw
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
            
            

        #print(f"prev chars is left as: {prev_chars}")

        if prev_chars.startswith("...") and len(prev_chars) == 4:
            v = prev_chars[3]
            #print(f"generating pattern for '{v}'")
            result += self._gen_pattern(v) + v
            prev_chars = ""
            #print(f"{prev_chars=}")
        
        
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

class Position:
    def __init__(self, index, column, line, file_name):
        self.index = index
        self.column = column
        self.line = line
        self.file_name = file_name

    def advance(self, char=None):
        self.index += 1

        self.column += 1

        if char == "\n":
            self.column = 0
            self.line += 1

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
            return f"<{self.token_type}:{self.token_value}:{id(self)}>"
        return f"<{self.token_type}:{id(self)}>"

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

lprint = DebugPrint("Lexer")
lprint.toggle()
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
        self.idx += n
        
        if self.idx >= self.text_len:
            self.current_char = None
        else:
            self.current_char = self.text[self.idx]

        self.pos.advance(self.current_char)

    def gdx(self):
        return self.idx + self.diff
    
    def ghost_advance(self, n=1):
        #print(f"text-length:{self.text_len}")
        self.diff += n
        if self.gdx() < self.text_len:
            self.current_char = self.text[self.gdx()]
        else:
            self.current_char = None

    def ghost_save(self):
        self._diff = self.diff
    
    def ghost_reset(self):
        self.diff = self._diff
        self._diff = 0
        if self.gdx() < self.text_len:
            self.current_char = self.text[self.gdx()]
        else:
            self.current_char = None

    def ghost_get(self):
        return self.diff

    def ghost_set(self, val):
        self.ghost_reset()
        self.ghost_advance(val)
    
    def solidify(self):
        self.advance(self.diff)
        self.diff = 0
        self._diff = 0

    def text_from_ghost(self, length=None):
        if length:
            length = self.gdx()+length
        return self.text[self.gdx():length]
        
    def text_from_real(self, length=None):
        if length:
            length = self.idx + length
        return self.text[self.idx:length]

    def _explore_pattern(self, rules):
        found_match = False
        soft_value = None
        
        if matches := rules.get("matches", None):
            lprint("exploring matches")
            value = None
            for pattern in matches.keys():
                lprint(f"testing {pattern=} against text: {self.text_from_ghost()}")
                if m := re.match(pattern, self.text_from_ghost()):
                    
                    pos_start = self.pos.copy()
                    m_rules = matches.get(pattern)
                    match_type = m_rules["type"] # either `hr-match`, `hc-match`, or `sr-match`
                    value = m.group()
                    lprint(f"found a match!  {value=}")
                    n = self.ghost_get()
                    self.ghost_advance(len(value))
                    lprint(f"\033[38;2;20;200;20midx={self.pos.index}  ghost-offset={n}\033[0m")
                    
                    if match_type == "sr-match" and not found_match:
                        lprint("match is an sr-match")
                        soft_value = value, rules.get("value", False)
                        found_match = True
                        #self.solidify()
                        #break
                        continue
                    elif match_type == "hr-match":
                        lprint("match is an hr-match")
                        found_match = True
                        lprint(f"exploring in {m_rules=}")
                        #self.solidify()
                        self.ghost_reset() # <- uncommenting causes some kind of recursive loop that seems to not be able to hit the recursion limit
                        #self.ghost_set(n)
                        val, err = self._explore_pattern(m_rules)
                        #self.solidify()
                        lprint(f"{value=}  {val=}  {err=}")
                        
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
                            lprint("\033[38;2;255;0;0m<--here?\033[0m")
                            lprint(rules)
                            lprint("\033[38;2;255;0;0m<--here?\033[0m")
                            
                            if val_ := rules.get("value", None):
                                if flags := rules.get("flags", None):
                                    if "#no-value" in flags: value = None
                                self.solidify()
                                lprint(f"value!! {value=}")
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
                        lprint("match is an hc-match")
                        found_match = True
                        #self.solidify()
                        lprint(f"exploring {m_rules=}")
                        val, err = self._explore_pattern(m_rules)
                        
                        #self.solidify()
                        lprint(f"{value=}  {val=}  {err=}")

                        if err == "plz advance":
                            err = None
                            if value:
                                self.ghost_advance(len(value))
                            
                        if err:
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
                        lprint(f"{tok=}")
                        flag = None
                        if flags := m_rules.get("flags", None):
                            flag = flags[0]
                        self.solidify()
                            
                        return tok, flag

            if soft_value:
                val, tok_type = soft_value
                lprint(f"using soft-match: {val=}  {tok_type=}")
                #self.solidify()
                lprint("soft value")
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
                lprint("REDIRECT")
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
                self.solidify()
                lprint("\033[38;2;20;255;20msolidifying position!\033[0m")
                lprint(f"\033[38;2;200;30;30m'{self.text_from_real()}'\n\n'{self.text_from_ghost()}'\033[0m")
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
            lprint(f"redirect!\n{self.pos.index}\n{self.text_from_ghost()}")
            
            self.ghost_reset()
            lprint(f"after ghost-reset: {self.text_from_ghost()}")
            val, err = self.explore_pattern(target, False)

            lprint(f"{val=}  {err=}")
            
            if err:
                if error:
                    return None, self.formatError(error)
                elif tok_type := rules.get("value", None):
                    self.solidify()
                    return Token(tok_type, None, self.pos.copy(), self.pos.copy()), None
                    
            return val, self.formatError(err)

        elif tok_type := rules.get("value", None):
            lprint("raw value")
            self.solidify()
            return Token(tok_type, None, self.pos.copy(), self.pos.copy()), None

        else:
            return None, f"No Value Error: {self.pos.copy()}"

    def explore_pattern(self, path, solidify=True):
        self.tree.goto(path)
        rules = self.tree.current_branch

        lprint(f"exploring '{path}'")
        ret = self._explore_pattern(rules)
        if solidify:
            self.solidify()
        return ret

    def _explore_literal(self, branch):
        pos_start = self.pos.copy()
        lprint(f"{self.current_char=}")
        self.ghost_advance()
        for key in branch.keys():
            lprint(f"checking '{self.current_char}' against '{key}'")
            if self.current_char == key:
                lprint(f"exploring literal: '{self.current_char}'")
                val, err = self._explore_literal(branch[key])
                return val, self.formatError(err)
            elif key == "redirect":
                redirect = branch["redirect"]
                target = redirect["target"]
                error = redirect["error"]
                lprint("ghost reset")
                self.ghost_reset()
                val, err = self.explore_pattern(target)
                if err:
                    if error:
                        return val, self.formatError(error)
                lprint(f"{val=}, {err=}, {branch=}")
                return val, self.formatError(err)
            elif key == "value":
                lprint(f"value = {branch[key]}")
                return Token(branch[key], None, pos_start, self.pos.copy()), None
    
    def explore_literal(self, char):
        self.tree.goto("literals")
        if branch := self.tree.current_branch.get(char, None):
            lprint(f"exploring literal: '{char}'\n{branch=}")
            val, err = self._explore_literal(branch)
            self.solidify()
            return val, err

        else:
            return char, self.formatError("?InvalidCharacter")
    
    def make_tokens(self) -> list:
        tokens = []

        while self.current_char != None:
            lprint(f"\033[38;2;20;200;200m{self.pos.index=}   char={self.current_char}\033[0m")
            if self.current_char == " ":
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

            return f"{self.parent.name}:({', '.join(res)})"

    @classmethod
    def get(cls, name):
        for node in cls._nodes:
            if node.name == name:
                return node
    
    def __init__(self, name, values:list):
        self.name = name
        self.values = values
        Node._nodes.append(self)

    def __call__(self, **kwargs):
        return Node.NodeInstance(self, **kwargs)
    
    def __repr__(self):
        return str(self.values)

class NodeBuilder:

    def __init__(self, text):
        self.text = text

    def build(self):
        for line_ in self.text.split("\n"):
            line = line_.strip()

            if "(" in line:
                name, vals = line.replace(")", "").split("(")
                values = [v.strip() for v in vals.split(",")]

            else:
                name = line
                values = []

            Node(name, values)
        
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


class ParserBuilder:

    def __init__(self, text):
        self.text = text
        self.tree = Tree()

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
        for comp in components:
            if isinstance(comp, list):
                pattern.update({str(index): self.format_components(comp)})
                
            elif isinstance(comp, str):
                if comp.strip() == "": continue
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

                elif comp.endswith(("?", "*", "+")) and comp not in ("?", "*", "+"):
                    pattern.update({
                        str(index): {
                            "pattern": comp[:-1],
                            "quantifier": comp[-1]
                        }
                    })

                elif m := re.search("\\{\d+(,\d*)?\\}$", comp) and not re.match("\\{\d+(,\d*)?\\}", comp):
                    pattern.update({
                        str(index): {
                            "pattern": comp.replace(m.group(), ""),
                            "quantifier": m.group()
                        }
                    })
                
                elif comp in ("?", "*", "+"):
                    pattern[str(index-1)].update({"quantifier": comp})
                    index -= 1

                elif re.match("\\{\d+(,\d*)?\\}", comp):
                    pattern[str(index-1)].update({"quantifier": comp})
                    index -= 1
                        
                else:
                    pattern.update({str(index): comp})

            index += 1

        return pattern
    
    def build(self):
        index = 0
        for line_ in self.text.split("\n"):
            line = line_.strip()
            pieces = line.split(" ")
            
            if (not line_.startswith(" ")) and pieces[0].endswith(":"):
                if len(pieces) >= 1: # rule-name:
                    self.tree.goto(pieces[0])
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

class Parser:

    def __init__(self):
        pass

    def parse(self, tokens):
        retok = "".join([tok.regex() for tok in tokens])

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

    #print(json.dumps(parseBuild.tree.tree, indent=2))
    #lexer = Lexer("test.txt", segments.CodeSegment, tree)
    #print(lexer.redirect_from_checks)
    #print(segments.CodeSegment)
    #tokens = lexer.make_tokens()
    
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
            

    

if __name__ == "__main__":
    main()

"""
testing:

from main import ParserBuilder
pb = ParserBuilder("")
pb._parse("<(VLINE|HASH|DOLLAR)>? name:<ID> (<ALIAS> aliases:<ID>)* <SEMICOLON>")

"""
    

    

