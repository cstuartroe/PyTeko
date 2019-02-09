def TekoException(message, line_number):
    print("Teko interpreter exception (line %s): %s" % (line_number,message))
    quit()

def TekoAssert(b):
    try:
        assert(b)
    except AssertionError as e:
        TekoException(message)
