#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''Creates a single module file combining the same module extracted from a set of memory dumps
'''

import os
import sys
import shutil
import logging
import struct
import configparser
import getopt
import glob
import subprocess
import tempfile
import ast

from avl import AVLTree

__author__ = "Ricardo J. Rodríguez"
__copyright__ = "Copyright 2020, University of Zaragoza, Spain"
__credits__ = ["Ricardo J. Rodríguez", "Miguel Martín-Pérez"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Ricardo J. Rodríguez"
__email__ = "rjrodriguez@unizar.es"
__status__ = "Production"

default_log_level = logging.WARNING
logger = logging.getLogger('main')

DEFAULT_PAGE_SIZE = 4096
DEFAULT_OUTPUT_FOLDER = 'output'

script_name = os.path.basename(__file__)
output_folder = DEFAULT_OUTPUT_FOLDER
PAGE_SIZE = DEFAULT_PAGE_SIZE
VOL_BIN = ''
SUM_PLUGIN_DIR = ''
PYTHON2_BIN = ''

help= f'''usage: {script_name} [-h] [-o OUTFILE] [-d out_dir] [-p vol_profile] [-s size] MODULE-NAME DUMPS-FOLDER
Creates a single module file combining the same MODULE-NAME extracted from a set of dumps, contained in DUMPS-FOLDER

Options:
    -h, --help
            List all available options and their default values.
            Default values for Python2.7, Volatility, and SUM plugin are set in the configuration file (see "config.ini")
    -d, --dir={DEFAULT_OUTPUT_FOLDER}
            Output folder name where the mixed file is stored (default value is "{DEFAULT_OUTPUT_FOLDER}")
    -o, --output=OUTFILE
            Output filename that contains the combined module (default value is MODULE-NAME postfixed with ".mixed")
    -p, --profile=PROFILE
            Volatility profile name of the dumps (use Volatility syntax)
    -s, --page-size={DEFAULT_PAGE_SIZE}
            Page size to be considered (default value is {DEFAULT_PAGE_SIZE})
'''

def usage_error(exit_code=0):
    print(help, file=sys.stderr)
    sys.exit(exit_code)

def main(argv):
    logging.basicConfig(level=default_log_level)
    # get optional arguments, if any
    profile = ''
    output_filename = ''
    global output_folder
    global PAGE_SIZE

    try:
        opts, _args = getopt.getopt(argv, "hd:o:p:s:",["help=", "output=", "dir=", "profile=", "page-size="])
    except getopt.GetoptError as e:
        logger.exception(e)
        usage_error(2)

    for opt, arg in opts:
      if opt in ('-h', "--help"):
         usage_error()
      elif opt in ("-d", "--dir"):
         output_folder = arg
      elif opt in ("-o", "--output"):
         output_filename = arg
      elif opt in ("-p", "--profile"):
         profile = arg
      elif opt in ("-s", "--page-size"):
         PAGE_SIZE = int(arg)

    try:
        module_name = _args[0]
        dumps_folder = _args[1]
    except:
        logger.error('Required arguments missed')
        usage_error(2)

    load_cfg_file() # load paths to binaries
    create_wd() # create working directory

    print(f'[>] Ready to parse dumps in "{dumps_folder}" to extract "{module_name}" module')
   
    # check if dumps_folder exists
    if not os.path.isdir(dumps_folder):
        logger.error(f'[-] Folder "{dumps_folder}" NOT FOUND! Please check it and launch again.')
        sys.exit(1)

    # First phase: extraction of content from dumps
    print("[*] Starting extraction phase ... ", end='')
    files = extract_module_from_dumps(dumps_folder, module_name, output_folder, profile)
    print("done!")
    # Second phase: mixing of extracted modules
    print("[*] Starting mixing phase ... ", end='')
    mix_dict, total_pages = mix_dumps_results(files)
    print('done!')
    # Third phase: generation of mixed file
    print("[*] Starting generation of mixed module phase ... ", end='')
    if output_filename == '':
        output_filename = module_name + '.mixed'
    generate_mixed_module(output_folder, mix_dict, output_filename, total_pages)
    print('done!')

    print("[>] Module {0} extracted successfully to {1} ({2} out of {3} memory pages retrieved)".format(module_name, os.path.join(output_folder, output_filename), len(mix_dict.keys()), total_pages))

def load_cfg_file(config_file='config.ini'):
    global VOL_BIN 
    global SUM_PLUGIN_DIR
    global PYTHON2_BIN

    config = configparser.ConfigParser()
    config.read(config_file)
    VOL_BIN = os.path.expanduser(os.path.normpath(config['DEFAULT']['VOL_BIN']))
    SUM_PLUGIN_DIR = os.path.expanduser(os.path.normpath(config['DEFAULT']['SUM_PLUGIN_DIR']))
    PYTHON2_BIN = os.path.normpath(config['DEFAULT']['PYTHON2_BIN'])

def execute_vol_plugin(plugin_name, dump_file, plugin_folder='', profile='', extra_params='') -> (str, int):
    '''
    Execute a Volatility plugin and get the return
    '''
    # first build the command 
    cmd = '{0} {1}'.format(PYTHON2_BIN, VOL_BIN)
    if plugin_folder != '':
        cmd += ' --plugins={0}'.format(plugin_folder)
    if profile != '': # append profile, if given 
        cmd += ' --profile={0}'.format(profile)
    if ' ' in dump_file:
        logger.warning('Please avoid white spaces in filenames, as in "{0}"'.format(dump_file))
    # XXX Volatility not recognizes the input file when putting "{0}" ?
    cmd += ' -f {0} {1} {2}'.format(dump_file, extra_params, plugin_name)
    logger.debug(f'[+] Ready to execute cmd: {cmd}')
    _completed_process = subprocess.run(cmd.split(' '), capture_output=True, close_fds=True)
    logger.debug('[+] Execution finished! Output: ' + _completed_process.stdout.decode('utf-8'))
    # check error code
    if _completed_process.returncode != 0:
        logger.error('Execution of command "{0}" finished with return code {1}'.format(cmd, _completed_process.returncode))
        return None, _completed_process.returncode

    return _completed_process.stdout.decode("utf-8"), _completed_process.returncode

def extract_module_from_dumps(dumps_folder, mod_name, out_folder, profile):
    '''
    Extract the given module from the list of dumps within the folder given as argument
    WARNING: Assumed the dumps come from the same VM
    '''
    logfiles = []
    # iterate in each dump file in dumps_folder
    for dump_file in get_files(dumps_folder):
        logger.info(f'[+] Processing dump file \"{dump_file}\" ... ')
        _tmpdir = create_tmpdir() # create temporary directory for working
        _tmpfd, _tmpfile = tempfile.mkstemp(dir=_tmpdir)
        _stdout, _returncode = execute_vol_plugin('sum', dump_file, SUM_PLUGIN_DIR, profile, f'-r {mod_name} -D {_tmpdir} --log-memory-pages {_tmpfile}')

        if _stdout is None:
            logger.error('Execution of command "{0}" finished with return code {1}'.format(cmd, _returncode))
        else: # append to logfiles if it finished with success
            logfiles.append(_tmpfile)

    # return the list of logfiles
    return logfiles

def create_tmpdir():
    tmp = os.path.join(tempfile.gettempdir(), '.{}'.format(hash(os.times())))
    os.makedirs(tmp)
    return tmp

def get_files(folder):
    return glob.glob(os.path.join(folder, '*'))

def get_inorder_pagelist_AVL(files) -> (list, int, str):
    '''
    Create an AVL tree that represents the mix of the dumps
    '''
    sort_tree = AVLTree()
    #sort_tree = {}
    total_pages = -1
    md5_first_page = -1
    _filename = ''
    current_file_version = ''
    base_address = ''

    # iterate on files
    for f in files:
        logger.info(f"[+] Processing dump log file \"{f}\" ... ")
        lines = read_data(f)
        current_file_version = ''
        base_address = ''
        for line in lines:
            data = line.split(':')
            aux = data[0].split(',')
            filename = aux[1]
            # get file version
            file_version = aux[3]
            if current_file_version == '':
                current_file_version = file_version

            if _filename == '':
                _filename = filename.split('-')[-3]
     
            current_base_address = filename.split('-')[-1].split('.')[0]
            if base_address == '':
                base_address = filename.split('-')[-1].split('.')[0]

            # check if the first page is identical, otherwise give a warning 
            current_md5 = aux[2]
            if md5_first_page == -1:
                md5_first_page = current_md5
            elif md5_first_page != current_md5:
                logger.warning(f'MD5 mismatch in "{filename}" ({current_md5} found, it should be {md5_first_page})')
                if current_file_version != file_version:
                    logger.warning(f'Version of {_filename} DLL differs ({current_file_version} vs. {file_version}), adding DLL considering version ...')
                    filename += '-' + file_version
                elif base_address != current_base_address: # XXX occurs by WoW64
                    logger.warning(f'Module base address differs ({current_base_address} found, it should be {base_address}), skipping ... ')
                    continue

            # get total pages, and warn if different
            current_total = int(aux[4])
            if total_pages == -1: # XXX we consider the first total pages value as the reference value
                total_pages = current_total
            elif total_pages != current_total:
                logger.warning(f'Total number of memory pages mismatch in "{filename}" ({current_total} found, it should be {total_pages})')
        
            list_pages = data[1].split(',')
            # store in an auxiliary structure to sort by len(list_pages)
            sort_tree.insert(len(list_pages), (filename, list_pages), duplicated_keys=True)
    
    # then traverse the tree in reversed order
    in_order = sort_tree.in_order(False)
    in_order = in_order.split(';')[:-1]
    return reversed(in_order), total_pages, _filename

def get_inorder_pagelist(files) -> (list, int, str):
    '''
    Create a dictionary that represents the mix of the dumps
    '''
    #sort_tree = AVLTree()
    sort_dict = {}
    total_pages = -1
    md5_first_page = -1
    _filename = ''
    current_file_version = ''
    base_address = ''

    # iterate on files
    for f in files:
        logger.info(f"[+] Processing dump log file \"{f}\" ... ")
        lines = read_data(f)
        current_file_version = ''
        base_address = ''
        for line in lines:
            data = line.split(':')
            aux = data[0].split(',')
            filename = aux[1]
            # get file version
            file_version = aux[3]
            if current_file_version == '':
                current_file_version = file_version

            if _filename == '':
                _filename = filename.split('-')[-3]
     
            current_base_address = filename.split('-')[-1].split('.')[0]
            if base_address == '':
                base_address = filename.split('-')[-1].split('.')[0]

            # check if the first page is identical, otherwise give a warning 
            current_md5 = aux[2]
            if md5_first_page == -1:
                md5_first_page = current_md5
            elif md5_first_page != current_md5:
                logger.warning(f'MD5 mismatch in "{filename}" ({current_md5} found, it should be {md5_first_page})')
                if current_file_version != file_version:
                    logger.warning(f'Version of {_filename} DLL differs ({current_file_version} vs. {file_version}), adding DLL considering version ...')
                    filename += '-' + file_version
                elif base_address != current_base_address: # XXX occurs by WoW64
                    logger.warning(f'Module base address differs ({current_base_address} found, it should be {base_address}), skipping ... ')
                    continue

            # get total pages, and warn if different
            current_total = int(aux[4])
            if total_pages == -1: # XXX we consider the first total pages value as the reference value
                total_pages = current_total
            elif total_pages != current_total:
                logger.warning(f'Total number of memory pages mismatch in "{filename}" ({current_total} found, it should be {total_pages})')
        
            list_pages = data[1].split(',')
            # store in an auxiliary structure to sort by len(list_pages)
            #sort_tree.insert(len(list_pages), (filename, list_pages), duplicated_keys=True)
            aux_len = len(list_pages)
            if sort_dict.get(aux_len) is None:
                sort_dict[aux_len] = []
            sort_dict[aux_len].append((filename, list_pages))

    return sort_dict, total_pages, _filename

def process_new_item(data, mix_tree):
    filename = data[0]
    list_pages = data[1]
    logger.info('[*] Total nodes before processing "{0}": {1}'.format(filename, mix_tree.get_count()))
    logger.info('[*] Number of memory pages to process: {0}'.format(len(list_pages)))
    for n_page in list_pages:
        logger.debug("[+] Inserting {0} in the tree (file {1})".format(int(n_page), filename))
        mix_tree.insert(int(n_page), filename)
    _nodes_after = mix_tree.get_count()
    logger.info('[*] Total nodes after processing "{0}": {1}'.format(filename, _nodes_after))

def mix_dumps_results_AVL(files) -> (AVLTree, int):
    '''
    Create an AVL tree that represents the mix of the dumps
    '''
    mix_tree = AVLTree()

    _reversed_pages, _totalpages, _modulename = get_inorder_pagelist_AVL(files)
    # iterate on the list of memory pages in reversed order and get results of new nodes added in each step
    for itm in _reversed_pages:
        first_occurrence = itm.find('[') + 1
        itm = ast.literal_eval(itm[first_occurrence:-1])
                
        if type(itm) is tuple:
            process_new_item(itm, mix_tree)
        elif type(itm) is list:
            for aux in itm:
                process_new_item(aux, mix_tree)
    return mix_tree, _totalpages

def mix_dumps_results_retAVL(files) -> (AVLTree, int):
    '''
    Create an AVL tree that represents the mix of the dumps
    '''
    mix_tree = AVLTree()

    _mpages, _totalpages, _modulename = get_inorder_pagelist(files)
    # iterate on the list of memory pages in reversed order and get results of new nodes added in each step
    _nodes_after = 0
    for key in reversed(sorted(_mpages)):
        for f in _mpages[key]:
            process_new_item(f, mix_tree)

    return mix_tree, _totalpages

def mix_dumps_results(files) -> (dict, int):
    '''
    Create a dictionary that represents the mix of the dumps
    '''
    #mix_tree = AVLTree()
    mix_dict = {}

    _mpages, _totalpages, _modulename = get_inorder_pagelist(files)
    # iterate on the list of memory pages in reversed order and get results of new nodes added in each step
    _nodes_after = 0
    for key in reversed(sorted(_mpages)):
        for f in _mpages[key]:
            filename = f[0]
            list_pages = f[1]
            logger.info('[*] Total nodes before processing "{0}": {1}'.format(filename, _nodes_after)) # optimization
            logger.info('[*] Number of memory pages to process: {0}'.format(len(list_pages)))
            for n_page in list_pages:
                logger.debug("[+] Inserting {0} in the tree (file {1})".format(int(n_page), filename))
                #mix_tree.insert(int(n_page), filename)
                n_page = int(n_page)
                if mix_dict.get(n_page) is None:
                    mix_dict[n_page] = []
                    mix_dict[n_page].append(filename)
                # XXX here we could check whether the given page is equal or not, raising a warning to the user
                # to do it, we need SUM plugin to provide us with specific hash information (per memory page)
                # or to compute them here (costly)
            _nodes_after = len(mix_dict)
            logger.info('[*] Total nodes after processing "{0}": {1}'.format(filename, _nodes_after))
    
    return mix_dict, _totalpages


def fill_with_zeros(f, init, end):
    for zf in range(init, end):
        for i in range(1, PAGE_SIZE + 1):
            f.write(struct.pack('1B', 0))

def read_and_write_page(fo, filename, n_page):
    # open the input file and set the pointer to the given page
    logger.debug('[+] Opening file {0} to read page {1}'.format(filename, n_page))
    fi = open(filename, "rb")
    fi.seek(n_page*PAGE_SIZE) # remember: initial page is 0
    # once the pinter is set, read bytes and write them to output file
    _bytes = fi.read(PAGE_SIZE)
    fo.write(_bytes)
    logger.debug('[+] Read {0} bytes from file {1}, written to output file ...'.format(len(_bytes), filename))
    # close input file
    fi.close()

def generate_mixed_module_AVL(dump_folder, tree: AVLTree, out_name, t_pages: int):
    '''
    Create a mixed module, considering the info stored in the given AVL tree
    '''
    # create output file
    outfile = os.path.join(output_folder, out_name)
    fo = open(outfile, "wb")
    
    in_order = tree.in_order(False)
    logging.debug(f'[+] Content of the dict (in-order): {in_order}')
    in_order_list = in_order.split(';')[:-1]

    # iterate on the items, reading each file and writing the content to fo
    last_page = -1 # initial page is 0 
    for item in in_order_list:
        data = item.split('[')
        n_page = int(data[0])
        filename = data[1][:-1] # remove the ] at the end of the filename
        # fill missing pages with zeros, if needed
        if n_page - last_page != 1:
            logger.debug('[+] Filling with zeros from {0} to {1}'.format(last_page, n_page))
            fill_with_zeros(fo, last_page, n_page - 1)
        # now read a page from filename and write it to fo
        read_and_write_page(fo, filename, n_page)
        # update last_page appropriately for next iteration
        last_page = n_page

    # fill last pages, if needed
    if t_pages - last_page != 1:
        logger.debug('[+] Filling with zeros from {0} to {1}'.format(last_page, t_pages))
        fill_with_zeros(fo, last_page, t_pages - 1)

    logger.debug('[+] Closing mixed file {0}'.format(out_name))
    # close output file
    fo.close()
    return

def generate_mixed_module(dump_folder, _dict: dict, out_name, t_pages: int):
    '''
    Create a mixed module, considering the info stored in the given AVL tree
    '''
    # create output file
    outfile = os.path.join(output_folder, out_name)
    fo = open(outfile, "wb")
    
    last_page = -1 # initial page is 0 
    # iterate on the items, reading each file and writing the content to fo
    for n_page in sorted(_dict):
        filename = _dict[n_page][0]
        # fill missing pages with zeros, if needed
        #import pdb; pdb.set_trace()
        if n_page - last_page != 1:
            logger.debug('[+] Filling with zeros from {0} to {1}'.format(last_page, n_page))
            fill_with_zeros(fo, last_page, n_page - 1)
        # now read a page from filename and write it to fo
        read_and_write_page(fo, filename, n_page)
        # update last_page appropriately for next iteration
        last_page = n_page

    # fill last pages, if needed
    if t_pages - last_page != 1:
        logger.debug('[+] Filling with zeros from {0} to {1}'.format(last_page, t_pages))
        fill_with_zeros(fo, last_page, t_pages - 1)

    logger.debug('[+] Closing mixed file {0}'.format(out_name))
    # close output file
    fo.close()
    return

def create_wd():
    global output_folder
    output_folder = os.path.join(os.getcwd(), output_folder)
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.mkdir(output_folder)

def read_data(file):
    try:
        with open(file, 'r') as f:
            return f.read().splitlines()
    except:
        logger.error("[-] File {0} not found, exiting program ...".format(file))
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])

