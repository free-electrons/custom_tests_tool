import os
import logging
import json

from jinja2 import FileSystemLoader, Environment


from src.crawlers import FreeElectronsCrawler, KernelCICrawler
from src.crawlers import RemoteAccessError
from src.writers import FileWriter, LavaWriter, UnavailableError


class JobCrafter(object):
    """
    This class handle the jobs.
    """
    __TEMPLATE_FOLDER = "jobs_templates"

    def __init__(self, boards, cfg):
        """
        `boards`: dict
            This is the dictionary structure found in the boards.json file.
        `cfg`: dict
            A configuration dict containing at least the following keys:
                - no_send
            If you need to upload custom files for the tests, the following keys
            must be provided:
                - ssh_server
                - ssh_username
            The following keys are also supported, through not mandatory:
                - notify
                - lava_server (for LAVA v1 templates)
                - lava_stream (for LAVA v1 templates)

        TODO: make some check at init time
        """
        self._boards = boards
        self._cfg = cfg
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests.json")) as f:
            self._tests = json.load(f)
        self.job = {
                "timeout": 0,
                "kernel": "",
                "device_tree": "",
                "rootfs": "",
                "rootfs_type": "",
                "modules": "",
                "test": "",
                "lava_server": "",
                "lava_stream": "",
                "device_type": "",
                "job_name": "",
                "notify": [],
                }
        self.jinja_env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
        if self._cfg['no_send']:
            self.writer = FileWriter(self._cfg)
        else:
            self.writer = LavaWriter(self._cfg)

# Template handling
    def get_template_from_file(self, file):
        logging.debug("    Template: %s" % file)
        self.job_template = self.jinja_env.get_template(file)

# Job handling
    def make_jobs(self, board_name, artifacts, test, job_name="default_job_name"):
        """
        The main method building up the jobs.

        `board_name`: string
            The name of the board to build the job for. Must correspond to one
            the keys in boards.json
        `artifacts`: dict
            A dictionary containing the URL to the artifacts, with the following
            keys:
                - kernel
                - dtb
                - rootfs
                - modules (optional)
        `test`: string
            The name of the test to build the job for. Must correspond to one of
            the keys in tests.json
        `job_name`: string
            A name to give to the job.
        """
        # Verify that the test exists
        if test not in self._tests.keys():
            logging.warning("  Test %s does not exists" % test)
            return

        # Get easier access to board config
        board_config = self._boards[board_name]

        if 'server' in self._cfg:
            self.job["lava_server"] = self._cfg['server']

        if 'stream' in self._cfg:
            self.job["lava_stream"] = self._cfg['stream']

        if 'notify' in self._cfg:
            self.job["notify"] = self._cfg['notify']

        logging.info("    Notifications recipients: %s" % ", ".join(self.job['notify']))

        # rootfs type
        if board_config["test_plan"] == "boot":
            self.job["rootfs_type"] = "ramdisk"
        elif board_config["test_plan"] == "boot-nfs":
            self.job["rootfs_type"] = "nfsrootfs"
        else:
            raise Exception(red("Invalid test_plan for board %s" %
                    board_config["name"]))

        self.job["device_type"] = board_config['device_type']

        self.job['rootfs'] = artifacts['rootfs']
        logging.info("    Root filesystem path: %s" % self.job['rootfs'])

        self.job['kernel'] = artifacts['kernel']
        logging.info("    Kernel path: %s" % self.job['kernel'])

        self.job['device_tree'] = artifacts['dtb']
        logging.info("    Device tree path: %s" % self.job['device_tree'])

        # modules are optional if we have our own kernel
        if 'modules' in artifacts:
            self.job['modules'] = artifacts['modules']
            logging.info('    Modules archive path: %s' % self.job['modules'])

        self.get_template_from_file(os.path.join(JobCrafter.__TEMPLATE_FOLDER,
            self._tests[test]['template']))

        if 'timeout' in self._cfg: # Give priority to the command line
            self.job["timeout"] = self._cfg['timeout']
        else:
            self.job["timeout"] = self._tests[test]['timeout']

        self.job["test"] = test

        self.job["job_name"] = "%s--%s" % (
                job_name,
                test
                )
        logging.debug("    Job name: %s" % self.job['job_name'])

        try:
            jobs = self.writer.write(board_config, job_name,
                                     self.job_template.render(self.job))
            for j in jobs:
                logging.info("  ==> Job saved to: '%s/scheduler/job/%s'" %
                             (self._cfg['web_ui_address'], j))

        except UnavailableError as e:
            logging.warning("  ==> Unable to send job: %s" % e)
            jobs = None

        return jobs

    def wait_jobs(self, jobs):
        statuses = dict()
        for j in jobs:
            statuses[j] = self.writer.wait(j)
        return statuses
