import sys

def TekoException(message, line_number):
    print("Teko interpreter exception (line %s): %s" % (line_number,message))
    sys.exit()

def TekoAssert(b):
    try:
        assert(b)
    except AssertionError as e:
        TekoException(message)
