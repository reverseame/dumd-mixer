# Dump Module Mixer 

`dumd-mixer` is a Python3 script to generate a given Windows module from the same module extracted from a collection of memory dumps. Its workflow comprises three steps:

* Extraction of the given module (either an executable or a system library) from a set of memory dumps. Of course, the memory dumps must be taken from the same machine! Otherwise, the behavior of the tool is unreliable.
* Mixing of the extracted modules. Using information provided by the previous step, the extracted modules are iterated checking which memory pages were found. Every memory page is inserted in a tree-like structure (in particular, an AVL tree), guaranteeing no repetitions of memory pages. 
* Generation of the mixed file. Walking through the tree-like structure, a new file is created considering the memory pages from the corresponding extracted module indicated by each node in the tree.

It relies on the Volatility memory framework and its plugin [`similarity-unrelocated-module`](https://github.com/reverseame/similarity-unrelocated-module) (`sum`). Invoking the plugin `sum` with the appropriate parameters, a log file is obtained that describes the memory pages of a given process or system library which are present in memory. The collection of logs is mixed using an AVL tree structure to optimize the insertion and in-order operations.

## Requirements

- Python 3.5 (tested on Python 3.8.4rc1 on top of Debian GNU/Linux bullseye/sid 8.11)
- Python 2.7 (needed for Volatility)
- [`volatility`](https://github.com/volatilityfoundation/volatility)
- [`similarity-unrelocated-module`](https://github.com/reverseame/similarity-unrelocated-module)

Use the [`config.ini`](config.ini) to specify the path to these binaries. You can use either absolute or relative paths.

## Usage

```
usage: dumd-mixer.py [-h] [-o OUTFILE] [-d out_dir] [-p vol_profile] [-s size] MODULE-NAME DUMPS-FOLDER
Creates a single module file combining the same MODULE-NAME extracted from a set of dumps, contained in DUMPS-FOLDER

Options:
    -h, --help
            List all available options and their default values.
            Default values for Python2.7, Volatility, and SUM plugin are set in the configuration file (see "config.ini")
    -d, --dir=output
            Output folder name where the mixed file is stored (default value is "output")
    -o, --output=OUTFILE
            Output filename that contains the combined module (default value is MODULE-NAME postfixed with ".mixed")
    -p, --profile=PROFILE
            Volatility profile name of the dumps (use Volatility syntax)
    -s, --page-size=4096
            Page size to be considered (default value is 4096)

```

## Usage example

```
$ python3 dumd-mixer.py -p Win7SP1x86 -o kernel32.mix -d tmp kernel32 ~/temp/
[>] Ready to parse dumps in "/home/ricardo/temp/" to extract kernel32 module
[*] Starting extraction phase ... done!
INFO:main:[*] Total nodes before processing "/home/ricardo/dumd-mixer/tmp/csrss.exe-372-kernel32.dll-PE-76a80000.dmp": 0
INFO:main:[*] Number of memory pages to process: 20
INFO:main:[*] Total nodes after processing "/home/ricardo/dumd-mixer/tmp/csrss.exe-372-kernel32.dll-PE-76a80000.dmp": 20
INFO:main:[*] Total nodes before processing "/home/ricardo/dumd-mixer/tmp/Explorer.EXE-328-kernel32.dll-PE-76a80000.dmp": 20
INFO:main:[*] Number of memory pages to process: 62
INFO:main:[*] Total nodes after processing "/home/ricardo/dumd-mixer/tmp/Explorer.EXE-328-kernel32.dll-PE-76a80000.dmp": 62
INFO:main:[*] Total nodes before processing "/home/ricardo/dumd-mixer/tmp/wmpnetwk.exe-1768-kernel32.dll-PE-76a80000.dmp": 62
INFO:main:[*] Number of memory pages to process: 47
INFO:main:[*] Total nodes after processing "/home/ricardo/dumd-mixer/tmp/wmpnetwk.exe-1768-kernel32.dll-PE-76a80000.dmp": 64
INFO:main:[*] Total nodes before processing "/home/ricardo/dumd-mixer/tmp/svchost.exe-3432-kernel32.dll-PE-76a80000.dmp": 64
INFO:main:[*] Number of memory pages to process: 36
INFO:main:[*] Total nodes after processing "/home/ricardo/dumd-mixer/tmp/svchost.exe-3432-kernel32.dll-PE-76a80000.dmp": 66
INFO:main:[*] Total nodes before processing "/home/ricardo/dumd-mixer/tmp/notepad++.exe-1964-kernel32.dll-PE-76a80000.dmp": 66
INFO:main:[*] Number of memory pages to process: 57
INFO:main:[*] Total nodes after processing "/home/ricardo/dumd-mixer/tmp/notepad++.exe-1964-kernel32.dll-PE-76a80000.dmp": 69
INFO:main:[*] Total nodes before processing "/home/ricardo/dumd-mixer/tmp/cmd.exe-2100-kernel32.dll-PE-76a80000.dmp": 69
INFO:main:[*] Number of memory pages to process: 65
INFO:main:[*] Total nodes after processing "/home/ricardo/dumd-mixer/tmp/cmd.exe-2100-kernel32.dll-PE-76a80000.dmp": 81
INFO:main:[*] Total nodes before processing "/home/ricardo/dumd-mixer/tmp/conhost.exe-568-kernel32.dll-PE-76a80000.dmp": 81
INFO:main:[*] Number of memory pages to process: 46
INFO:main:[*] Total nodes after processing "/home/ricardo/dumd-mixer/tmp/conhost.exe-568-kernel32.dll-PE-76a80000.dmp": 81
INFO:main:[*] Total nodes before processing "/home/ricardo/dumd-mixer/tmp/test.exe-2976-kernel32.dll-PE-76a80000.dmp": 81
INFO:main:[*] Number of memory pages to process: 28
INFO:main:[*] Total nodes after processing "/home/ricardo/dumd-mixer/tmp/test.exe-2976-kernel32.dll-PE-76a80000.dmp": 81
[*] Starting mixing phase ... done!
[*] Starting generation of mixed module phase ... done!
[>] Module kernel32 extracted successfully to /home/ricardo/dumd-mixer/tmp/kernel32.mix (81 out of 212 memory pages retrieved)
```

It extracts the system library "kernel32" from the memory dumps contained in ~/temp, analyzing them considering the Volatility profile Win7SP1x86. As a result, a file named `kernel32.mix` is obtained which contains 81 memory pages out of 212 memory pages of the system library `kernel32.dll`, as stated by the output.

Note that if you extract this system library from a single process in a memory dump its content is partial. In the INFO messages you can see how the number of pages increases after processing different dumps of the same module, retrieved from different processes within the same memory dump.

## License

Licensed under the [GNU GPLv3](LICENSE) license.
