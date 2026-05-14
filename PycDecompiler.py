import os
import sys
import time
import shutil
import subprocess
import marshal
import base64
import zlib
import importlib.util
import tempfile
from typing import Optional

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    DIM = '\033[2m'
    MAGENTA = '\033[95m'
    ORANGE = '\033[38;5;208m'
    PINK = '\033[38;5;206m'
    TEAL = '\033[38;5;44m'
    PURPLE = '\033[38;5;141m'
    GOLD = '\033[38;5;220m'

class FileNotPyc(Exception):
    pass

class DecompilationError(Exception):
    pass

def remove_dir(path: str):
    try:
        shutil.rmtree(path)
    except Exception:
        pass

def get_python_executable():
    try:
        return __cpy_syspath__ + "\\python.exe"
    except NameError:
        return sys.executable

def get_current_python_version():
    return ".".join(sys.version.split()[0].split(".")[:-1])

magic_map = {
    "3.6": b"3\r\r\n\x8bq\x98d\x0c\x00\x00\x00\xe3\x00\x00\x00",
    "3.7": b"B\r\r\n\x00\x00\x00\x00\x8bq\x98d\x0c\x00\x00\x00",
    "3.8": b"U\r\r\n\x00\x00\x00\x00\tq\x98d\x0b\x00\x00\x00",
    "3.9": b"a\r\r\n\x00\x00\x00\x00\tq\x98d\x0b\x00\x00\x00",
    "3.10": b"o\r\r\n\x00\x00\x00\x00\tq\x98d\x0b\x00\x00\x00",
    "3.11": b"\xa7\r\r\n\x00\x00\x00\x004\x0eAi\n\x00\x00\x00",
    "3.12": b"\xcb\r\r\n\x00\x00\x00\x00{\x0eAi\n\x00\x00\x00",
    "3.13": b"\xf3\r\r\n\x00\x00\x00\x00\x90\x0eAi\n\x00\x00\x00",
}

def get_pyc_magic(pyver: str) -> bytes:
    return magic_map.get(pyver, magic_map[get_current_python_version()])

def print_banner():
    banner = f"""
{Colors.CYAN}{'='*65}{Colors.END}
{Colors.BOLD}{Colors.MAGENTA}    ____        __    _                         __{Colors.END}
{Colors.BOLD}{Colors.PINK}   / __ \\__  __/ /   (_)___  ____ ___  ______ _/ /{Colors.END}
{Colors.BOLD}{Colors.TEAL}  / /_/ / / / / /   / / __ \\/ __ `/ / / / __ `/ /{Colors.END}
{Colors.BOLD}{Colors.GREEN} / ____/ /_/ / /___/ / / / / /_/ / /_/ / /_/ / /{Colors.END}
{Colors.BOLD}{Colors.YELLOW}/_/    \\__, /_____/_/_/ /_/\\__, /\\__,_/\\__,_/_/{Colors.END}
{Colors.BOLD}{Colors.ORANGE}      /____/              /____/{Colors.END}
{Colors.CYAN}{'='*65}{Colors.END}
{Colors.BOLD}{Colors.GOLD}{'P Y L I N G U A L'.center(65)}{Colors.END}
{Colors.CYAN}{'='*65}{Colors.END}
{Colors.GREEN}[ + ] Program:{Colors.END}
{Colors.CYAN}    -> Marshal/PYC Converter & Decompiler{Colors.END}
    
{Colors.BLUE}[ * ] Features:{Colors.END}
{Colors.TEAL}    -> Convert Marshal to PYC (Python 3.6-3.13){Colors.END}
{Colors.PURPLE}    -> Decompile PYC to Python Source{Colors.END}
    
{Colors.YELLOW}[ </> ] Developer:{Colors.END}
{Colors.PINK}    -> Github   : @GhostPlugger{Colors.END}
{Colors.ORANGE}    -> Telegram : @Asteix{Colors.END}
{Colors.CYAN}{'='*65}{Colors.END}
"""
    print(banner)

def marshal_to_pyc(input_file: str, pyver: str = None) -> str:
    if pyver is None:
        pyver = get_current_python_version()
    print(f"\n{Colors.BLUE}[ * ]{Colors.END} Converting Marshal to PYC (Python {Colors.YELLOW}{pyver}{Colors.END})...")
    try:
        with open(input_file, "rb") as f:
            data = f.read()
        base_path = os.path.dirname(input_file)
        if base_path:
            base_path += os.sep
        filename = os.path.basename(input_file)
        name_only = ".".join(filename.split(".")[:-1])
        remove_dir("__pycache__")
        hook_code = '\nimport marshal, sys\n\ndef loads(data, *_):\n    open("temp_marshal.pyc", "wb").write(data)\n    sys.exit(0)\n'
        hook_payload = marshal.dumps(compile(hook_code, "<marshal_hook>", "exec"))
        encoded = base64.b64encode(zlib.compress(hook_payload))[::-1]
        with open("marshal_hook.py", "w") as f:
            f.write(
                f"import base64, zlib, marshal\nexec(marshal.loads(zlib.decompress(base64.b64decode({encoded}[::-1]))), globals())"
            )
        exec_code = (
            b"\nimport marshal_hook, sys\nsys.modules['marshal'] = marshal_hook\n"
            + data
        )
        exec_payload = marshal.dumps(compile(exec_code, "<exec>", "exec"))
        encoded_exec = base64.b64encode(zlib.compress(exec_payload))[::-1]
        with open("runner.py", "w") as f:
            f.write(
                f"import base64, zlib, marshal\nexec(marshal.loads(zlib.decompress(base64.b64decode({encoded_exec}[::-1]))), globals())"
            )
        subprocess.run(
            [get_python_executable(), "runner.py"],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
        os.remove("marshal_hook.py")
        os.remove("runner.py")
        try:
            with open("temp_marshal.pyc", "rb") as f:
                marshal_data = f.read()
            os.remove("temp_marshal.pyc")
            pyc_path = f"{base_path}{name_only}.pyc"
            with open(pyc_path, "wb") as f:
                f.write(get_pyc_magic(pyver) + marshal_data)
            print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Saved: {Colors.CYAN}{pyc_path}{Colors.END}")
            remove_dir("__pycache__")
            return pyc_path
        except FileNotFoundError:
            print(f"{Colors.RED}[ ! ]{Colors.END} Not a valid marshal file")
            remove_dir("__pycache__")
            return None
    except Exception as e:
        print(f"{Colors.RED}[ ! ]{Colors.END} Error: {e}")
        remove_dir("__pycache__")
        return None

def validate_pyc_file(file_path: str) -> None:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.endswith(".pyc"):
        raise FileNotPyc(f"File must have .pyc extension: {file_path}")

def check_uncompyle6():
    try:
        import uncompyle6
        return True
    except ImportError:
        return False

def install_uncompyle6():
    print(f"{Colors.BLUE}[ * ]{Colors.END} Installing uncompyle6...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "uncompyle6"], 
                      capture_output=True, text=True)
        return check_uncompyle6()
    except Exception as e:
        print(f"{Colors.RED}[ ! ]{Colors.END} Failed to install uncompyle6: {e}")
        return False

def decompile_with_pycdc(file_path: str, output_path: str) -> bool:
    try:
        import urllib.request
        import zipfile
        import stat
        
        pycdc_path = os.path.join(tempfile.gettempdir(), "pycdc")
        
        if not os.path.exists(pycdc_path):
            print(f"{Colors.BLUE}[ * ]{Colors.END} Downloading pycdc...")
            if sys.platform == "win32":
                url = "https://github.com/zrax/pycdc/releases/download/v1.0/pycdc.exe"
                pycdc_exe = os.path.join(pycdc_path, "pycdc.exe")
            else:
                url = "https://github.com/zrax/pycdc/releases/download/v1.0/pycdc_linux"
                pycdc_exe = os.path.join(pycdc_path, "pycdc")
            
            os.makedirs(pycdc_path, exist_ok=True)
            urllib.request.urlretrieve(url, pycdc_exe)
            if sys.platform != "win32":
                os.chmod(pycdc_exe, os.stat(pycdc_exe).st_mode | stat.S_IEXEC)
        
        result = subprocess.run([pycdc_exe, file_path], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            return True
        return False
    except Exception as e:
        return False

def decompile_pyc_local(file_path: str) -> str:
    base_name = os.path.basename(file_path)
    output_name = "decoded_" + base_name.replace(".pyc", ".py")
    output_path = os.path.join(os.path.dirname(file_path) or ".", output_name)
    
    print(f"{Colors.BLUE}[ * ]{Colors.END} Decompiling PYC file...")
    
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(4)
            bit_field = f.read(4)
            timestamp = f.read(4)
            size = f.read(4)
            code_obj = marshal.load(f)
        
        import dis
        import types
        
        temp_py_path = output_path
        
        if check_uncompyle6():
            import uncompyle6
            import io
            
            print(f"{Colors.BLUE}[ * ]{Colors.END} Using uncompyle6...")
            out = io.StringIO()
            uncompyle6.decompile(3.8, code_obj, out)
            decompiled_code = out.getvalue()
            
            with open(temp_py_path, 'w', encoding='utf-8') as f:
                f.write(decompiled_code)
            
            if os.path.getsize(temp_py_path) > 100:
                print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Successfully decompiled with uncompyle6!")
                return output_path
        
        print(f"{Colors.YELLOW}[ * ]{Colors.END} Trying pycdc...")
        if decompile_with_pycdc(file_path, temp_py_path):
            if os.path.getsize(temp_py_path) > 100:
                print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Successfully decompiled with pycdc!")
                return output_path
        
        print(f"{Colors.BLUE}[ * ]{Colors.END} Extracting raw code object...")
        with open(temp_py_path, 'w', encoding='utf-8') as f:
            f.write("# Decompiled code object\n\n")
            f.write("import marshal\n\n")
            f.write(f"# Code object extracted from {file_path}\n")
            f.write("# This is the raw code object, manual analysis needed\n\n")
            f.write("code_obj = " + repr(code_obj) + "\n\n")
            f.write("# To execute this code object:\n")
            f.write("# exec(code_obj)\n")
        
        print(f"{Colors.YELLOW}[ ! ]{Colors.END} Partial decompilation - code object extracted")
        return output_path
        
    except Exception as e:
        import dis
        
        print(f"{Colors.BLUE}[ * ]{Colors.END} Extracting bytecode with dis...")
        
        with open(file_path, 'rb') as f:
            f.read(12)
            try:
                code_obj = marshal.load(f)
            except:
                f.seek(0)
                code_obj = marshal.load(f)
        
        temp_py_path = output_path
        
        with open(temp_py_path, 'w', encoding='utf-8') as f:
            f.write(f"# Bytecode extracted from {file_path}\n")
            f.write("# This is low-level bytecode representation\n\n")
            f.write("import dis\nimport marshal\n\n")
            f.write("code_obj = " + repr(code_obj) + "\n\n")
            f.write("# Bytecode disassembly:\n")
            f.write("# dis.dis(code_obj)\n\n")
            
            original_stdout = sys.stdout
            from io import StringIO
            dis_output = StringIO()
            sys.stdout = dis_output
            try:
                dis.dis(code_obj)
            finally:
                sys.stdout = original_stdout
            
            f.write("# DISASSEMBLY:\n")
            for line in dis_output.getvalue().split('\n'):
                f.write(f"# {line}\n")
        
        print(f"{Colors.YELLOW}[ ! ]{Colors.END} Bytecode extracted to {temp_py_path}")
        print(f"{Colors.RED}[ ! ]{Colors.END} Full decompilation failed - bytecode extracted for manual analysis")
        return output_path

def decompile_pyc(file_path: str) -> None:
    total_start_time = time.time()
    try:
        print(f"\n{Colors.BLUE}[ * ]{Colors.END} Processing: {Colors.CYAN}{file_path}{Colors.END}")
        validate_pyc_file(file_path)
        print(f"{Colors.GREEN}[ ✓ ]{Colors.END} File validated")
        
        output_path = decompile_pyc_local(file_path)
        
        total_time = time.time() - total_start_time
        print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Output saved to: {Colors.CYAN}{output_path}{Colors.END}")
        print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Total execution time: {Colors.YELLOW}{total_time:.2f}s{Colors.END}")
    except FileNotFoundError as e:
        print(f"{Colors.RED}[ ! ]{Colors.END} File Error: {e}")
        raise
    except FileNotPyc as e:
        print(f"{Colors.RED}[ ! ]{Colors.END} Format Error: {e}")
        raise
    except DecompilationError as e:
        print(f"{Colors.RED}[ ! ]{Colors.END} Decompilation Error: {e}")
        raise
    except Exception as e:
        print(f"{Colors.RED}[ ! ]{Colors.END} Unexpected Error: {e}")
        raise

def show_menu():
    print(f"\n{Colors.CYAN}{'='*55}{Colors.END}")
    print(f"{Colors.GREEN}[ 1 ]{Colors.END} Convert Marshal to PYC")
    print(f"{Colors.BLUE}[ 2 ]{Colors.END} Decompile PYC to Python Source")
    print(f"{Colors.RED}[ 0 ]{Colors.END} Exit")
    print(f"{Colors.CYAN}{'='*55}{Colors.END}")

def select_python_version():
    print(f"\n{Colors.CYAN}{'='*55}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}Available Python Versions:{Colors.END}")
    versions = list(magic_map.keys())
    for i, ver in enumerate(versions, 1):
        print(f"{Colors.GREEN}[ {i} ]{Colors.END} Python {Colors.CYAN}{ver}{Colors.END}")
    print(f"{Colors.RED}[ 0 ]{Colors.END} Current Version ({Colors.YELLOW}{get_current_python_version()}{Colors.END})")
    print(f"{Colors.CYAN}{'='*55}{Colors.END}")
    while True:
        try:
            choice = input(f"{Colors.BLUE}[ ? ]{Colors.END} Select version: ").strip()
            if choice == "0" or choice == "":
                return get_current_python_version()
            idx = int(choice) - 1
            if 0 <= idx < len(versions):
                return versions[idx]
            else:
                print(f"{Colors.RED}[ ! ]{Colors.END} Invalid choice!")
        except ValueError:
            print(f"{Colors.RED}[ ! ]{Colors.END} Enter a valid number!")

def interactive_mode():
    os.system("cls" if os.name == "nt" else "clear")
    print_banner()
    while True:
        show_menu()
        choice = input(f"{Colors.BLUE}[ ? ]{Colors.END} Select option: ").strip()
        if choice == "0":
            print(f"\n{Colors.GREEN}[ ✓ ]{Colors.END} Goodbye!")
            sys.exit(0)
        elif choice == "1":
            file_path = (
                input(f"\n{Colors.BLUE}[ ? ]{Colors.END} Enter Marshal file path: ").strip().replace('"', "")
            )
            if not os.path.exists(file_path):
                print(f"{Colors.RED}[ ! ]{Colors.END} File not found!")
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.END}")
                continue
            pyver = select_python_version()
            result = marshal_to_pyc(file_path, pyver)
            if result:
                print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Done!")
            input(f"\n{Colors.DIM}Press Enter to continue...{Colors.END}")
        elif choice == "2":
            file_path = input(f"\n{Colors.BLUE}[ ? ]{Colors.END} Enter PYC file path: ").strip().replace('"', "")
            try:
                decompile_pyc(file_path)
                print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Done!")
            except Exception:
                pass
            input(f"\n{Colors.DIM}Press Enter to continue...{Colors.END}")
        else:
            print(f"{Colors.RED}[ ! ]{Colors.END} Invalid option!")
            input(f"\n{Colors.DIM}Press Enter to continue...{Colors.END}")

def cli_mode(file_path: str, pyver: str = None):
    if pyver is None:
        pyver = get_current_python_version()
    if not os.path.exists(file_path):
        print(f"{Colors.RED}[ ! ]{Colors.END} File not found: {file_path}")
        sys.exit(1)
    if file_path.endswith(".pyc"):
        print(f"{Colors.GREEN}[ * ]{Colors.END} Detected: PYC file")
        try:
            decompile_pyc(file_path)
            print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Done!")
        except Exception:
            sys.exit(1)
    elif file_path.endswith(".py"):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            if b"marshal" in content:
                print(f"{Colors.GREEN}[ * ]{Colors.END} Detected: Marshal file")
                pyc_file = marshal_to_pyc(file_path, pyver)
                if pyc_file:
                    print(f"\n{Colors.BLUE}[ * ]{Colors.END} Now decompiling PYC...")
                    try:
                        decompile_pyc(pyc_file)
                        print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Done!")
                    except Exception:
                        sys.exit(1)
                else:
                    sys.exit(1)
            else:
                print(f"{Colors.RED}[ ! ]{Colors.END} Not a marshal file")
                sys.exit(1)
        except Exception as e:
            print(f"{Colors.RED}[ ! ]{Colors.END} Error: {e}")
            sys.exit(1)
    else:
        print(f"{Colors.RED}[ ! ]{Colors.END} Unsupported file type (must be .pyc or .py)")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        pyver = sys.argv[2] if len(sys.argv) > 2 else None
        if pyver and pyver not in magic_map:
            print(f"{Colors.RED}[ ! ]{Colors.END} Invalid Python version: {pyver}")
            print(f"{Colors.BLUE}[ * ]{Colors.END} Available versions: {', '.join(magic_map.keys())}")
            sys.exit(1)
        cli_mode(file_path, pyver)
    else:
        interactive_mode()
