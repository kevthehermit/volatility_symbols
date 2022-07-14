# volatility_symbols

This tool can be used to generate an ISF file for Volatitlity3. 

*__WARNING__* - This tool will download 700MB - 1Gb of data per kernel in order to generate a given symbol set. The resulting ISF file is compressed to approx 3Mb.

You can also check the https://isf-server.techanarchy.net to search / download a precompiled ISF File. 

### Overview

First you need to identify the distribution and kernel version you want to download. You can get the kernel version by running `uname -r`

If you are targetting a non default kernel, like AWS or Azure you will also need to include the branch name. See the examples below for more detail.

### Usage

```
usage: symbol_maker.py [-h] -d {ubuntu,debian,fedora,amazon,cbl-mariner} -k KERNEL [-b BRANCH] [-v]

Generate a volatilty symbol file for a given distro and kernel version

options:
  -h, --help            show this help message and exit
  -d {ubuntu,debian,fedora,amazon,cbl-mariner}, --distro {ubuntu,debian,fedora,amazon,cbl-mariner}
                        Target Distribution
  -k KERNEL, --kernel KERNEL
                        Target Kernel release or 'all' The output of `uname -r`
  -b BRANCH, --branch BRANCH
                        Target Kernel branch e.g. linux-aws
  -v, --verbose         Verbose Debug logging
```


### Examples

To generate a symbol file for `Debian` `4.9.0-13-amd64` use the following command

`python3 symbol_maker.py -d debian -k '4.9.0-13-amd64'`

To generate a symbol file for `Ubuntu` `5.11.0-43-generic` use the following command 

`python3 symbol_maker.py -d ubuntu -k '5.11.0-43-generic' `

To generate a symbol file for `AWS` `Ubuntu` `4.15.0-1048-aws` use the following command

`python3 symbol_maker.py -d ubuntu -b 'linux-aws' -k '4.15.0-1048-aws'`



5.15.48.1-2.cm2