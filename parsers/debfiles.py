import logging
import requests
import tempfile
import tarfile
from io import BytesIO

import zstandard as zstd
from debian import debfile
from arpy import Archive


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
    try:
        deb = debfile.DebFile(fileobj = f)
        tar_files = deb.data.tgz().getmembers()
        compression_type = "tgz"
    except Exception as err:
        print(err)
        # Some debs now use zst compression which is not supported by debian
        compression_type = "zst"
        # Back to start of file
        f.seek(0)

        # Get the data archive from arpy
        dpkg_archive = Archive(fileobj=f)
        dpkg_archive.read_all_headers()
        data_archive = dpkg_archive.archived_files[b"data.tar.zst"]

        # Decompress with zstandard
        # We stream copy to another bytes IO to keep it all in memory
        dctx = zstd.ZstdDecompressor()
        uncompressed_tar = BytesIO()
        dctx.copy_stream(data_archive, uncompressed_tar)
        uncompressed_tar.seek(0)

        # This should be a tar file now. 
        tar_io = tarfile.open(fileobj=uncompressed_tar)
        tar_files = tar_io.getmembers()

    logger.debug('Searching deb for file')
    # ToDo, dont iterate just read the file from the right location
    for member in tar_files:
        if file_pattern in member.name:
            logger.debug(f"Extracting {member.name}")
            if compression_type == 'tgz':
                extracted = deb.data.get_file(member.name)
            else:
                extracted = tar_io.extractfile(member.name)
            break
    if not extracted:
        return None

    prefix = 'vmlinux' if 'vmlinux' in member.name else 'System.map'

    with tempfile.NamedTemporaryFile(delete = False,
                                         prefix = prefix) as outfile:
    
        logger.debug(f'Writing {member.name} to {outfile.name}')
        outfile.write(extracted.read())

    # Close file handles
    f.close()
    uncompressed_tar.close()

    return outfile.name