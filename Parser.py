
from Util import Tree, DebugPrint, Quantifier
import re

pbprint = DebugPrint("ParserBuilder", (200, 10, 200))
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
        pbprint["format-components"](f"{components}")
        for comp in components:
            if isinstance(comp, list):
                pbprint["format-components"](f"component is a list: {comp}")
                pattern.update({str(index): self.format_components(comp)})
                
            elif isinstance(comp, str):
                if comp.strip() == "": continue
                pbprint["format-components"](f"component is a string: {comp}")
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
                    pbprint["format-components"](f"set pattern:{index} to: {temp}")

                elif comp.endswith(("?", "*", "+")) and comp not in ("?", "*", "+"):
                    pbprint["format-components"](f"component has a quantifier: '{comp}'")
                    pattern.update({
                        str(index): {
                            "pattern": comp[:-1],
                            "quantifier": comp[-1]
                        }
                    })

                elif m := re.search("\\{\d+(,\d*)?\\}$", comp) and not re.match("\\{\d+(,\d*)?\\}", comp):
                    pbprint["format-components"](f"components has a quantifier: '{comp}'")
                    pattern.update({
                        str(index): {
                            "pattern": comp.replace(m.group(), ""),
                            "quantifier": m.group()
                        }
                    })
                
                elif comp in ("?", "*", "+"):
                    pbprint["format-components"](f"component is a quantifier: '{comp}'")
                    pattern[str(index-1)].update({"quantifier": comp})
                    index -= 1

                elif re.match("\\{\d+(,\d*)?\\}", comp):
                    pbprint["format-components"](f"component is a quantifier: '{comp}'")
                    pattern[str(index-1)].update({"quantifier": comp})
                    index -= 1
                        
                else:
                    pbprint["format-components"](f"set pattern:{index} to: '{comp}'")
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
                pbprint["build"](f"entry-point: '{self.entry_point}'")
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




Pprint = DebugPrint("Parser", (0, 220, 220))
Pprint.set_tag_colors({
    "parse": (0, 127, 0),
    "explore-pattern": (255, 127, 0),
    "ghost": (100, 100, 100),
    "stack": (255, 0, 255),
    "parse-node": (155, 155, 155),
    "save": (0, 255, 0),
    "unsave": (255, 255, 0),
    "reset": (255, 0, 0),
    "_parse": (200, 200, 200),
    "advance": (0, 127, 255)
})
Pprint.toggle()
#Pprint.toggle("_parse")
class Parser:

    def __init__(self, tokens, builder, node_class):
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
        self.Node = node_class
        Pprint["init"]("creating new Parser", color=(255,0,0))
        self.advance()

    def gdx(self):
        return self.idx + self.diff

    def advance(self, n=1):
        Pprint["advance"](f"{n=}  current-token:{self.current_tok}")
        while n >= 1:
            self.idx += 1
            if self.idx < self.tok_len:
                self.current_tok = self.tokens[self.idx]
            else:
                self.current_tok = self.tokens[-1] # this item should be EOF
            n -= 1
        Pprint["advance"](f"current-token changed to: {self.current_tok}")

    def ghost_advance(self, n=1):
        Pprint["ghost"]["advance"](f"{n=}  current-token:{self.current_tok}")
        self.diff += n
        if self.idx + self.diff < self.tok_len:
            self.current_tok = self.tokens[self.idx + self.diff]
        else:
            self.current_tok = self.tokens[-1] # < EOF
        Pprint["ghost"]["advance"](f"current-token changed to: {self.current_tok}")

    def ghost_save(self):
        self.ghost_stack.insert(0, self.diff)
        Pprint["ghost"]["save"]["stack"](f"{self.ghost_stack}", color=(255,127,0))
    
    def ghost_unsave(self):
        if len(self.ghost_stack) > 0:
            self.ghost_stack.pop(0)

        Pprint["ghost"]["unsave"]["stack"](f"{self.ghost_stack}", color=(255,127,0))

    def ghost_reset(self):
        Pprint["ghost"]["reset"](f"current-token:{self.current_tok}")
        self.diff = self.ghost_stack.pop(0) if len(self.ghost_stack) > 0 else 0
        if self.gdx() < self.tok_len:
            self.current_tok = self.tokens[self.gdx()]
        else:
            self.current_tok = self.tokens[-1] # < EOF

        Pprint["ghost"]["reset"](f"current-token changed to: {self.current_tok}")
        Pprint["ghost"]["reset"]["stack"](f"{self.ghost_stack}", color=(255,127,0))

    def solidify(self):
        Pprint["ghost"]("solidify!")
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
        Pprint["parse-node"](f"parsing: '{node_str}'", color=(127,127,0))
        while node_str != "":
            
            if node_str[0] == "(":
                #name = node_str.split("(", 1)[0]
                node = self.Node.get(name)
                name = ""
                Pprint["parse-node"](f"current char is '(', {name=}, after='{node_str[1:]}'")
                _node, node_str = self._parse_node(node_str[1:])
                values.append(_node)
                
            elif node_str[0] == ")":
                node_str = node_str[1:]
                if node_str[0] == ",": node_str = node_str[1:]
                Pprint["parse-node"](f"current char is ')', node is '{node.name}', {node_str=}")
                return node(**dict(zip(node.values, values))), node_str

            elif node_str[0] == ",":
                _node = self.Node.get(name)()
                values.append(_node)
                Pprint["parse-node"](f"current char is ',', name is '{name}'")
                name = ""
                node_str = node_str[1:]

            else:
                name += node_str[0]
                node_str = node_str[1:]

        if name:
            Pprint["parse-node"](f"making node: {name=}", color=(0,200,0))
            return self.Node.get(name)(), None
        
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
        
        Pprint["explore-pattern"](f"exp-pattern: {node=}")
        if set_vals := pattern.get("set-value", None):
            for key in set_vals:
                _node = self.parse_node(set_vals[key])
                Pprint["explore-pattern"](f"set-val: '{key}': {_node}")
                set_values.update({key: _node})

        self.ghost_save() # 0 -> []  =>  0  [0]
        #do_unsave = True
        for i in list(pattern.keys()): # iterate through portions of a pattern
            Pprint["explore-pattern"](f"iteration key: '{i}'")
            if i == "node": continue
            if i == "set-value": continue
            if i == "quantifier": continue
            patt = pattern[i]
            Pprint["explore-pattern"](f"current-tok: {self.current_tok}", color=(0,127,255))
            if isinstance(patt, str):
                Pprint["explore-pattern"](f"is string, pattern={patt}")
                if patt.startswith("[") and patt.endswith("]"):
                    branch = self.tree.get_path()
                    Pprint["explore-pattern"](f"saving branch: '{'/-/'.join(branch)}'")
                    self.tree.goto(patt.replace("[", "").replace("]", ""))
                    Pprint["explore-pattern"](f"moved to branch: '{'/-/'.join(self.tree.get_path())}', parsing", color=(0,255,255))
                    Pprint["explore-pattern"](f"contents of branch: {self.tree.current_branch}", color=(200,200,0))
                    #self.ghost_save()
                    value, error, eof = self._parse()
                    #if eof: return value, error, eof
                    
                    Pprint["explore-pattern"](f"returning to branch: '{'/-/'.join(branch)}'")
                    self.tree.goto(branch)
                    Pprint["explore-pattern"](f"{value=}  {error=}")
                    if error:
                        self.ghost_reset() # X<-[0]  =>  0  []
                        #self.ghost_unsave()
                        return value, error, None
                    if not value:
                        if not isinstance(val1, tuple): self.ghost_reset() # X<-[0]  =>  0  []
                        #self.ghost_unsave()
                        return val1, f"Expected: {patt}", None
                    #self.ghost_unsave()
                    if i == "0":
                        if isinstance(value, tuple):
                            val1 = (patt, value[1])
                        else:
                            val1 = (patt, value)
                    # if value is present, then nothing needs to be done

                elif patt.startswith("<") and patt.endswith(">"):
                    # if not self.current_tok:
                    #     return None, "EOF", "EOF"
                    # if self.current_tok.token_type == "EOF":
                    #     return None, "EOF", "EOF"
                    Pprint["explore-pattern"](f"testing: '{self.current_tok.regex()}' against pattern: '{patt}'", color=(255,0,0))
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
                    Pprint["explore-pattern"]("key 'pattern' found in pattern rules")
                    pat = patt["pattern"]
                    quantifier = Quantifier(patt.get("quantifier", None))
                    capture = patt.get("capture", None)
                    captures = []
                    if pat.startswith("[") and pat.endswith("]"): # [atom]+
                        Pprint["explore-pattern"]("pattern is a sub-rule")
                        branch = self.tree.get_path()
                        Pprint["explore-pattern"](f"saving branch: '{'/-/'.join(branch)}'")
                        do_loop = True
                        self.ghost_save() # 1->[0]  =>  1  [1, 0]
                        while do_loop:
                            self.tree.goto(pat.replace("[", "").replace("]", ""))
                            Pprint["explore-pattern"](f"moving to branch: '{pat.replace('[', '').replace(']', '')}'")
                            Pprint["explore-pattern"]("parsing")
                            value, error, eof = self._parse() # IntegerNode | value:<INT> -> IntegerNode(<INT>), None
                            Pprint["explore-pattern"](f"returning to branch: '{'/-/'.join(branch)}'", color=(255,255,0))
                            self.tree.goto(branch)
                            Pprint["explore-pattern"](f"{value=}  {error=}  {eof=}")
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
                            elif state == "not-enough": # if this is reached, value is None
                                self.ghost_reset() # 2<-[1,0]  =>  1  [0]
                                if not isinstance(val1, tuple): self.ghost_reset()#self.ghost_reset() # 1<-[0]  =>  0  []
                                return val1, f"Expected: {pat}", None # quantifier did not recieve enough values

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

                            if i == "0":
                                if isinstance(node_captures[capture], tuple):
                                    val1 = (pat, node_captures[capture][1])
                                else:
                                    val1 = (pat, node_captures[capture])
                        elif i == "0":
                            if isinstance(value, tuple):
                                val1 = value[1]
                            else:
                                val1 = value
                        # 2  [0]
                            
                    elif pat.startswith("<") and pat.endswith(">"):
                        do_loop = True
                        self.ghost_save() # 1->[0]  =>  1  [1, 0]
                        while do_loop:
                            # if not self.current_tok:
                            #     return None, "EOF", "EOF"
                            # if self.current_tok.token_type == "EOF":
                            #     return None, "EOF", "EOF"

                            Pprint["explore-pattern"](f"testing: '{self.current_tok.regex()}' against pattern: '{pat}'", color=(255,0,0))
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
                                if not isinstance(val1, tuple): self.ghost_reset()#self.ghost_reset() # 1<-[0]  =>  0  []     # reset to beginning of pattern
                                return val1, f"Expected: {pat}", None

                        #if not do_loop: break
                        
                        if not quantifier.valid():
                            if not isinstance(val1, tuple): self.ghost_reset() # 2<-[0]  =>  0  []
                            return val1, quantifier.get_err(), None
                        if capture:
                            node_captures.update({capture: captures})

                        # 2  [0]

                else:
                    Pprint["explore-pattern"](f"Exploring sub-pattern: {patt}")

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
                            if not isinstance(val1, tuple): self.ghost_reset()#self.ghost_reset() # 1<-[0]  =>  0  []     # reset to before the entire pattern
                            return val1, err, None

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
        Pprint["explore-pattern"](f"{node=}  {node_captures=}")

        if not node:
            Pprint["explore-pattern"](f"no node, {val1=}")
            if val1:
                return val1[1], None, None
        
        return self.Node.get(node)(**node_captures), None, None
    
    
    def _parse(self):
        # [expr]: global-node:None
        global_node = self.tree.current_branch.get("node", None)
        # ^ get global node if present
        Pprint["_parse"](f"global-node: {global_node}")
        if patterns := self.tree.current_branch.get("patterns", None):
            error = None
            Pprint(f"KEYS: {patterns.keys()}", color=(255,0,0))
            #quantifier = Quantifier(patterns.get)
            save = None
            for key in patterns.keys(): # keys: ['0', '1', '2', 'quantifier'?]
                Pprint["_parse"](f"{key=}  {save=}  rules: {patterns[key]}")
                pk = list(patterns[key].keys())
                if ("0" in pk) and ("1" not in pk) and ("quantifier" not in pk) and save:
                    # if pk looks like: ["0"] or ["0", "capture"] then it has 1 pattern element
                    if patterns[key]["0"] == save[0]:
                        # if a failed rule happens to be the rule of this pattern, then return that node
                        return save[1], None, None
                    else:
                        save = None
                        self.ghost_reset()
                elif save:
                    save = None
                    self.ghost_reset()
                node, error, eof = self.explore_pattern(patterns[key], global_node)
                Pprint["_parse"](f"{node=}  {error=}  {eof=}", color=(255,255,0))
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
