
colors = {
    "red": (255, 0, 0),
    "dark-red": (127, 0, 0),
    "orange": (255, 127, 0),
    "yellow": (255, 255, 0),
    "green": (0, 255, 0),
    "dark-green": (0, 127, 0),
    "blue": (0, 0, 255),
    "dark-blue": (0, 0, 127),
    "neon-blue": (0, 255, 255),
    "cyan": (0, 127, 127),
    "magenta": (255, 0, 255),
    "purple": (127, 0, 255)
}

def Color(red, green, blue, ground="fg"): # this function is kinda useless other than converting fg/bg to 38/48
    """
    `ground` may be either "fg" or "bg",
    invalid values are read as fg
    """
    return (red, green, blue, "48" if ground == "bg" else "38")

def TextColor(red, green, blue, ground="fg"):
    return f"\033[{'48' if ground in ['bg', '48'] else '38'};2;{red};{green};{blue}m"

class DebugPrint:

    class _disabled_:
        def __init__(self):
            pass

        def __call__(self, *args, **kwargs):
            pass

        def __getitem__(self, item):
            return self

        def c(self, r, g, b, ground="fg"):
            return self
    
    def __init__(self, name, color=None):
        self.name = name
        if isinstance(color, (tuple, list)):
            if len(color) == 3:
                self.color = f"\033[38;2;{color[0]};{color[1]};{color[2]}m"
            elif len(color) == 4:
                self.color = f"\033[{color[3]};2;{color[0]};{color[1]};{color[2]}m"
            else:
                self.color = ""
        elif isinstance(color, str):
            color = colors.get(color, (255, 255, 255))
            self.color = f"\033[38;2;{color[0]};{color[1]};{color[2]}m"
        else:
            self.color = ""

        self.tags_ = []
        self.active = False
        self.color_map = {}

        self._disabled = []

        self._disabled_object = DebugPrint._disabled_()
    
    def toggle(self, *args):
        if len(args) == 0:
            self.active = not self.active
        else:
            for arg in args:
                if arg in self._disabled:
                    self._disabled.remove(arg)
                else:
                    self._disabled.append(arg)

    def set_tag_colors(self, map):
        self.color_map.update(map)
    
    def __getitem__(self, item):
        if not self.active: return self._disabled_object
        if item in self.color_map.keys():
            col = TextColor(*self.color_map[item])
        else:
            col = ""
        self.tags_.append(f"{col}[{item}]\033[0m")
        if item in self._disabled:
            self.tags_.clear()
            return self._disabled_object
        return self

    def c(self, r, g, b, ground="fg"):
        self.tags_.append(f"\033[{'48' if ground in ['48', 'bg'] else '38'};2;{r};{g};{b}m")
        return self

    def __call__(self, *args, **kwargs):

        if not self.active: return
        
        if "color" in kwargs.keys():
            color = kwargs.pop("color")
            if isinstance(color, (tuple, list)):
                if len(color) == 3:
                    color = f"\033[38;2;{color[0]};{color[1]};{color[2]}m"
                elif len(color) == 4:
                    color = f"\033[{'48' if color[3] in ['48', 'bg'] else '38'};2;{color[0]};{color[1]};{color[2]}m"
        else:
            color = ""

        args = list(args)

        out = f"{self.color}[{self.name}]\033[0m"

        if self.tags_:
            out += " " + " ".join(self.tags_)
            self.tags_.clear()
        out += f":{color}"

        args.insert(0, out)

        sep = kwargs.get("sep", " ")
        p = sep.join(args) + "\033[0m"

        print(p, **kwargs)
        

tprint = DebugPrint("Tree", (10, 200, 10))
tprint.set_tag_colors({
    "get/set": colors["dark-green"],
    "movement": colors["orange"]
})
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
        tprint["movement"]["goto"](f"'{path}'")
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
        tprint.c(255, 0, 0)("locked")
        self.locked = True
    
    def get_path(self):
        if self.current_branch_str == "": x = []
        x = self.current_branch_str.split("/-/")
        tprint["get/set"]["get-path"](f"'{'/-/'.join(x)}'")
        return x

    def get_branch_name(self):
        
        tprint["get/set"]["get-branch-name"]("(next get-path last item)")
        x = self.get_path()
        if len(x) == 0: return ""
        return x[-1]
    
    def into(self, path):
        if isinstance(path, str): path = path.split("/-/")
        tprint["movement"]["into"](f"'{'/-/'.join(path)}'")
        self.goto(self.get_path() + path)

    def into_raw(self, key):
        tprint["movement"]["into-raw"](f"'{key}'")
        self.current_branch = self.current_branch.get(key)
    
    def back_out(self):
        path = self.get_path()
        tprint["movement"]("back-out! (next goto)")
        if len(path) > 1:
            path.pop(-1)
            self.goto(path)

    def set(self, key, value):
        tprint["get/set"](f"setting '{key}' to: {value}")
        self.current_branch.update({key: value})

    def get(self, key):
        tprint["get/set"]["get"](f"getting '{key}' from current branch")
        return self.current_branch.get(key)

    def contains(self, key):
        x = key in self.current_branch.keys()
        tprint["get/set"]["contains"](f"'key' => {x}")
        return x
    
    def into_set(self, key, value:dict):
        tprint["get/set"]["into-set"](f"valid value? {isinstance(value, dict)}")
        assert isinstance(value, dict)
        
        self.set(key, value)
        self.into(key)


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


pprint = DebugPrint("Position", (255, 127, 0))
#pprint.toggle()
class Position:
    def __init__(self, index, column, line, file_name):
        self.index = index
        self.column = column
        self.line = line
        self.file_name = file_name

    def advance(self, char=None):
        pprint[id(self)]["advance"](f"(1) idx:{self.index} col:{self.column} ln:{self.line} {char=}")
        self.index += 1
        self.column += 1

        if char == "\n":
            self.column = 0
            self.line += 1

        pprint[id(self)]["advance"](f"(2) idx:{self.index} col:{self.column} ln:{self.line}")
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



Qprint = DebugPrint("Quantifier", (255, 255, 20))
Qprint.toggle()
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
        Qprint(f"new: '{quant}' ({self.min_val}:{self.max_val})", color=(255,255,0))

    def check(self, value):
        if value:
            self.next()
            if self.max_val == -1:
                if self.current < self.min_val:
                    Qprint[id(self)]["check"](f"need more values! min:{self.min_val} current:{self.current}")
                    return "need"
                Qprint[id(self)]["check"](f"valid value! min:{self.min_val} current:{self.current}")
                return "valid"
                
            elif self.current == self.max_val:
                Qprint[id(self)]["check"](f"max values reached! {self.min_val}<={self.current}<={self.max_val}")
                return "done"

            elif self.current > self.max_val:
                Qprint[id(self)]["check"](f"max values exceeded!? max:{self.max_val} current:{self.current}")
                raise Exception("quantifier went over!")

        else:
            if self.current < self.min_val:
                Qprint[id(self)]["check"](f"not enough values! current:{self.current} min:{self.min_val}")
                return "not-enough"
            Qprint[id(self)]["check"](f"quantifier satisfied! {self.min_val}<={self.current} max:{self.max_val}")
            return "done"

    def next(self):
        Qprint[id(self)](f"next")
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

