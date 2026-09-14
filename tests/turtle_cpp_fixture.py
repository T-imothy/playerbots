from pathlib import Path
import shutil, subprocess, tempfile
def run(code, includes=()):
    with tempfile.TemporaryDirectory(prefix='turtle-owner-') as temp:
        d=Path(temp); p=d/'fixture.cpp'; p.write_text(code,encoding='utf-8')
        cl=shutil.which('cl'); compiler=cl or shutil.which('c++')
        if not compiler: raise SystemExit('Run in a C++17 compiler environment.')
        exe=d/('fixture.exe' if cl else 'fixture')
        command=([cl,'/nologo','/std:c++17','/EHsc','/MD','/O2',str(p),'/Fe'+str(exe),'/Fo'+str(d/'fixture.obj')]+['/I'+str(i) for i in includes]) if cl else ([compiler,'-std=c++17','-pthread',str(p),'-o',str(exe)]+['-I'+str(i) for i in includes])
        subprocess.run(command,cwd=d,check=True);subprocess.run([str(exe)],check=True,cwd=d)
