import os
import sys
import time
import shutil
import subprocess
import marshal
import base64
import zlib
import importlib.util
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

def decompile_pyc_local(file_path: str) -> str:
    if not check_uncompyle6():
        print(f"{Colors.YELLOW}[ * ]{Colors.END} uncompyle6 not found. Installing...")
        if not install_uncompyle6():
            raise DecompilationError("uncompyle6 is required for decompilation. Please install it manually: pip install uncompyle6")
    
    base_name = os.path.basename(file_path)
    output_name = "decoded_" + base_name.replace(".pyc", ".py")
    output_path = os.path.join(os.path.dirname(file_path) or ".", output_name)
    
    print(f"{Colors.BLUE}[ * ]{Colors.END} Decompiling using uncompyle6...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "uncompyle6", "-o", output_path, file_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            import uncompyle6
            import struct
            import dis
            import tempfile
            
            print(f"{Colors.BLUE}[ * ]{Colors.END} Trying alternative decompilation method...")
            
            with open(file_path, 'rb') as f:
                magic = f.read(4)
                bit_field = f.read(4)
                timestamp = f.read(4)
                size = f.read(4)
                code_obj = marshal.load(f)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
                tmp_path = tmp.name
            
            uncompyle6.decompile_file(open(file_path, 'rb'), open(tmp_path, 'w'))
            
            with open(tmp_path, 'r') as f:
                code = f.read()
            
            os.unlink(tmp_path)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(code)
        
        print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Decompiled successfully!")
        return output_path
        
    except Exception as e:
        raise DecompilationError(f"Decompilation failed: {e}")

def decompile_pyc(file_path: str) -> None:
    total_start_time = time.time()
    try:
        print(f"\n{Colors.BLUE}[ * ]{Colors.END} Processing: {Colors.CYAN}{file_path}{Colors.END}")
        validate_pyc_file(file_path)
        print(f"{Colors.GREEN}[ ✓ ]{Colors.END} File validated")
        
        output_path = decompile_pyc_local(file_path)
        
        total_time = time.time() - total_start_time
        print(f"{Colors.GREEN}[ ✓ ]{Colors.END} Decompiled code saved to: {Colors.CYAN}{output_path}{Colors.END}")
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
