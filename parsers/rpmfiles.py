import logging
import requests
import rpmfile
import tempfile

from io import BytesIO

logger = logging.getLogger(__name__)

def process_rpm(rpm_url, file_pattern):
    """Takes a URL to an rmp file retrieves it and extracts the required file
    file, if found, is saved to a tempdir"""
    logger.debug(f'Fetching RPM File: {rpm_url}')

    # We do this in memory to save DiskIO    
    f = BytesIO()

    with requests.get(rpm_url, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192): 
            # If you have chunk encoded response uncomment if
            # and set chunk_size parameter to None.
            #if chunk: 
            f.write(chunk)

    # Go to start of file.
    f.seek(0)


    rpm = rpmfile.RPMFile(fileobj = f)
    member = None
    extracted = None
    for member in rpm.getmembers():
        if file_pattern in member.name:
            logger.debug(f"Extracting {member.name}")
            extracted = rpm.extractfile(member)
            break
    if not extracted:
        return None

    prefix = 'vmlinux' if 'vmlinux' in member.name else 'System.map'

    with tempfile.NamedTemporaryFile(delete = False,
                                         prefix = prefix) as outfile:
    
        logger.debug(f'Writing {member.name} to {outfile.name}')
        outfile.write(extracted.read())

    return outfile.name
