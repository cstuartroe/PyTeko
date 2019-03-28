import argparse

from src.framework import TekoModule, StandardLibrary

parser = argparse.ArgumentParser()
parser.add_argument('file', metavar="path/to/file", type=str,
                    help = ".to file to interpret")

if __name__ == "__main__":
    args = parser.parse_args()

    module = TekoModule(name="__main__", filename = args.file, outers = [StandardLibrary])
    module.interpret()
