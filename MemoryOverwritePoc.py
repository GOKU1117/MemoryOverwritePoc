import os
import time
import ctypes
import win32api
import win32con
import subprocess
import win32process


PROCESS_ALL_ACCESS = 0x1F0FFF
PAGE_EXECUTE_READWRITE = 0x40
wplsoft_path = r"C:\Program Files (x86)\Delta Industrial Automation\WPLSoft 2.52\WPLSoft.exe"
data_segment_start = 0x635000
buffer_size = 635000

def get_process_id(process_name):
    for proc in win32process.EnumProcesses():
        try:
            h_process = win32api.OpenProcess(PROCESS_ALL_ACCESS, False, proc)
            exe_name = win32process.GetModuleFileNameEx(h_process, 0)
            if process_name in exe_name:
                return proc
        except Exception:
            continue
    return None

def read_memory(process_id, address, size):
    process_handle = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, process_id)
    buffer = ctypes.create_string_buffer(size)
    bytesRead = ctypes.c_size_t(0)
    ctypes.windll.kernel32.ReadProcessMemory(process_handle, address, buffer, size, ctypes.byref(bytesRead))
    ctypes.windll.kernel32.CloseHandle(process_handle)
    return buffer.raw

def write_memory(process_id, address, data):
    process_handle = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, process_id)
    old_protect = ctypes.c_ulong()
    success = ctypes.windll.kernel32.VirtualProtectEx(process_handle, address, len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect))
    if not success:
        print("Failed to change memory protection.")
        ctypes.windll.kernel32.CloseHandle(process_handle)
        return 0
    bytes_written = ctypes.c_size_t(0)
    success = ctypes.windll.kernel32.WriteProcessMemory(process_handle, address, data, len(data), ctypes.byref(bytes_written))
    if not success:
        print(f"WriteProcessMemory failed with error code: {ctypes.windll.kernel32.GetLastError()}")
    ctypes.windll.kernel32.VirtualProtectEx(process_handle, address, len(data), old_protect, ctypes.byref(old_protect))
    ctypes.windll.kernel32.CloseHandle(process_handle)
    return bytes_written.value

def monitor_process(process_id):
    while True:
        try:
            h_process = win32api.OpenProcess(PROCESS_ALL_ACCESS, False, process_id)
            exit_code = win32process.GetExitCodeProcess(h_process)
            if exit_code != win32con.STILL_ACTIVE:
                print(f"Process {process_id} has exited, exit code: {exit_code}")
                break
            print(f"Process {process_id} is running...")
            time.sleep(2)  
        except Exception as e:
            print(f"Error during monitoring: {e}")
            break
        
try:
    print("Starting WPLSoft...")
    subprocess.Popen(wplsoft_path)
except FileNotFoundError:
    print(f"Application not found: {wplsoft_path}")
    exit(1)

print("Waiting for the application to start...")
time.sleep(10)

process_name = "WPLSoft.exe"
process_id = get_process_id(process_name)

if process_id:
    print(f"Successfully found process {process_name}, ID: {process_id}")
    
    data_segment_content = read_memory(process_id, data_segment_start, buffer_size)
    print(f"Initial .data segment memory content (first 100 bytes): {data_segment_content[:100]}")
    
    data_to_write = os.urandom(buffer_size)
    written_bytes = write_memory(process_id, data_segment_start, data_to_write)
    print(f"Number of bytes written: {written_bytes}")
    
    if written_bytes == buffer_size:
        print(f"Successfully written to .data segment at address: 0x{data_segment_start:X}")
        modified_data = read_memory(process_id, data_segment_start, buffer_size)
        print(f".data segment memory content after writing (first 100 bytes): {modified_data[:100]}")
    else:
        print("Failed to write to the .data segment, check address and protection settings.")
    
    monitor_process(process_id)
else:
    print(f"Process {process_name} not found")
