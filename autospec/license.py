#!/bin/true
#
# license.py - part of autospec
# Copyright (C) 2015 Intel Corporation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Deduce the upstream version from the package content
# based on both license file pattern matching and
# exact matches on hashes of the COPYING file
#

import sys
import os
import re
import hashlib
import shlex
import tarball
import pycurl
import urllib.parse
import config
from io import BytesIO

from util import print_fatal, print_warning

default_license = "TO BE DETERMINED"

licenses = []
license_files = []


def add_license(lic):
    """
    Add license from license string lic after checking for duplication or
    presence in the blacklist. Returns False if no license were added, True
    otherwise.
    """
    global licenses
    global license_files
    lic = lic.strip().strip(',')
    result = False

    # Translate the license if a translation exists
    real_lic_str = config.license_translations.get(lic, lic)
    real_lics = real_lic_str.split()
    for real_lic in real_lics:
        if real_lic in licenses or real_lic in config.license_blacklist:
            continue
        else:
            result = True
            licenses.append(real_lic)

    return result


def license_from_copying_hash(copying, srcdir):
    """Add licenses based on the hash of the copying file"""
    data = tarball.get_contents(copying)
    if data.startswith(b'#!'):
        # Not a license if this is a script
        return

    sh = hashlib.sha1()
    sh.update(data)
    hash_sum = sh.hexdigest()

    if config.license_fetch:
        values = {'hash': hash_sum, 'text': data, 'package': tarball.name}
        data = urllib.parse.urlencode(values)
        data = data.encode('utf-8')

        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(c.URL, config.license_fetch)
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.POSTFIELDS, data)
        c.setopt(c.FOLLOWLOCATION, 1)
        try:
            c.perform()
        except Exception as excep:
            print_fatal("Failed to fetch license from {}: {}"
                        .format(config.license_fetch, excep))
            c.close()
            sys.exit(1)

        c.close()

        response = buffer.getvalue()
        page = response.decode('utf-8').strip()
        if page:
            print("License     : ", page, " (server) (", hash_sum, ")")
            add_license(page)
            if page != "none":
                lic_path = copying[len(srcdir) + 1:]
                license_files.append(shlex.quote(lic_path))

            return

    if hash_sum in config.license_hashes:
        add_license(config.license_hashes[hash_sum])
    else:
        if not config.license_show:
            return
        print_warning("Unknown license {0} with hash {1}".format(copying, hash_sum))
        hash_url = config.license_show % {'HASH': hash_sum}
        print_warning("Visit {0} to enter".format(hash_url))


def scan_for_licenses(srcdir):
    """
    Scan the project directory for things we can use to guess a description
    and summary
    """
    targets = ["copyright",
               "copyright.txt",
               "apache-2.0",
               "libcurllicense",
               "gpl.txt",
               "gplv2.txt",
               "notice",
               "copyrights",
               "about_bsd.txt"]
    # look for files that start with copying or licen[cs]e (but are
    # not likely scripts) or end with licen[cs]e
    target_pat = re.compile(r"^((copying)|(licen[cs]e))|(licen[cs]e)$")
    for dirpath, dirnames, files in os.walk(srcdir):
        for name in files:
            if name.lower() in targets or target_pat.search(name.lower()):
                license_from_copying_hash(os.path.join(dirpath, name), srcdir)

    if not licenses:
        print_fatal(" Cannot find any license or {}.license file!\n".format(tarball.name))
        sys.exit(1)

    print("Licenses    : ", " ".join(sorted(licenses)))


def load_specfile(specfile):
    global licenses
    global license_files
    specfile.licenses = licenses if licenses else [default_license]
    specfile.license_files = sorted(license_files)
