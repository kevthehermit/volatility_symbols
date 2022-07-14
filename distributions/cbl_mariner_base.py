import logging
import re
import gzip
import requests
from requests.api import request

from parsers import rpmfiles

logger = logging.getLogger(__name__)


class CBLMariner:
    def __init__(self, branch):
        self.operating_system = 'cbl-mariner'
        self.supported_base = ['linux']
        self.kernel_pattern = '<a href="(kernel-([0-9]+.*?).rpm)">'
        self.kernel_pairs = {}
        
        if branch in self.supported_base:
            self.base_url = 'https://packages.microsoft.com/yumrepos'
        else:
            logger.error(f'Unsupported Target {branch}')
            exit()


    def get_kernel_list(self, kernel_filter):
        """Parses the `kernel_url` for any matching kernel deb files"""
        logger.info(f'Fetching list of kernels from {self.base_url}')

        folders = ["prod", "preview"]
        for folder in folders:
            url = f'{self.base_url}/cbl-mariner-2.0-{folder}-base-x86_64'
            logger.debug(f'Checking {url}')
            page_data = requests.get(url)
            # If its 200 its the correct page
            if page_data.status_code == 200:
                # 5.15.48.1-2.cm2
                rpm_data = re.findall(self.kernel_pattern, page_data.text)
                for rpm, kernel in rpm_data:
                    if kernel_filter == 'all' or kernel == f'{kernel_filter}.x86_64':
                        # Generate Debug URL
                        debug_rpm = f"kernel-debuginfo-{kernel}.rpm"
                        debug_url = f'{self.base_url}/cbl-mariner-2.0-{folder}-base-debuginfo-x86_64'
                        self.kernel_pairs[kernel] = {
                            "kernel_rpm": f'{url}/{rpm}',
                            "debug_rpm": f'{debug_url}/{debug_rpm}',
                            "valid": False,
                            "banner": '',
                            "isf_file": False,
                            "kernel": kernel.replace(".x86_64", ""),
                        }
                    else:
                        logger.debug('Ignored by filter')

    def validate_links(self, kernel):
        """For each pair of RPM files make HEAD requests to confirm files are present"""
        logger.info('Validating remote files exist')
        valid = False
        rpm_files = self.kernel_pairs[kernel]

        kernel_head = requests.head(rpm_files['kernel_rpm']).status_code
        debug_head = requests.head(rpm_files['debug_rpm']).status_code

        if kernel_head == debug_head == 200:
            self.kernel_pairs[kernel]['valid'] = True
            valid = True
        else:
            logger.warning(f'{kernel} Kernel RPM returned {kernel_head}, Debug RPM Returned {debug_head}')
        
        return valid


    def extract_files(self, symbol_set):
        logger.info('Processing RPMS')
        kernel = symbol_set['kernel']
        system_map = rpmfiles.process_rpm(symbol_set['kernel_rpm'], 'System.map')
        vmlinux = rpmfiles.process_rpm(symbol_set['debug_rpm'], f'vmlinux-{kernel}')

        return system_map, vmlinux
