HW8 for Harvard's cloud computing course
========================================

# Requirements
- Python 2.7+
- Internet connection

# Install package dependencies
Open up your console, `cd` to this directory, run:
```
pip install -r requirements.txt
```

On Windows you'll additionally need [PyWin32](http://sourceforge.net/projects/pywin32)

# Run project
```
python -c "from os.path import join; from os import getcwd; execfile(join(getcwd(), 'hw7', 'server.py'))"
```

(or just use your OS-specific path to specify that you want to execute that file, e.g.: `./hw7/server.py`)
