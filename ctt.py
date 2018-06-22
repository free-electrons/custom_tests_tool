#!/usr/bin/env python3
# -*- coding:utf-8 -*
#

import json
import logging
import os
import sys
import getpass

from src import ssh_utils
from src.Config import CTTCmdline, CTTConfig
from src.rootfs_chooser import RootfsChooser, RootfsAccessError
from src.launcher import BaseLauncher

class CTTLauncher(BaseLauncher):
    """
    This class implements the BaseLauncher interface to launch manual custom
    tests.
    It is be able to upload the provided artifacts through SSH before crafting
    the job.
    """
    _CMDLINE_CLASS = CTTCmdline
    _CONFIG_CLASS = CTTConfig
    _REMOTE_ROOT = os.path.join("/tmp/ctt/", getpass.getuser())

    def _set_logging(self):
        super(CTTLauncher, self)._set_logging()
        paramiko_logger = logging.getLogger("paramiko")
        paramiko_logger.setLevel(logging.WARN)

    # Files handling
    def _handle_file(self, local):
        if not (local.startswith("http://") or local.startswith("file://") or
                local.startswith("https://")):
            remote = os.path.join(CTTLauncher._REMOTE_ROOT, os.path.basename(local))
            self._send_file(local, remote)
            remote = "file://" + remote
            return remote
        else:
            return local

    def _send_file(self, local, remote):
        scp = ssh_utils.get_sftp(self._cfg["ssh_server"], 22, self._cfg["ssh_username"])
        logging.info('  Sending %s to %s' % (local, remote))
        try:
            scp.put(local, remote)
        except IOError as e:
            ssh_utils.mkdir_p(scp, os.path.dirname(remote))
            scp.put(local, remote)
        logging.info('  File %s sent' % local)

    def poll(self, all_jobs):
        statuses = self.crafter.wait_jobs(all_jobs)
        has_canceled = False
        has_failed = False
        for job_id, status in statuses.items():
            # Canceled (4) or Canceling (5).
            if status == 4 or status == 5:
                has_canceled = True
            # Incomplete (3).
            if status == 3:
                has_failed = True

        # If at least one job has been canceled, we can't conclude on
        # the result of the test, use special exit code 2 for this
        # situation.
        if has_canceled:
            logging.error("At least one job has been canceled")
            return 2
        # At least one job has failed, consider the entire test has
        # failed.
        elif has_failed:
            logging.error("At least one job has failed")
            return 1
        else:
            logging.info("All jobs successful")
            return 0

    # Launcher
    def launch(self):
        if self._cfg['list']:
            print("Here are the available boards:")
            for b in sorted(self._boards_config):
                print("  - %s" % b)
            return
        all_jobs = list()
        for board in self._cfg['boards']:
            logging.info(board)

            # Handle rootfs, since it's not mandatory
            if 'rootfs' not in self._cfg:
                try:
                    rootfs = RootfsChooser().get_url(self._boards_config[board])
                except RootfsAccessError as e:
                    logging.warning(e)
                    continue
            else:
                rootfs = self._cfg['rootfs']

            if 'tests' not in self._cfg:
                logging.critical("  No test asked, aborting")
                sys.exit(1)

            for test in self._cfg['tests']:
                logging.debug("  Building job(s) for %s" % test)

                artifacts = {}

                if 'kernel' in self._cfg:
                    artifacts['kernel'] = self._handle_file(self._cfg['kernel'])

                if 'dtb' in self._cfg:
                    artifacts['dtb'] = self._handle_file(self._cfg['dtb'])
                elif 'dtb_folder' in self._cfg:
                    artifacts['dtb'] = self._handle_file("%s/%s.dtb" % (self._cfg['dtb_folder'],
                            self._boards_config[board]['dt']))

                if 'modules' in self._cfg:
                    artifacts['modules'] = self._handle_file(self._cfg['modules'])

                artifacts['rootfs'] = self._handle_file(rootfs)

                logging.info("  Making %s job" % test)
                job_name = "%s--custom_kernel--%s" % (board, test)
                jobs = self.crafter.make_jobs(board, artifacts, test, job_name)
                if jobs:
                    all_jobs += jobs
        if self._cfg['poll']:
            return self.poll(all_jobs)
        else:
            return 0

if __name__ == "__main__":
    sys.exit(CTTLauncher().launch())
