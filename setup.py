from cx_Freeze import setup, Executable

base = None    

executables = [Executable("teko.py", base=base)]

packages = ["idna"]
options = {
    'build_exe': {    
        'packages':packages,
    },    
}

setup(
    name = "teko",
    options = options,
    version = "0.0",
    description = 'a python implementation of Teko',
    executables = executables
)
