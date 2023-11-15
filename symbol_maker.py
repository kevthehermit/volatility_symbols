import argparse
import json
import logging
import lzma
import os
import subprocess


from base64 import b64decode
from pathlib import Path

from distributions.ubuntu_base import UbuntuBase
from distributions.debian_base import DebianBase
from distributions.fedora_base import FedoraBase
from distributions.amazon_base import AmazonBase
from distributions.cbl_mariner_base import CBLMariner


def create_isf(system_map, vmlinux, kernel, output_path):
    """Given a System.map and vmlinux file create the ISF and write to output path compressed"""

    banner_path = output_path / 'banner.txt'
    isf_path = output_path / f'{kernel}.json.xz'

    root = Path(__file__).resolve().parent
    if os.name == 'nt':
        dwarf2json = Path(root, "dwarf2json.exe")
    else:
        dwarf2json = Path(root, "dwarf2json")

    dwarf_args = [dwarf2json, 'linux', '--system-map', system_map, '--elf', vmlinux]
    logger.debug(dwarf_args)
    logger.info(f'Creating ISF {isf_path}')
    proc = subprocess.run(dwarf_args, capture_output = True)

    logger.info('Reading Banner')
    try:
        json_data = json.loads(proc.stdout)
        banner_encoded = json_data['symbols']['linux_banner']['constant_data']
        banner_decoded = b64decode(banner_encoded).rstrip(b'\n\x00')

        banner_path.write_text(banner_decoded.decode())
        logger.debug(f'Found banner: {banner_decoded}')

    except Exception as err:
        logger.error(f'Could not process banner: {err}')

    logger.debug('Writing compressed isf file')

    with lzma.open(isf_path, 'w') as f:
        f.write(proc.stdout)

    logger.info(f'ISF created at {isf_path}')


def main(target_distro, kernel_filter, branch):

    if target_distro == 'ubuntu':
        distro = UbuntuBase(branch)
    elif target_distro == 'debian':
        distro = DebianBase(branch)
    elif target_distro == 'fedora':
        distro = FedoraBase(branch)
    elif target_distro == 'amazon':
        distro = AmazonBase(branch)
    elif target_distro == "cbl-mariner":
        distro = CBLMariner(branch)

    distro.get_kernel_list(kernel_filter)

    logger.info(f'Found {len(distro.kernel_pairs)} symbol sets')

    for kernel, symbol_set in distro.kernel_pairs.items():
        system_map = None
        vmlinux = None
        output_path = Path('symbol_files', distro.operating_system, kernel)
        isf_path = output_path / f'{kernel}.json.xz'
        if isf_path.exists():
            logger.warning(f'ISF already exists at {isf_path}')
            continue
        else:
            isf_path.parent.mkdir(parents=True, exist_ok=True)    

        valid = distro.validate_links(kernel)
        if valid:
            logger.info(f'Processing Files for {kernel}')

            try:
                system_map, vmlinux = distro.extract_files(symbol_set, kernel)
            except Exception as err:
                logger.error(f'Could not extract files: {err}')

        if system_map and vmlinux:
            try:
                create_isf(system_map, vmlinux, kernel, output_path)
            except Exception as err:
                logger.error(f'Could not create ISF File: {err}')

            logger.info("Cleanup Temp Files")
            os.remove(system_map)
            os.remove(vmlinux)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = "Generate a volatilty symbol file for a given distro and kernel version")
    parser.add_argument("-d",
                        "--distro",
                        dest = 'distro',
                        help = "Target Distribution",
                        choices = ['ubuntu', 'debian', 'fedora', 'amazon', 'cbl-mariner'],
                        required = True)
                        
    parser.add_argument("-k",
                        "--kernel",
                        dest = 'kernel',
                        help = "Target Kernel release or 'all'\n The output of `uname -r`",
                        required = True)

    parser.add_argument("-b",
                        "--branch",
                        dest = 'branch',
                        default='linux',
                        help = "Target Kernel branch e.g. linux-aws",
                        required = False)

    parser.add_argument("-v",
                        "--verbose",
                        dest = 'verbose',
                        action='store_true',
                        help = "Verbose Debug logging",
                        required = False)

    parser.set_defaults(verbose=False)
    args = parser.parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level)
    logger = logging.getLogger(__name__)
    logger.info('Started')

    main(args.distro, args.kernel, args.branch)
