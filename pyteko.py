import argparse

from src.parser import TekoParser

parser = argparse.ArgumentParser()
parser.add_argument('file', metavar="path/to/file", type=str,
                    help = ".to file to interpret")

if __name__ == "__main__":
    args = parser.parse_args()
        
    tp = TekoParser(args.file)
    cb = tp.parse()
    for stmt in cb.statements:
        print()
        for tag in stmt:
            print(tag)
