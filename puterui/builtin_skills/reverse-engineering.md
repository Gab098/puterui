# Reverse Engineering
> Binary analysis, malware analysis, and reverse engineering techniques

## Static Analysis
1. **File identification**: `file`, `binwalk`, magic bytes
2. **Strings extraction**: `strings`, FLOSS for obfuscated strings
3. **Headers**: ELF headers (`readelf`), PE headers (`pestudio`)
4. **Disassembly**: Ghidra, radare2/rizin, IDA, Binary Ninja
5. **Decompilation**: Ghidra decompiler, RetDec, JEB for Android
6. **Symbol analysis**: Exported/imported functions, libraries

## Dynamic Analysis
1. **Debugging**: gdb, x64dbg, lldb, WinDbg
2. **Tracing**: strace, ltrace, Process Monitor
3. **Network**: Wireshark, tcpdump, mitmproxy
4. **Sandboxing**: Any.run, Cuckoo, Docker isolation
5. **Hooking**: Frida, LD_PRELOAD, DLL injection

## Binary Exploitation
1. **Buffer overflow**: Stack-based, heap-based
2. **Format string**: Read/write arbitrary memory
3. **ROP chains**: Return-oriented programming
4. **Shellcode**: Writing and encoding shellcode
5. **Protections**: ASLR, DEP/NX, stack canaries, PIE, RELRO
6. **Bypass**: ret2libc, ret2plt, GOT overwrite, one_gadget

## CTF Approach
1. Check file type and protections (`checksec`)
2. Run the binary to understand behavior
3. Disassemble/decompile key functions
4. Identify vulnerability class
5. Develop exploit locally
6. Adapt for remote target

## Malware Analysis
1. **Triage**: Hash lookup (VirusTotal), basic static analysis
2. **Behavioral**: Run in sandbox, monitor file/network/registry
3. **Code analysis**: Decompile, identify C2, encryption, persistence
4. **IOCs**: Extract domains, IPs, file hashes, mutexes
5. **YARA rules**: Write signatures for detection

## Tools Reference
- **Disassembly**: Ghidra, radare2, rizin, objdump
- **Debugging**: gdb + pwndbg/gef, x64dbg
- **Exploitation**: pwntools, ROPgadget, one_gadget
- **Malware**: YARA, ssdeep, pestudio, PE-bear
- **Android**: apktool, jadx, Frida
