import logging
import re
import gzip
import requests
from requests.api import request

from parsers import rpmfiles

logger = logging.getLogger(__name__)


class AmazonBase:
    def __init__(self, branch):
        self.operating_system = 'amazonlinux'
        self.supported_base = ['2']
        self.kernel_pattern = b'(/blobstore/.*?/kernel-([0-9].*?).rpm)'
        self.debug_pattern = b'(/blobstore/.*?/kernel-debuginfo-([0-9].*?).rpm)'
        self.kernel_pairs = {}
        
        if branch in self.supported_base:
            self.base_url = 'http://amazonlinux.us-east-1.amazonaws.com'
            self.kernel_url = 'http://amazonlinux.us-east-1.amazonaws.com/2/core/latest/x86_64/mirror.list'
            self.debug_url = 'http://amazonlinux.us-east-1.amazonaws.com/2/core/latest/debuginfo/x86_64/mirror.list'
        else:
            logger.error(f'Unsupported Target {branch}')
            exit()


    def get_kernel_list(self, kernel_filter):
        """Parses the `kernel_url` for any matching kernel deb files"""
        logger.info(f'Fetching list of kernels from {self.kernel_url}')

        # We need to read the mirror address from the mirror.list
        kernel_mirror = requests.get(self.kernel_url).text.rstrip('\n')

        # Then Read the XML and uncompress it
        kernel_xml_path = f'{kernel_mirror}/repodata/primary.xml.gz'
        kernel_xml = requests.get(kernel_xml_path)
        kernel_xml_data = gzip.decompress(kernel_xml.content)

        # Now search for matching kernels
        kernel_list = re.findall(self.kernel_pattern, kernel_xml_data)

        # Repeat all the steps for debugs, we need to blobstore path
        logger.info(f'Fetching list of debug kernels from {self.debug_url}')
        debug_mirror = requests.get(self.debug_url).text.rstrip('\n')
        debug_xml_path = f'{debug_mirror}/repodata/primary.xml.gz'
        debug_xml = requests.get(debug_xml_path)
        debug_xml_data = gzip.decompress(debug_xml.content)

        debug_list = re.findall(self.debug_pattern, debug_xml_data)

        for match in kernel_list:
            kernel_rpm = match[0].decode()
            kernel_string = match[1].decode()

            for debug_match in debug_list:
                if kernel_string == debug_match[1].decode():
                    debug_rpm = debug_match[0].decode()
                    break

            if kernel_filter == 'all' or kernel_string == kernel_filter:
                self.kernel_pairs[kernel_string] = {
                    "kernel_rpm": f'{self.base_url}{kernel_rpm}',
                    "debug_rpm": f'{self.base_url}{debug_rpm}',
                    "valid": False,
                    "banner": '',
                    "isf_file": False
                    }
            else:
                logger.debug('Ignored by filter')



    def validate_links(self, kernel):
        """For each pair of RPM files make HEAD requests to confirm files are present"""
        logger.info('Validating remote files exist')
        valid = False
        rpm_files = self.kernel_pairs[kernel]

        deb_head = requests.head(rpm_files['kernel_rpm']).status_code
        debug_head = requests.head(rpm_files['debug_rpm']).status_code

        if deb_head == debug_head == 200:
            self.kernel_pairs[kernel]['valid'] = True
            valid = True
        else:
            logger.warning(f'{kernel} Kernel Deb returned {deb_head}, Debug Deb Returned {debug_head}')
        
        return valid


    def extract_files(self, symbol_set):
        logger.info('Processing RPMS')
        system_map = rpmfiles.process_rpm(symbol_set['kernel_rpm'], 'System.map')
        vmlinux = rpmfiles.process_rpm(symbol_set['debug_rpm'], 'vmlinux')

        return system_map, vmlinux
