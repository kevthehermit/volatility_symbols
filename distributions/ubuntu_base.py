import logging
import re
import requests

from parsers import debfiles

logger = logging.getLogger(__name__)


class UbuntuBase:
    def __init__(self, branch):
        self.operating_system = 'ubuntu'
        self.supported_base = ['linux', 'linux-aws', 'linux-azure', 'linux-gcp']
        self.kernel_pattern = '<a href="linux-modules-(.*?).deb">'
        self.debug_pattern = '<a href="linux-image-(.*?).deb">'
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

        logger.info(f'Fetching list of debug kernels from {self.kernel_url}')
        debug_list = requests.get(self.debug_url)
        debug_debs = re.findall(self.debug_pattern, debug_list.text)

        logger.info('Searching for Debian Packages')
        for match in kernel_debs:
            # Ignore some of the results to prevent duplicates
            if any(x in match for x in ['-dbg', 'extra-']):
                continue
            logger.debug(f'Found: {match}')

            # Find the matching debug symbols
            pattern = match.split('_', 1)[0]
            for item in debug_debs:
                if item.startswith(pattern):
                    debug_deb = f'{self.debug_url}linux-image-{item}ddeb'
                    break

            if kernel_filter == 'all' or match == kernel_filter:
                self.kernel_pairs[match] = {
                    "kernel_deb": f'{self.kernel_url}linux-modules-{match}.deb',
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
