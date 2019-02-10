import argparse

from src.parser import TekoParser

parser = argparse.ArgumentParser()
parser.add_argument('file', metavar="path/to/file", type=str,
                    help = ".to file to interpret")

if __name__ == "__main__":
    args = parser.parse_args()
        
    tp = TekoParser(args.file)
    for stmt in tp.parse():
        print(stmt)
