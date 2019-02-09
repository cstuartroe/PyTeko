import argparse

from src.tokenizer import tokenize
from src.tagger import get_tags

parser = argparse.ArgumentParser()
parser.add_argument('file', metavar="path/to/file", type=str,
                    help = ".to file to interpret")

if __name__ == "__main__":
    args = parser.parse_args()
    with open(args.file,"r") as fh:
        source = fh.read()
    ts = tokenize(source)
    tags = get_tags(ts)
    for tag in tags:
        print(tag)
