from nose.tools import assert_equal, assert_raises
import mock
import xmlrpc

from src.writers import FileWriter, LavaWriter
from src.writers import UnavailableError


class TestFileWriter(object):
    OUTPUT_DIR = 'foo'
    CONTENT = 'test'
    NAME = 'test-job-name'

    def test_fail_open(self):
        cfg = {
            'output_dir': self.OUTPUT_DIR,
        }

        mo = mock.mock_open()
        with mock.patch('builtins.open', mo, create=True) as mocked:
            mocked.side_effect = IOError

            writer = FileWriter(cfg)
            assert_raises(UnavailableError, writer.write, dict(),
                          self.NAME, self.CONTENT)

    def test_write(self):
        cfg = {
            'output_dir': self.OUTPUT_DIR,
        }

        mo = mock.mock_open(read_data=self.CONTENT)
        with mock.patch('builtins.open', mo, create=True) as mocked:
            path = '%s/%s.yaml' % (self.OUTPUT_DIR, self.NAME)
            mocked_file = mocked.return_value

            writer = FileWriter(cfg)
            results = writer.write(dict(), self.NAME, self.CONTENT)

            mocked.assert_called_once_with(path, 'w')
            mocked_file.write.assert_called_with(self.CONTENT)
            assert_equal(results, [path])


class TestLavaWriter(object):
    DEVICE_TYPE = 'foo_bar'
    CONTENT = 'test'
    NAME = 'test-job-name'
    UI_ADDRESS = 'http://webui.example.org'

    @mock.patch('xmlrpc.client.ServerProxy')
    def test_connection_error(self, mock):
        board = {
            'device_type': self.DEVICE_TYPE,
        }
        cfg = {
            'server': 'https://test.example.org/RPC2',
            'username': 'foobar',
            'token': 'deadcoffee42',
        }
        response = {
            'status': 'offline',
        }

        mock.side_effect = xmlrpc.client.Error
        assert_raises(UnavailableError, LavaWriter, cfg)

    @mock.patch('xmlrpc.client.ServerProxy')
    def test_device_offline(self, mock):
        board = {
            'device_type': self.DEVICE_TYPE,
        }
        cfg = {
            'server': 'https://test.example.org/RPC2',
            'username': 'foobar',
            'token': 'deadcoffee42',
        }
        response = {
            'status': 'offline',
        }

        mock_proxy = mock.return_value
        mock_proxy.scheduler.get_device_status.return_value = response

        writer = LavaWriter(cfg)
        assert_raises(UnavailableError, writer.write, board,
                      self.NAME, self.CONTENT)

    @mock.patch('xmlrpc.client.ServerProxy')
    def test_write_unique(self, mock):
        board = {
            'device_type': self.DEVICE_TYPE,
        }
        cfg = {
            'server': 'https://test.example.org/RPC2',
            'username': 'foobar',
            'token': 'deadcoffee42',
            'web_ui_address': self.UI_ADDRESS,
        }
        response = {
            'status': 'online',
        }

        mock_proxy = mock.return_value
        mock_proxy.scheduler.submit_job.return_value = 42

        writer = LavaWriter(cfg)
        results = writer.write(board, self.NAME, self.CONTENT)

        mock_proxy.scheduler.get_device_status.assert_called_with('%s_01' % self.DEVICE_TYPE)
        mock_proxy.scheduler.submit_job.assert_called_with(self.CONTENT)
        assert_equal(results, ['%s/scheduler/job/%d' % (self.UI_ADDRESS, 42)])

    @mock.patch('xmlrpc.client.ServerProxy')
    def test_write_multiple(self, mock):
        board = {
            'device_type': self.DEVICE_TYPE,
        }
        cfg = {
            'server': 'https://test.example.org/RPC2',
            'username': 'foobar',
            'token': 'deadcoffee42',
            'web_ui_address': self.UI_ADDRESS,
        }
        response = {
            'status': 'online',
        }

        mock_proxy = mock.return_value
        mock_proxy.scheduler.submit_job.return_value = (42, 84)

        writer = LavaWriter(cfg)
        results = writer.write(board, self.NAME, self.CONTENT)

        mock_proxy.scheduler.get_device_status.assert_called_with('%s_01' % self.DEVICE_TYPE)
        mock_proxy.scheduler.submit_job.assert_called_with(self.CONTENT)
        assert_equal(results, ['%s/scheduler/job/%d' % (self.UI_ADDRESS, 42),
                               '%s/scheduler/job/%d' % (self.UI_ADDRESS, 84)])
