import logging
import re
import requests

from parsers import debfiles

logger = logging.getLogger(__name__)


class DebianBase:
    def __init__(self, branch):
        self.operating_system = 'debian'
        self.supported_base = ['linux', 'linux-aws', 'linux-azure', 'linux-gcp']
        self.search_pattern = '<a href="(linux-image-(.*?)_.*deb)">'
        self.kernel_pairs = {}
        
        if branch in self.supported_base:
            self.kernel_url = 'http://ftp.us.debian.org/debian/pool/main/l/linux/'
        else:
            logger.error(f'Unsupported Target {branch}')
            exit()

    def get_kernel_list(self, kernel_filter):
        """Parses the `kernel_url` for any matching kernel deb files"""
        logger.info(f'Fetching list of kernels from {self.kernel_url}')
        kernel_list = requests.get(self.kernel_url)
        kernel_debs = re.findall(self.search_pattern, kernel_list.text)


        logger.info('Searching for Debian Packages')
        for match in kernel_debs:

            deb_path = match[0]
            kernel_string = match[1].split('-unsigned')[0]

            # Ignore some of the results to prevent duplicates
            if any(x in kernel_string for x in ['-dbg']):
                continue
            logger.debug(f'Found: {kernel_string}')

            # Find the matching debug symbols
            for debug in kernel_debs:
                if f'linux-image-{kernel_string}-dbg' in debug[0]:
                    debug_deb = f'{self.kernel_url}{debug[0]}'
                    break

            if kernel_filter == 'all' or match == kernel_filter:
                self.kernel_pairs[kernel_string] = {
                    "kernel_deb": f'{self.kernel_url}{deb_path}',
                    "debug_deb": debug_deb,
                    "valid": False,
                    "banner": '',
                    "isf_file": False
                    }
            else:
                logger.debug('Ignored by filter')


    def validate_links(self, kernel):
        """For each pair of deb files make HEAD requests to confirm files are present"""
        logger.info('Validating remote files exist')
        valid = False
        deb_files = self.kernel_pairs[kernel]

        deb_head = requests.head(deb_files['kernel_deb']).status_code
        debug_head = requests.head(deb_files['debug_deb']).status_code

        if deb_head == debug_head == 200:
            self.kernel_pairs[kernel]['valid'] = True
            valid = True
        else:
            logger.warning(f'{kernel} Kernel Deb returned {deb_head}, Debug Deb Returned {debug_head}')
        
        return valid


    def extract_files(self, symbol_set):
        logger.info('Processing Debs')
        system_map = debfiles.process_deb(symbol_set['kernel_deb'], 'System.map')
        vmlinux = debfiles.process_deb(symbol_set['debug_deb'], 'boot/vmlinux')

        return system_map, vmlinux
