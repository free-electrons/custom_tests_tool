import logging
import os
import urllib
import xmlrpc.client
import time

class BaseError(Exception):
    pass


class UnavailableError(BaseError):
    pass


class Writer(object):
    """
    This class is responsible for saving the job somewhere. It must be
    subclassed to implement the `write` method.

    It take in its constructor a dictionary-like object to contain the needed
    informations to save the jobs. The actual mandatory keys depends on the
    implementation of the write method.
    """

    def __init__(self, cfg):
        self._cfg = cfg

    def write(self, board, name, job):
        """
        The write method takes the board structure (dict), a name (string), and
        the job (string) in argument.
        """
        raise NotImplementedError('Missing write method')


class FileWriter(Writer):
    """
    This class writes the job to the filesystem, in the directory given in the
    `output_dir` of the configuration attribute.
    """

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
    """
    This class saves the job by sending it to LAVA.
    It needs the following keys in its configuration:
        - `server`: the xmlrpc address of the LAVA API.
        - `username`: the LAVA username to use to send the job.
        - `token`: the LAVA token to get authorization in the API.
        - `web_ui_address`: a string containing the base URL of LAVA to display
          a nice link by appending the job ID once submitted.
    """

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
        elif dev['status'] == "retired":
            logging.error("Device is retired, not sending the job")
            raise UnavailableError('LAVA device is retired')

        value = list()
        #
        # submit_job can return either an int (if there's one element)
        # or a list of them (if it's a multinode job).
        # This is crappy, but the least crappy way to handle this.
        #
        ret = self._con.scheduler.submit_job(job)
        try:
            for r in ret:
                value.append(r)
        except TypeError:
            value.append(ret)

        return value

    def wait(self, job_id):
        while True:
            job_list = self._con.results.make_custom_query("testjob",
                                                           "testjob__id__exact__%s" % job_id)
            job = job_list[0]
            if job['status'] != 0 and job['status'] != 1:
                return job['status']
            time.sleep(30)
