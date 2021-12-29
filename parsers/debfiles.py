import logging
import requests
import tempfile

from debian import debfile
from io import BytesIO

logger = logging.getLogger(__name__)

def process_deb(deb_url, file_pattern):
    """Takes a URL to a deb file retrieves it and extracts the required file
    file, if found, is saved to a dir with `kernel_name`"""
    logger.debug(f'Fetching Deb File: {deb_url}')

    # We do this in memory to save DiskIO    
    f = BytesIO()

    with requests.get(deb_url, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192): 
            # If you have chunk encoded response uncomment if
            # and set chunk_size parameter to None.
            #if chunk: 
            f.write(chunk)

    # Go to start of file.
    f.seek(0)

    logger.debug('Creating Deb Object')
    deb = debfile.DebFile(fileobj = f)

    logger.debug('Searching deb for file')
    # ToDo, dont iterate just read the file from the right location
    for member in deb.data.tgz().getmembers():
        if file_pattern in member.name:
            logger.debug(f"Extracting {member.name}")
            extracted = deb.data.get_file(member.name)
            break
    if not extracted:
        return None

    prefix = 'vmlinux' if 'vmlinux' in member.name else 'System.map'

    with tempfile.NamedTemporaryFile(delete = False,
                                         prefix = prefix) as outfile:
    
        logger.debug(f'Writing {member.name} to {outfile.name}')
        outfile.write(extracted.read())

    return outfile.name