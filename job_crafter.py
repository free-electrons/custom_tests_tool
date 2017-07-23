import os
import collections
import utils
import paramiko
import getpass
import logging

from boards import boards
from src.crawlers import FreeElectronsCrawler, KernelCICrawler
from src.crawlers import RemoteAccessError
from jinja2 import FileSystemLoader, Environment

REMOTE_ROOT = os.path.join("/tmp/ctt/", getpass.getuser())
TEMPLATE_FOLDER = "jobs_templates"
DEFAULT_TEMPLATE = "generic_simple_job.jinja"

class JobCrafter:
    """
    This class handle the jobs.
    """
    def __init__(self, board, cfg):
        self.board = boards[board]
        self.cfg = cfg
        self.crawlers = [KernelCICrawler(cfg), FreeElectronsCrawler(cfg)]
        self.job = {
                "kernel": "",
                "device_tree": "",
                "rootfs": "",
                "rootfs_type": "",
                "modules": "",
                "tests": "",
                "lava_server": "",
                "lava_stream": "",
                "device_type": "",
                "job_name": "",
                "notify": [],
                }
        self.jinja_env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))

    def get_device_status(self):
        try:
            return self._device_status
        except:
            conn = utils.get_connection(self.cfg)
            board = "%s_01" % self.board["device_type"]
            self._device_status = conn.scheduler.get_device_status(board)
            return self._device_status

# Template handling
    def get_template_from_file(self, file):
        logging.debug("template: using %s" % file)
        self.job_template = self.jinja_env.get_template(file)

    def save_job_to_file(self, ext="yaml"):
        try:
            os.makedirs(self.cfg['output_dir'])
        except:
            pass

        file = os.path.join(self.cfg['output_dir'],
                            self.job["job_name"] + "." + ext)

        with open(file, 'w') as f:
            f.write(self.job_template.render(self.job))

        logging.info("  ==> Job file saved to %s" % file)

    def send_to_lava(self):
        try:
            dev = self.get_device_status()
            if dev["status"] == "offline":
                logging.error("Device is offline, not sending the job")
                return
        except Exception as e:
            logging.error('Not sending the job: %s' % e)
            return

        logging.debug("Sending to LAVA")

        job_str = self.job_template.render(self.job)

        #
        # submit_job can return either an int (if there's one element)
        # or a list of them (if it's a multinode job).
        # This is crappy, but the least crappy way to handle this.
        #
        ret = utils.get_connection(self.cfg).scheduler.submit_job(job_str)
        try:
            for r in ret:
                logging.debug("Job sent (id: %s)" % r)
                logging.info("  ==> Job URL: %s/scheduler/job/%s" %
                             (self.cfg['web_ui_address'], r))
        except TypeError:
            logging.debug("Job sent (id: %s)" % ret)
            logging.info("  ==> Job URL: %s/scheduler/job/%s" %
                         (self.cfg['web_ui_address'], ret))

# Job handling
    def make_jobs(self):
        logging.info("Making jobs for %s" % self.board['device_type'])
        # Override basic values that are constant over each test
        if 'server' in self.cfg:
            self.job["lava_server"] = self.cfg['server']

        if 'stream' in self.cfg:
            self.job["lava_stream"] = self.cfg['stream']

        # rootfs
        if 'rootfs' in self.cfg:
            self.override('rootfs', self.cfg['rootfs'])
        else:
            self.override('rootfs', os.path.join(self.cfg['rootfs_path'],
                                                 self.board['rootfs']))

        logging.info("  Root filesystem path: %s" % self.job['rootfs'])

        # rootfs type
        if self.board["test_plan"] == "boot":
            self.job["rootfs_type"] = "ramdisk"
        elif self.board["test_plan"] == "boot-nfs":
            self.job["rootfs_type"] = "nfsrootfs"
        else:
            raise Exception(red("Invalid test_plan for board %s" %
                    self.board["name"]))

        self.job["device_type"] = self.board['device_type']

        if self.cfg['default_notify']:
            self.job["notify"] = self.board.get("notify", [])
        else:
            self.job["notify"] = self.cfg['notify']

        logging.info("  Notifications recipients: %s" % ", ".join(self.job['notify']))

        # Define which test to run
        tests = []
        if 'tests' in self.cfg:
            # This is needed to generate the test list as a list of dictionaries, as in the `boards.py` file.
            # It has two purposes:
            #   * When a test is in not affected to a board in `boards.py`, this
            #     simulates it in order to have the same data structure for the rest
            #     of the code. (a list of dict, and not a list of strings)
            #   * When a test has been affected to a board, but overrides a
            #     default value (the template to use, for example; useful for
            #     multinode tests), this makes sure to take that value into
            #     account by transforming the test name given in the command line, by
            #     the dictionary of the configuration.
            tests = [next(iter([e for e in self.board['tests'] if e['name'] == t]), {'name': t}) for t in self.cfg['tests']]
        else:
            tests = self.board.get("tests", [])
        for test in tests:
            configs = []
            # If we use a custom kernel
            if 'kernel' in self.cfg:
                data = { 'kernel': self.cfg['kernel'] }
                # Only one custom config
                configs = ['custom_kernel']

                if 'dtb' in self.cfg:
                    data['dtb'] = os.path.abspath(self.cfg['dtb'])
                else:
                    data['dtb'] = os.path.abspath(os.path.join(self.cfg['dtb_folder'],
                                                               self.board['dt'] + '.dtb'))

                if 'modules' in self.cfg:
                    data['modules'] = self.cfg['modules']

            # If we go fetch remote artifacts
            else:
                if 'defconfigs' in self.cfg:
                    for d in self.cfg['defconfigs']:
                        # Construct the list of configs to fetch
                        configs.append("%s/%s/%s" % (self.cfg['tree'], self.cfg['branch'], d))
                else:
                    # Get the configs from boards.py
                    configs = test.get('configs', self.board['configs'])

            for config in configs:
                logging.info("  Test %s on %s using %s" % (test['name'], self.board['device_type'], config))

                # Go fetch remote artifacts
                # data is already populated if we have a user supplied kernel
                if not 'kernel' in self.cfg:
                    tree, branch, defconfig = config.split('/')
                    data = None

                    for crawler in self.crawlers:
                        try:
                            data = crawler.crawl(self.board, tree, branch, defconfig)
                            # If we don't get any exception, then we've got what we want
                            break
                        except RemoteAccessError:
                            logging.debug('Didn\'t find the artifacts on current crawler..')

                    if data is None:
                        logging.warning("No artifacts available, skipping")
                        continue

                    job_name = "%s--%s--%s--%s--%s" % (
                            self.board['device_type'], # device type
                            config.split('/')[0], # tree
                            config.split('/')[1], # branch
                            config.split('/')[2], # defconfig
                            test['name'] # test name
                            )
                else:
                    job_name = "%s--%s--%s" % (
                            self.board['device_type'],
                            config,
                            test['name']
                            )

                self.override('kernel', data.get('kernel'))
                logging.info("    Kernel path: %s" % self.job['kernel'])

                self.override('device_tree', data.get('dtb'))
                logging.info("    Device tree path: %s" % self.job['device_tree'])

                # modules are optional if we have our own kernel
                if 'modules' in data:
                    self.override('modules', data['modules'])
                    logging.info('    Modules archive path: %s' % self.job['modules'])

                self.get_template_from_file(os.path.join(TEMPLATE_FOLDER,
                    test.get('template', DEFAULT_TEMPLATE)))

                self.job["tests"] = test['name']

                if 'job_name' in self.cfg:
                    self.job["job_name"] = self.cfg['job_name']
                else:
                    self.job["job_name"] = job_name
                logging.debug("    Job name: %s" % self.job['modules'])

                # Complete job creation
                if self.cfg['no_send']:
                    self.save_job_to_file()
                else:
                    self.send_to_lava()

    def override(self, key, value):
        logging.debug('Overriding key "%s" with value "%s"' % (key, value))
        remote_path = self.handle_file(value)
        self.job[key] = remote_path

# Files handling
    def handle_file(self, local):
        if not (local.startswith("http://") or local.startswith("file://") or
                local.startswith("https://")):
            remote = os.path.join(REMOTE_ROOT, os.path.basename(local))
            self.send_file(local, remote)
            remote = "file://" + remote
            return remote
        else:
            return local

    def send_file(self, local, remote):
        scp = utils.get_sftp(self.cfg["ssh_server"], 22, self.cfg["ssh_username"])
        logging.info('    Sending %s to %s' % (local, remote))
        try:
            scp.put(local, remote)
        except IOError as e:
            utils.mkdir_p(scp, os.path.dirname(remote))
            scp.put(local, remote)
        logging.info('    File %s sent' % local)

