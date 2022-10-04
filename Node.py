from Util import DebugPrint

Nprint = DebugPrint("Node", (0, 255, 255))
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

nbprint = DebugPrint("NodeBuilder", (0, 50, 200))
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
        nbprint(Node._nodes)
        return Node