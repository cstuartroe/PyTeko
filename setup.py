from cx_Freeze import setup, Executable

base = None    

executables = [Executable("pyteko.py", base=base)]

packages = ["idna"]
options = {
    'build_exe': {    
        'packages':packages,
    },    
}

setup(
    name = "pyteko",
    options = options,
    version = "0.0",
    description = 'a python implementation of Teko',
    executables = executables
)
