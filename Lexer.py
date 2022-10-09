
from Util import Tree, DebugPrint, Position, Token
import re

lbprint = DebugPrint("LexerBuilder", (200, 0, 50))

class LexerBuilder:

    def __init__(self, text):
        self.text = text
        self.tree = Tree({"literals": {"\n": {"value": "NEWLINE"}}, "patterns": {}})

    def parse_flags(self, raw:str) -> dict:
        flags = {}
        curr = raw
        lbprint["parse"]["parse-flags"](f"'{raw}'")
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
        lbprint["parse"]["parse-flags"](f"{flags=}")
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
        lbprint["parse"]["parse-pattern"](f"'{pattern}'")
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
        lbprint["parse-pattern"]["gen"](f"parse-pattern: prev chars is left as: {prev_chars}")

        if prev_chars.startswith("...") and len(prev_chars) == 4:
            v = prev_chars[3]
            lbprint["parse-pattern"]["gen"](f"generating pattern for '{v}'")
            result += self._gen_pattern(v) + v
            prev_chars = ""
            lbprint["parse-pattern"]["gen"](f"{prev_chars=}")
        
        
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
                    
                elif line.startswith(">>"): # soft-reset-match
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




lprint = DebugPrint("Lexer", (0, 200, 200))
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
    
            lprint["advance"](f"{n=} text-length:{self.text_len}  current-char:{self.current_char}")
            n -= 1
            

    def gdx(self):
        return self.idx + self.diff
    
    def ghost_advance(self, n=1):
        lprint["ghost"]["advance"](f"{n=} text-length:{self.text_len}")
        self.diff += n
        if self.gdx() < self.text_len:
            self.current_char = self.text[self.gdx()]
        else:
            self.current_char = None

    def ghost_save(self):
        lprint["ghost"]("save")
        self._diff = self.diff
    
    def ghost_reset(self):
        lprint["ghost"]("reset")
        self.diff = self._diff
        self._diff = 0
        if self.gdx() < self.text_len:
            self.current_char = self.text[self.gdx()]
        else:
            self.current_char = None

    def ghost_get(self):
        lprint["ghost"]["get"](f"{self.diff}")
        return self.diff

    def ghost_set(self, val):
        lprint["ghost"]["set"](f"{val}")
        self.ghost_reset()
        self.ghost_advance(val)
    
    def solidify(self):
        lprint["ghost"]("solidify")
        self.advance(self.diff)
        self.diff = 0
        self._diff = 0

    def text_from_ghost(self, length=None):
        x = self.gdx()
        if length:
            length = x+length
        lprint["ghost"]["text-from-ghost"](f"(up to 30 chars) '{self.text[x:x+30]}'")
        return self.text[x:length]
        
    def text_from_real(self, length=None):
        if length:
            length = self.idx + length
        lprint["text-from-real"](f"(up to 30 chars) '{self.text[self.idx:self.idx+30]}'")
        return self.text[self.idx:length]

    def _explore_pattern(self, rules):
        found_match = False
        soft_value = None
        
        if matches := rules.get("matches", None):
            lprint["explore-pattern"]("exploring matches")
            value = None
            for pattern in matches.keys():
                lprint["explore-pattern"](f"testing {pattern=} against text: {self.text_from_ghost()}")
                if m := re.match(pattern, self.text_from_ghost()):
                    
                    pos_start = self.pos.copy()
                    m_rules = matches.get(pattern)
                    match_type = m_rules["type"] # either `hr-match`, `hc-match`, or `sr-match`
                    value = m.group()
                    lprint["explore-pattern"](f"found a match!  {value=}")
                    n = self.ghost_get()
                    self.ghost_advance(len(value))
                    lprint["explore-pattern"](f"\033[38;2;20;200;20midx={self.pos.index}  ghost-offset={n}\033[0m")
                    
                    if match_type == "sr-match" and not found_match:
                        lprint["explore-pattern"]("match is an sr-match")
                        soft_value = value, rules.get("value", False)
                        found_match = True
                        #self.solidify()
                        #break
                        continue
                    elif match_type == "hr-match":
                        lprint["explore-pattern"]("match is an hr-match")
                        found_match = True
                        lprint["explore-pattern"](f"exploring in {m_rules=}")
                        #self.solidify()
                        self.ghost_reset() # <- uncommenting causes some kind of recursive loop that seems to not be able to hit the recursion limit
                        #self.ghost_set(n)
                        val, err = self._explore_pattern(m_rules)
                        #self.solidify()
                        lprint["explore-pattern"](f"{value=}  {val=}  {err=}")
                        
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
                            lprint["explore-pattern"]("\033[38;2;255;0;0m<--here?\033[0m")
                            lprint["explore-pattern"](rules)
                            lprint["explore-pattern"]("\033[38;2;255;0;0m<--here?\033[0m")
                            
                            if val_ := rules.get("value", None):
                                if flags := rules.get("flags", None):
                                    if "#no-value" in flags: value = None
                                self.solidify()
                                lprint["explore-pattern"](f"value!! {value=}")
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
                        lprint["explore-pattern"]("match is an hc-match")
                        found_match = True
                        #self.solidify()
                        lprint["explore-pattern"](f"exploring {m_rules=}")
                        val, err = self._explore_pattern(m_rules)
                        
                        #self.solidify()
                        lprint["explore-pattern"](f"{value=}  {val=}  {err=}")

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
                        lprint["explore-pattern"](f"{tok=}")
                        flag = None
                        if flags := m_rules.get("flags", None):
                            flag = flags[0]
                        self.solidify()
                            
                        return tok, flag

            if soft_value:
                val, tok_type = soft_value
                lprint["explore-pattern"](f"using soft-match: {val=}  {tok_type=}")
                #self.solidify()
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
                lprint["explore-pattern"]("REDIRECT")
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
                lprint["explore-pattern"](f"value?? {value=}")
                #self.solidify()
                #lprint("\033[38;2;20;255;20msolidifying position!\033[0m", x="ep")
                lprint["explore-pattern"](f"text-from-real: \033[38;2;200;30;30m'{self.text_from_real()}'\033[0m")
                lprint["explore-pattern"](f"text-from-ghost: \033[38;2;200;30;30m'{self.text_from_ghost()}'\033[0m")
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
            lprint["explore-pattern"](f"redirect!\n{self.pos.index}\n{self.text_from_ghost()}")
            
            self.ghost_reset()
            lprint["explore-pattern"](f"after ghost-reset: {self.text_from_ghost()}")
            val, err = self.explore_pattern(target, False)

            lprint["explore-pattern"](f"{val=}  {err=}")
            
            if err:
                if error:
                    return None, self.formatError(error)
                elif tok_type := rules.get("value", None):
                    self.solidify()
                    return Token(tok_type, None, self.pos.copy(), self.pos.copy()), None
                    
            return val, self.formatError(err)

        elif tok_type := rules.get("value", None):
            lprint["explore-pattern"]("raw value")
            self.solidify()
            return Token(tok_type, None, self.pos.copy(), self.pos.copy()), None

        else:
            return None, f"No Value Error: {self.pos.copy()}"

    def explore_pattern(self, path, solidify=True):
        self.tree.goto(path)
        rules = self.tree.current_branch

        lprint["explore-pattern"](f"exploring '{path}'")
        ret = self._explore_pattern(rules)
        if solidify:
            self.solidify()
        return ret

    def _explore_literal(self, branch):
        pos_start = self.pos.copy()
        lprint["explore-literal"](f"{self.current_char=}")
        self.ghost_advance()
        for key in branch.keys():
            lprint["explore-literal"](f"checking '{self.current_char}' against '{key}'")
            if self.current_char == key:
                lprint["explore-literal"](f"exploring literal: '{self.current_char}'")
                val, err = self._explore_literal(branch[key])
                return val, self.formatError(err)
            elif key == "redirect":
                redirect = branch["redirect"]
                target = redirect["target"]
                error = redirect["error"]
                lprint["explore-literal"]("ghost reset")
                self.ghost_reset()
                val, err = self.explore_pattern(target)
                if err:
                    if error:
                        return val, self.formatError(error)
                lprint["explore-literal"](f"{val=}, {err=}, {branch=}")
                return val, self.formatError(err)
            elif key == "value":
                lprint["explore-literal"](f"value = {branch[key]}")
                return Token(branch[key], None, pos_start, self.pos.copy()), None
    
    def explore_literal(self, char):
        self.tree.goto("literals")
        if branch := self.tree.current_branch.get(char, None):
            lprint["explore-literal"](f"exploring literal: '{char}'\n{branch=}")
            val, err = self._explore_literal(branch)
            self.solidify()
            return val, err

        else:
            return char, self.formatError("?InvalidCharacter")
    
    def make_tokens(self) -> list:
        tokens = []

        while self.current_char != None:
            lprint["make-tokens"](f"{self.pos.index=}   char={self.current_char}\033[0m", color=(20, 200, 200))
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