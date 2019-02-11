import argparse

from src.parser import TekoParser
from src.interpreter import TekoInterpreter

parser = argparse.ArgumentParser()
parser.add_argument('file', metavar="path/to/file", type=str,
                    help = ".to file to interpret")

if __name__ == "__main__":
    args = parser.parse_args()
        
    tp = TekoParser(args.file)
    stmts = list(tp.parse())

    ti = TekoInterpreter()
    for stmt in stmts:
        ti.exec(stmt)
