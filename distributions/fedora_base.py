import logging
import re
import requests

from parsers import rpmfiles

logger = logging.getLogger(__name__)


class FedoraBase:
    def __init__(self, branch):
        self.operating_system = 'fedora'
        self.supported_base = ['linux']
        self.debug_pattern = '<a href="(kernel-debuginfo-(.*?).rpm)">'
        self.kernel_pairs = {}
        
        if branch in self.supported_base:
            self.base_url = 'http://ftp.pbone.net/mirror/download.fedora.redhat.com/pub/fedora/linux/releases/'
            self.kernel_url = 'http://ftp.us.debian.org/debian/pool/main/l/linux/'
            self.debug_url = 'http://ftp.pbone.net/mirror/download.fedora.redhat.com/pub/fedora/linux/releases/'
        else:
            logger.error(f'Unsupported Target {branch}')
            exit()


    def get_kernel_list(self, kernel_filter):
        """Parses the `kernel_url` for any matching kernel deb files"""
        logger.info(f'Fetching list of kernels from {self.base_url}')

        search_urls = [
            'https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/',
            'https://archives.fedoraproject.org/pub/archive/fedora/linux/updates/',
            'http://ftp.pbone.net/mirror/download.fedora.redhat.com/pub/fedora/linux/releases/',
            'http://ftp.pbone.net/mirror/download.fedora.redhat.com/pub/fedora/linux/updates/'

        ]

        # Check each Search Page for a list of releases
        for base_url in search_urls:

            pattern = '<a href=.*>([0-9]{1,2}/)</a>'

            page_text = requests.get(base_url).text
            pages_list = re.findall(pattern, page_text)
            logger.info(f"Found {len(pages_list)} releases for {base_url}")

            # For each Release
            for release in pages_list:
                # Dir strucutre changes in 25
                if int(release[:-1]) < 25:
                    sub_path = 'debug/'
                elif 'linux/releases/' in base_url:
                    sub_path = 'debug/tree/Packages/k/'
                else:
                    sub_path = 'debug/Packages/k/'

                
                # There are 2 variations of path depending on version
                # # Check them both    
                for debug_page in [
                        f'{base_url}{release}Everything/x86_64/{sub_path}',
                        f'{base_url}{release}x86_64/{sub_path}']:
                    logger.debug(f'Checking {debug_page}')
                    page_data = requests.get(debug_page)

                    # If its 200 its the correct page
                    if page_data.status_code == 200:
                        rpm_data = re.findall(self.debug_pattern, page_data.text)
                        for rpm_name, kernel_name in rpm_data:
                            if 'common' in kernel_name:
                                continue
                            logger.debug(f'Found {kernel_name} on {debug_page}')
                            debug_rpm = f'{debug_page}{rpm_name}'

                            # Remove the debug name
                            kernel_rpm = debug_rpm.replace('-debuginfo-', '-core-')

                            # get the new path
                            if '/tree/Packages/' in debug_rpm:
                                kernel_rpm = kernel_rpm.replace('/debug/tree/Packages/', '/os/Packages/')
                            elif 'Everything/' in debug_rpm:
                                kernel_rpm = kernel_rpm.replace('/debug/', '/os/Packages/')
                            else:
                                kernel_rpm = kernel_rpm.replace('/debug/', '/')

                            # I hate the lack of consistency!
                            kernel_rpm.replace('/Packages/Packages/', '/Packages/')

                            if kernel_filter == 'all' or kernel_name == kernel_filter:
                                # Add to data set
                                self.kernel_pairs[kernel_name] = {
                                    "debug_rpm": debug_rpm,
                                    "kernel_rpm": kernel_rpm,
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


#http://ftp.pbone.net/mirror/download.fedora.redhat.com/pub/fedora/linux/releases/32/Everything/x86_64/debug/tree/Packages/k/kernel-debuginfo-5.6.6-300.fc32.x86_64.rpm
#http://ftp.pbone.net/mirror/download.fedora.redhat.com/pub/fedora/linux/releases/32/Everything/x86_64/os/Packages/k/kernel-5.6.6-300.fc32.x86_64.rpm


#https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/11/Everything/x86_64/kernel-2.6.29.4-167.fc11.x86_64.rpm
#https://archives.fedoraproject.org/pub/archive/fedora/linux/releases/11/Everything/x86_64/debug/kernel-debuginfo-2.6.29.4-167.fc11.x86_64.rpm
#