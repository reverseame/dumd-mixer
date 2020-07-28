#!/usr/bin/python3

import os
import sys
import shutil
import logging
import struct
import configparser
import getopt
import glob
import subprocess

from avl import AVLTree

default_log_level = logging.INFO
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

    print(f'[>] Ready to parse dumps in "{dumps_folder}" to extract {module_name} module')
    
    # First phase: extraction of content from dumps
    print("[*] Starting extraction phase ... ", end='')
    files = extract_module_from_dumps(dumps_folder, module_name, output_folder, profile)
    print("done!")
    # Second phase: mixing of extracted modules
    print("[*] Starting mixing phase ... ", end='')
    mix_tree, total_pages = mix_dumps_results(files)
    print('done!')
    # Third phase: generation of mixed file
    print("[*] Starting generation of mixed module phase ... ", end='')
    if output_filename == '':
        output_filename = module_name + '.mixed'
    generate_mixed_module(output_folder, mix_tree, output_filename, total_pages)
    print('done!')

    print("[>] Module {0} extracted successfully to {1} ({2} out of {3} memory pages retrieved)".format(module_name, os.path.join(output_folder, output_filename), mix_tree.get_count(), total_pages))

def load_cfg_file(config_file='config.ini'):
    global VOL_BIN 
    global SUM_PLUGIN_DIR
    global PYTHON2_BIN

    config = configparser.ConfigParser()
    config.read(config_file)
    VOL_BIN = output_name = config['DEFAULT']['VOL_BIN']
    SUM_PLUGIN_DIR = output_name = config['DEFAULT']['SUM_PLUGIN_DIR']
    PYTHON2_BIN = config['DEFAULT']['PYTHON2_BIN']

def extract_module_from_dumps(dumps_folder, mod_name, out_folder, profile):
    '''
    Extract the given module from the list of dumps within the folder given as argument
    '''
    logfiles = []
    # iterate in each dump file in dumps_folder
    for dump_file in get_files(dumps_folder):
        # execute SUM plugin with this dump file, and store log results
        logname = os.path.join(output_folder, os.path.basename(dump_file) + ".log")
        # first build the command 
        cmd = '{0} {1} --plugins={2}'.format(PYTHON2_BIN, VOL_BIN, SUM_PLUGIN_DIR)
        if profile != '': # append profile, if given as argument
            cmd += ' --profile={0}'.format(profile)
        if ' ' in dump_file:
            logger.warning('Please avoid white spaces in filenames, as in "{0}"'.format(dump_file))
        # XXX Volatility not recognizes the input file when putting "{0}" ?
        cmd += ' -f {0} -r {1} -D {2} --log-memory-pages {3} sum'.format(dump_file, mod_name, output_folder, logname)
        logger.debug('[+] Ready to execute cmd: ' + cmd)
        _completed_process = subprocess.run(cmd.split(' '), capture_output=True)
        logger.debug('[+] Execution finished! Output: ' + _completed_process.stdout.decode('utf-8'))
        # check error code
        if _completed_process.returncode != 0:
            logger.error('Execution of command "{0}" finished with return code {1}'.format(cmd, _completed_process.returncode))
        else: # append to logfiles if it finished with success
            logfiles.append(logname)

    # return the list of logfiles
    return logfiles

def get_files(folder):
    return glob.glob(os.path.join(folder, '*'))

def mix_dumps_results(files) -> (AVLTree, int):
    '''
    Create an AVL tree that represents the mix of the dumps
    '''
    mix_tree = AVLTree()
    total_pages = -1
    md5_first_page = -1
    # iterate on files
    for f in files:
        lines = read_data(f)
        for line in lines:
            data = line.split(':')
            aux = data[0].split(',')
            filename = aux[1]
            # check if the first page is identical, otherwise give a warning 
            current_md5 = aux[2]
            if md5_first_page == -1:
                md5_first_page = current_md5
            elif md5_first_page != current_md5:
                logger.warning(f'MD5 mismatch in "{filename}" ({current_md5} found, it should be {md5_first_page})')

            # get total pages, and warn if different
            current_total = int(aux[3])
            if total_pages == -1: # XXX we consider the first total pages value as the reference value
                total_pages = current_total
            elif total_pages != current_total:
                logger.warning(f'Total number of memory pages mismatch in "{filename}" ({current_total} found, it should be {total_pages})')

            list_pages = data[1].split(',')
            logger.info('[*] Total nodes before processing "{0}": {1}'.format(filename, mix_tree.get_count()))
            logger.info('[*] Number of memory pages to process: {0}'.format(len(list_pages)))
            for n_page in list_pages:
                logger.debug("[+] Inserting {0} in the tree (file {1})".format(n_page, f))
                mix_tree.insert(int(n_page), filename)
            logger.info('[*] Total nodes after processing "{0}": {1}'.format(filename, mix_tree.get_count()))

    return mix_tree, total_pages

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

def generate_mixed_module(dump_folder, tree: AVLTree, out_name, t_pages: int):
    '''
    Create a mixed module, considering the info stored in the given AVL tree
    '''
    in_order = tree.in_order(False)
    logging.debug(f'[+] Content of the AVL tree (in-order): {in_order}')
    in_order_list = in_order.split(';')[:-1]
    # create output file
    outfile = os.path.join(output_folder, out_name)
    fo = open(outfile, "wb")
    # iterate on the items, reading each file and writing the content to fo
    last_page = -1 # initial page is 0 
    for item in in_order_list:
        data = item.split('[')
        n_page = int(data[0])
        filename = data[1][:-1] # remove the ] at the end of the filename
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

