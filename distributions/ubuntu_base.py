import logging
import re
import requests

from parsers import debfiles

logger = logging.getLogger(__name__)


class UbuntuBase:
    def __init__(self, branch):
        self.operating_system = 'ubuntu'
        self.supported_base = ['linux', 'linux-aws', 'linux-azure', 'linux-gcp']
        self.kernel_pattern = '<a href="(linux-modules-(.*?).deb)">'
        self.debug_pattern = '<a href="(linux-image-(.*?).deb)">'
        self.kernel_pairs = {}
        
        if branch in self.supported_base:
            self.kernel_url = f'http://security.ubuntu.com/ubuntu/pool/main/l/{branch}/'
            self.debug_url = f'http://ddebs.ubuntu.com/ubuntu/pool/main/l/{branch}/'
        else:
            logger.error(f'Unsupported Target {branch}')
            exit()

    def get_kernel_list(self, kernel_filter):
        """Parses the `kernel_url` for any matching kernel deb files"""
        logger.info(f'Fetching list of kernels from {self.kernel_url}')
        kernel_list = requests.get(self.kernel_url)
        kernel_debs = re.findall(self.kernel_pattern, kernel_list.text)

        logger.info(f'Fetching list of debug kernels from {self.debug_url}')
        debug_list = requests.get(self.debug_url)
        debug_debs = re.findall(self.debug_pattern, debug_list.text)

        logger.info('Searching for Debian Packages')
        for match in kernel_debs:

            deb_path = match[0]
            kernel_string = match[1].split('-unsigned')[0]

            # Ignore some of the results to prevent duplicates
            if any(x in kernel_string for x in ['-dbg', 'extra-']):
                continue
            logger.debug(f'Found: {kernel_string}')

            # Find the matching debug 
            debug_deb = None
            pattern = kernel_string.split('_', 1)[0]

            for debug_path, debug_kernel in debug_debs:
                if debug_kernel.startswith(pattern) or debug_kernel.startswith(f'unsigned-{pattern}'):
                    debug_deb = f'{self.debug_url}{debug_path}'
                    break

            if debug_deb:
                if kernel_filter == 'all' or kernel_string == kernel_filter:
                    #print(debug_deb, f'{self.kernel_url}{deb_path}')
                    self.kernel_pairs[kernel_string] = {
                        "kernel_deb": f'{self.kernel_url}{deb_path}',
                        "debug_deb": debug_deb,
                        "valid": False,
                        "banner": '',
                        "isf_file": False
                        }
                else:
                    logger.debug('Ignored by filter')
            else:
                logger.warning(f'Unable to find matching debug deb for {kernel_string}')

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
