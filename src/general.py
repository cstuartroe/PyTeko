def TekoException(message):
    print("Teko interpreter exception:",message)
    quit()

def TekoAssert(b):
    try:
        assert(b)
    except AssertionError as e:
        TekoException(message)
