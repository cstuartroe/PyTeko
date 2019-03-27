import argparse

from src.parser import TekoParser
from src.primitives import * # TekoModule
from src.interpreter import TekoInterpreter

parser = argparse.ArgumentParser()
parser.add_argument('file', metavar="path/to/file", type=str,
                    help = ".to file to interpret")

if __name__ == "__main__":
    args = parser.parse_args()
        
    tp = TekoParser(args.file)
    stmts = list(tp.parse())

    module = TekoModule(name="__main__", owner=StandardLibrary) # switch to TekoModule()
    ti = TekoInterpreter(module)
    print("---Beginning Teko Interpretation---")
    for stmt in stmts:
        ti.exec(stmt)
