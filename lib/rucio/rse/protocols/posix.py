# Copyright European Organization for Nuclear Research (CERN) since 2012
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import os.path
import shutil
from subprocess import call

from rucio.common import exception
from rucio.common.checksum import adler32
from rucio.rse.protocols import protocol


class Default(protocol.RSEProtocol):
    """ Implementing access to RSEs using the local filesystem."""

    def exists(self, pfn):
        """
            Checks if the requested file is known by the referred RSE.

            :param pfn: Physical file name

            :returns: True if the file exists, False if it doesn't

            :raises SourceNotFound: if the source file was not found on the referred storage.
        """
        status = ''
        try:
            status = os.path.exists(self.pfn2path(pfn))
        except Exception as e:
            raise exception.ServiceUnavailable(e)
        return status

    def connect(self):
        """
            Establishes the actual connection to the referred RSE.

            :param credentials: needed to establish a connection with the storage.

            :raises RSEAccessDenied: if no connection could be established.
        """
        pass

    def close(self):
        """ Closes the connection to RSE."""
        pass

    def get(self, pfn, dest, transfer_timeout=None):
        """ Provides access to files stored inside connected the RSE.

            :param pfn: Physical file name of requested file
            :param dest: Name and path of the files when stored at the client
            :param transfer_timeout Transfer timeout (in seconds) - dummy

            :raises DestinationNotAccessible: if the destination storage was not accessible.
            :raises ServiceUnavailable: if some generic error occurred in the library.
            :raises SourceNotFound: if the source file was not found on the referred storage.
         """
        try:
            shutil.copy(self.pfn2path(pfn), dest)
        except OSError as e:
            try:  # To check if the error happened local or remote
                with open(dest, 'wb'):
                    pass
                call(['rm', '-rf', dest])  # noqa: S607
            except OSError as e:
                if e.errno == 2:
                    raise exception.DestinationNotAccessible(e)
                else:
                    raise exception.ServiceUnavailable(e)
            if e.errno == 2:
                raise exception.SourceNotFound(e)
            else:
                raise exception.ServiceUnavailable(e)

    def put(self, source, target, source_dir=None, transfer_timeout=None):
        """
            Allows to store files inside the referred RSE.

            :param source: path to the source file on the client file system
            :param target: path to the destination file on the storage
            :param source_dir: Path where the to be transferred files are stored in the local file system
            :param transfer_timeout Transfer timeout (in seconds) - dummy

            :raises DestinationNotAccessible: if the destination storage was not accessible.
            :raises ServiceUnavailable: if some generic error occurred in the library.
            :raises SourceNotFound: if the source file was not found on the referred storage.
        """
        target = self.pfn2path(target)

        if source_dir:
            sf = source_dir + '/' + source
        else:
            sf = source
        try:
            dirs = os.path.dirname(target)
            if not os.path.exists(dirs):
                os.makedirs(dirs)
            shutil.copy(sf, target)
        except OSError as e:
            if e.errno == 2:
                raise exception.SourceNotFound(e)
            elif not self.exists(self.rse['prefix']):
                path = ''
                for p in self.rse['prefix'].split('/'):
                    path += p + '/'
                    os.mkdir(path)
                shutil.copy(sf, self.pfn2path(target))
            else:
                raise exception.DestinationNotAccessible(e)

    def delete(self, pfn):
        """ Deletes a file from the connected RSE.

            :param pfn: pfn to the to be deleted file

            :raises ServiceUnavailable: if some generic error occurred in the library.
            :raises SourceNotFound: if the source file was not found on the referred storage.
        """
        try:
            os.remove(self.pfn2path(pfn))
        except OSError as e:
            if e.errno == 2:
                raise exception.SourceNotFound(e)

    def rename(self, pfn, new_pfn):
        """ Allows to rename a file stored inside the connected RSE.

            :param path: path to the current file on the storage
            :param new_path: path to the new file on the storage

            :raises DestinationNotAccessible: if the destination storage was not accessible.
            :raises ServiceUnavailable: if some generic error occurred in the library.
            :raises SourceNotFound: if the source file was not found on the referred storage.
        """
        path = self.pfn2path(pfn)
        new_path = self.pfn2path(new_pfn)
        try:
            if not os.path.exists(os.path.dirname(new_path)):
                os.makedirs(os.path.dirname(new_path))
            os.rename(path, new_path)
        except OSError as e:
            if e.errno == 2:
                if self.exists(self.pfn2path(path)):
                    raise exception.SourceNotFound(e)
                else:
                    raise exception.DestinationNotAccessible(e)
            else:
                raise exception.ServiceUnavailable(e)

    def lfns2pfns(self, lfns):
        """ Returns fully qualified PFNs for the file referred by each lfn in
            the lfns list.

            :param lfns: List of lfns. If lfn['path'] is present it is used as
                   the path to the file, otherwise the path is constructed
                   deterministically.

            :returns: Fully qualified PFNs.
        """
        pfns = {}
        prefix = self.attributes['prefix']

        if not prefix.startswith('/'):
            prefix = ''.join(['/', prefix])
        if not prefix.endswith('/'):
            prefix = ''.join([prefix, '/'])

        lfns = [lfns] if isinstance(lfns, dict) else lfns
        for lfn in lfns:
            scope, name = str(lfn['scope']), lfn['name']
            if 'path' in lfn and lfn.get('path'):
                pfns['%s:%s' % (scope, name)] = ''.join([self.attributes['scheme'],
                                                         '://',
                                                         self.attributes['hostname'],
                                                         prefix,
                                                         lfn['path'] if not lfn['path'].startswith('/') else lfn['path'][1:]
                                                         ])
            else:
                pfns['%s:%s' % (scope, name)] = ''.join([self.attributes['scheme'],
                                                         '://',
                                                         self.attributes['hostname'],
                                                         prefix,
                                                         self._get_path(scope=scope, name=name)
                                                         ])
        return pfns

    def pfn2path(self, pfn):
        tmp = list(self.parse_pfns(pfn).values())[0]
        return '/'.join([tmp['prefix'], tmp['path'], tmp['name']])

    def stat(self, pfn):
        """ Determines the file size in bytes and checksum (adler32) of the provided file.

            :param pfn: The PFN the file.

            :returns: a dict containing the keys filesize and adler32.
        """
        path = self.pfn2path(pfn)
        return {'filesize': os.stat(path)[os.path.stat.ST_SIZE], 'adler32': adler32(path)}


class Symlink(Default):
    """ Implementing access to RSEs using the local filesystem, creating a symlink on a get """

    def get(self, pfn, dest, transfer_timeout=None):
        """ Provides access to files stored inside connected the RSE.
            A download/get will create a symlink on the local file system pointing to the
            underlying file. Other operations act directly on the remote file.
            :param pfn: Physical file name of requested file
            :param dest: Name and path of the files when stored at the client
            :param transfer_timeout Transfer timeout (in seconds) - dummy
            :raises DestinationNotAccessible: if the destination storage was not accessible.
            :raises ServiceUnavailable: if some generic error occurred in the library.
            :raises SourceNotFound: if the source file was not found on the referred storage.
         """
        path = self.pfn2path(pfn)
        os.symlink(path, dest)
        self.logger(logging.DEBUG,
                    'Symlink {} created for {} from {}'
                    .format(dest, path, pfn))
        if not os.lstat(dest):
            # problem in creating the symlink
            self.logger(logging.ERROR, 'Symlink {} could not be created'.format(dest))
            raise exception.DestinationNotAccessible()
        if not os.path.exists(dest):
            # could not find the file following the symlink
            self.logger(logging.ERROR, 'Symlink {} appears to be a broken link to {}'
                        .format(dest, path))
            if os.lstat(dest) and os.path.islink(dest):
                os.unlink(dest)
            raise exception.SourceNotFound()

    def pfn2path(self, pfn):
        # obtain path and sanitise from multiple slashes, etc
        path = os.path.normpath(super().pfn2path(pfn))
        self.logger(logging.DEBUG, 'Extracted path: {} from: {}'.format(path, pfn))
        return path
