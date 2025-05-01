import typing as ty

#This whole file exists just so I can use Haskell-like type annotations in my Python code
#I know am oppsessed with Haskell, its an addiction at this point 😂!

class Type:
    def __init__(self, out):
        self.out = out
    def __rshift__(self, x):
        return pyty.Callable[self.out, x.out]
    def __or__(self, x):
        return Union[self, x]
    def __repr__(self):
        return str(self.out)

class TypeFunc:
    def __init__(self, out):
        self.out = out
    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = (args, )
        a = [n.out if n != ... else ... for n in args]
        return Type(self.out[a])
    def __repr__(self):
        return f'{self.__name__}[{self.out}]'

Int = Type(int)
Str = Type(str)
Float = Type(float)

List = TypeFunc(ty.List)
Tuple = TypeFunc(ty.Tuple)
Maybe = TypeFunc(ty.Optional)
Union = TypeFunc(ty.Union)
