from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

class OptionError(Exception):
    pass

class BaseCmdline(object):
    """
    A Cmdline object basically behaves like a dictionary, but makes all the
    needed validation in its constructor.
    It needs one mandatory argument to initialize: a dictionary object of the
    boards to make the validation (boards.json)
    A second optional boolean argument can be passed to allow or not the
    validation. It defaults to True (allow).

    This class must be subclassed to implement its _parse_cmdline method, to
    describe the wanted command line arguments.

    When the argument validation fails, this class throws an OptionError
    exception.
    """
    def __init__(self, boards, validate=True):
        self._boards = boards
        self._parse_cmdline()
        if validate:
            self._validate_cmdline()

    def _parse_cmdline(self):
        raise NotImplementedError("Missing parsing function")

    def _validate_cmdline(self):
        # We can always just list the boards
        if self._cmdline['list']:
            return

        # Validate that we have all the basic options
        for option in self._MANDATORY_KEYS:
            if not self.__contains__(option):
                raise OptionError('Missing %s option' % option)

        if 'boards' in self:
            for board in self._cmdline['boards']:
                # Expand all boards to what we know
                if board == 'all':
                    self._cmdline['boards'] = list(self._boards.keys())
                    break

                if board not in self._boards.keys():
                    raise OptionError('Invalid board %s' % board)

    def __getitem__(self, key):
        if key in self._cmdline:
            val = self._cmdline[key]
            if val is not None:
                return self._cmdline[key]

        raise KeyError

    def __contains__(self, key):
        if key in self._cmdline:
            val = self._cmdline[key]
            if val is not None:
                return True

        return False

class CICmdline(BaseCmdline):
    _MANDATORY_KEYS = ['boards']

    def _parse_cmdline(self):
        parser = ArgumentParser(description='Send custom job to a LAVA server')

        parser.add_argument('--no-send', action='store_true',
                            help='Don\'t send the job')
        parser.add_argument('--output-dir', default='jobs',
                         help='Path where the jobs will be stored if not sent')
        parser.add_argument('-b', '--boards', nargs='+',
                            help='Board to run the test on')
        parser.add_argument('-l', '--list', action='store_true',
                            help='List all the available boards')
        parser.add_argument('-d', '--debug', action='store_true',
                            help='Debug mode')

        self._cmdline = vars(parser.parse_args())

class CTTCmdline(BaseCmdline):
    _MANDATORY_KEYS = [
            'boards',
            'kernel',
        ]

    def _parse_cmdline(self):
        parser = ArgumentParser(description='Send custom job to a LAVA server')

        parser.add_argument('-d', '--debug', action='store_true',
                            help='Debug mode')
        parser.add_argument('--no-send', action='store_true',
                            help='Don\'t send the job')
        parser.add_argument('-b', '--boards', nargs='+',
                            help='Board to run the test on')
        parser.add_argument('-l', '--list', action='store_true',
                            help='List all the available boards')

        job = parser.add_argument_group('Job handling')
        job.add_argument('--output-dir', default='jobs',
                         help='Path where the jobs will be stored')

        job.add_argument('--timeout', help='Set a manual timeout for your job.')
        job.add_argument('--rootfs', help='Path to your rootfs image')
        job.add_argument('--kernel', help='Path to your kernel image')
        job.add_argument('--dtb', help='Path to your dtb')
        job.add_argument('--dtb-folder', help='Path to your dtb folder')
        job.add_argument('--modules', help='Path to your modules tar.gz')
        job.add_argument('--poll', action='store_true', help='Poll until the jobs results are available')
        job.add_argument('-t', '--tests', nargs='+',
                         help='Tests to run on the board')

        lava = parser.add_argument_group('LAVA server options')
        lava.add_argument('--server', help='LAVA server to send results to')
        lava.add_argument('--username', help='LAVA username')
        lava.add_argument('--token', help='LAVA token')

        ssh = parser.add_argument_group('SSH server options')
        ssh.add_argument('--ssh-server', help='SSH server')
        ssh.add_argument('--ssh-username', help='SSH username')

        self._cmdline = vars(parser.parse_args())

    def _validate_cmdline(self):
        super(CTTCmdline, self)._validate_cmdline()
        # We can always list the boards
        if 'list' in self:
            return
        if ('dtb' not in self and
                'dtb_folder' not in self):
            raise OptionError("You must provide either a dtb or a dtb folder")

