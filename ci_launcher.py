#!/usr/bin/env python3
# -*- coding:utf-8 -*
#

import json
import logging
import os
import sys

from src.Config import CICmdline, CIConfig
from src.CTTFormatter import CTTFormatter
from src.crawlers import FreeElectronsCrawler, KernelCICrawler
from src.crawlers import RemoteAccessError, RemoteEmptyError
from src.rootfs_chooser import RootfsChooser, RootfsAccessError
from src.launcher import BaseLauncher

class CILauncher(BaseLauncher):
    """
    This class implements the BaseLauncher interface to launch automatic CI
    tests.
    It fetches the artifacts from the different crawlers, and gets the test to
    run from the `ci_tests.json` file.
    """
    _CMDLINE_CLASS = CICmdline
    _CONFIG_CLASS = CIConfig

    def _set_config(self):
        super(CILauncher, self)._set_config()
        ctt_root_location = os.path.abspath(os.path.dirname(
            os.path.realpath(__file__)))

        with open(os.path.join(ctt_root_location, "ci_tests.json")) as f:
            self._tests_config = json.load(f)
        self._crawlers = [
                FreeElectronsCrawler(self._cfg),
                KernelCICrawler(self._cfg)
            ]

    def launch(self):
        if self._cfg['list']:
            print("Here are the available boards:")
            for b in sorted(self._boards_config):
                print("  - %s" % b)
            return
        for board in self._cfg['boards']:

            logging.info(board)
            if not self._tests_config[board]['tests']:
                logging.info("  No test set")

            # Retrieve the device status
            dev = self.crafter.get_device_status(board)
            if dev['status'] == "offline":
                logging.error("Device is offline, not sending jobs")
                continue
            elif dev['status'] == "retired":
                logging.error("Device is retired, not sending jobs")
                continue

            try:
                rootfs = RootfsChooser().get_url(self._boards_config[board])
            except RootfsAccessError as e:
                logging.warning(e)
                continue
            for test in self._tests_config[board]['tests']:
                logging.info(" Building job(s) for %s" % test['name'])

                # Check if configs has been overridden by test
                if 'configs' in test:
                    configs = test['configs']
                    logging.debug("  Configs overridden: %s" % configs)
                else:
                    configs = self._tests_config[board]['configs']
                    logging.debug("  Using default configs: %s" % configs)

                # Check if we need to exclude some configs
                if 'exclude_configs' in test:
                    exclude_configs = test['exclude_configs']
                    logging.debug("  Configs excluded: %s" % exclude_configs)
                    for exclude in exclude_configs:
                        configs.remove(exclude)
                    logging.debug("  Using new configs: %s" % configs)

                for config in configs:
                    logging.info("  Fetching artifacts for %s" % config)
                    artifacts = None
                    for crawler in self._crawlers:
                        try:
                            artifacts = crawler.crawl(self._boards_config[board],
                                    config['tree'], config['branch'],
                                    config['defconfig'])
                        except RemoteEmptyError as e:
                            logging.debug("  No artifacts returned by crawler %s: %s" %
                                    (crawler.__class__.__name__, e))
                        except RemoteAccessError as e:
                            logging.warning("  Remote unreachable for crawler %s: %s" %
                                    (crawler.__class__.__name__, e))
                    if artifacts:
                        artifacts['rootfs'] = rootfs
                        logging.info("  Making %s job on %s -> %s -> %s" %
                                (test['name'], config['tree'], config['branch'],
                                    config['defconfig']))
                        job_name = "%s--%s--%s--%s--%s" % (
                                board, config['tree'], config['branch'],
                                config['defconfig'], test['name']
                                )
                        self.crafter.make_jobs(board, artifacts, test['name'], job_name)
                    else:
                        logging.error("  No artifacts found")


if __name__ == "__main__":
    CILauncher().launch()

