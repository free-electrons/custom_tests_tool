import logging
import os
import urllib
import xmlrpc.client


class BaseError(Exception):
    pass


class UnavailableError(BaseError):
    pass


class Writer(object):

    def __init__(self, cfg):
        self._cfg = cfg

    def write(self, board, name, job):
        raise NotImplementedError('Missing write method')


class FileWriter(Writer):

    def write(self, board, name, job):
        try:
            os.makedirs(self._cfg['output_dir'])
        except:
            pass

        out = os.path.join(self._cfg['output_dir'], '%s.yaml' % name)
        try:
            f = open(out, 'w')
            f.write(job)
        except IOError:
            raise UnavailableError('Couldn\'t save our file')

        return [out]


class LavaWriter(Writer):

    def __init__(self, cfg):
        self._cfg = cfg

        try:
            u = urllib.parse.urlparse(self._cfg['server'])
            url = "%s://%s:%s@%s/RPC2" % (u.scheme,
                                          self._cfg['username'],
                                          self._cfg['token'],
                                          u.netloc)

            self._con = xmlrpc.client.ServerProxy(url)
        except xmlrpc.client.Error:
            raise UnavailableError('LAVA device is offline')

    def __get_device_status(self, device):
        board = "%s_01" % device

        return self._con.scheduler.get_device_status(board)

    def write(self, board, name, job):
        dev = self.__get_device_status(board['device_type'])
        if dev['status'] == "offline":
            logging.error("Device is offline, not sending the job")
            raise UnavailableError('LAVA device is offline')

        value = list()
        #
        # submit_job can return either an int (if there's one element)
        # or a list of them (if it's a multinode job).
        # This is crappy, but the least crappy way to handle this.
        #
        ret = self._con.scheduler.submit_job(job)
        try:
            for r in ret:
                value.append('%s/scheduler/job/%s' %
                             (self._cfg['web_ui_address'], r))
        except TypeError:
            value.append('%s/scheduler/job/%s' %
                         (self._cfg['web_ui_address'], ret))

        return value
