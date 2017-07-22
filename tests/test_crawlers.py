import requests
import requests_mock
from nose.tools import assert_equal, assert_raises

from crawlers import FreeElectronsCrawler, KernelCICrawler
from crawlers import RemoteAccessError, RemoteEmptyError


class TestKernelCICrawler(object):
    BASE_URL = 'https://storage.kernelci.org/'
    RELEASE_URL = 'https://api.kernelci.org/build?limit=1&job=%s&field=kernel&sort=created_on&git_branch=%s'
    DEFAULT_API_TOKEN = 'foobar42'
    DEFAULT_ARCH = 'arm'
    DEFAULT_BRANCH = 'master'
    DEFAULT_DEFCONFIG = 'test_defconfig'
    DEFAULT_DTB = 'test'
    DEFAULT_IMAGE = 'zImage'
    DEFAULT_MODULES = 'modules.tar.xz'
    DEFAULT_RELEASE = 'version-deadcoffee-4.2'
    DEFAULT_TREE = 'mainline'

    @requests_mock.mock()
    def test_check_release(self, mock):
        url = self.RELEASE_URL % (self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        response = {
            'result': [{'kernel': self.DEFAULT_RELEASE}],
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }
        headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, json=response, request_headers=headers)

        crawler = KernelCICrawler(cfg)
        assert_equal(self.DEFAULT_RELEASE,
                     crawler._get_latest_release(self.DEFAULT_TREE,
                                                 self.DEFAULT_BRANCH))

    @requests_mock.mock()
    def test_check_release_error(self, mock):
        url = self.RELEASE_URL % (self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, status_code=404)

        crawler = KernelCICrawler(cfg)
        assert_raises(RemoteAccessError, crawler._get_latest_release,
                      self.DEFAULT_TREE, self.DEFAULT_BRANCH)

    @requests_mock.mock()
    def test_check_release_missing_result(self, mock):
        url = self.RELEASE_URL % (self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        response = {
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }
        headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, json=response, request_headers=headers)

        crawler = KernelCICrawler(cfg)
        assert_raises(RemoteEmptyError, crawler._get_latest_release,
                      self.DEFAULT_TREE, self.DEFAULT_BRANCH)

    @requests_mock.mock()
    def test_check_release_empty_result(self, mock):
        url = self.RELEASE_URL % (self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        response = {
            'result': list(),
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }
        headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, json=response, request_headers=headers)

        crawler = KernelCICrawler(cfg)
        assert_raises(RemoteEmptyError, crawler._get_latest_release,
                      self.DEFAULT_TREE, self.DEFAULT_BRANCH)

    @requests_mock.mock()
    def test_check_release_missing_result_kernel(self, mock):
        url = self.RELEASE_URL % (self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        response = {
            'result': [{'test': 'test'}],
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }
        headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, json=response, request_headers=headers)

        crawler = KernelCICrawler(cfg)
        assert_raises(RemoteEmptyError, crawler._get_latest_release,
                      self.DEFAULT_TREE, self.DEFAULT_BRANCH)

    @requests_mock.mock()
    def test_check_release_url(self, mock):
        url = self.RELEASE_URL % (self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        base_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                          self.DEFAULT_TREE,
                                          self.DEFAULT_BRANCH,
                                          self.DEFAULT_RELEASE,
                                          self.DEFAULT_ARCH,
                                          self.DEFAULT_DEFCONFIG)
        response = {
            'result': [{'kernel': self.DEFAULT_RELEASE}],
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }
        headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, json=response, request_headers=headers)

        crawler = KernelCICrawler(cfg)
        assert_equal(base_url, crawler._get_base_url(self.DEFAULT_TREE,
                                                     self.DEFAULT_BRANCH,
                                                     self.DEFAULT_ARCH,
                                                     self.DEFAULT_DEFCONFIG))

    @requests_mock.mock()
    def test_check_artifacts_all(self, mock):
        release_url = self.RELEASE_URL % (self.DEFAULT_TREE,
                                          self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        kernel_url = '%s/%s' % (config_url, self.DEFAULT_IMAGE)
        modules_url = '%s/%s' % (config_url, self.DEFAULT_MODULES)
        dtb_url = '%s/dtbs/%s.dtb' % (config_url, self.DEFAULT_DTB)
        release_response = {
            'result': [{'kernel': self.DEFAULT_RELEASE}],
        }
        release_headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, json=release_response,
                 request_headers=release_headers)
        mock.get(config_url)
        mock.get(kernel_url)
        mock.get(modules_url)
        mock.get(dtb_url)

        crawler = KernelCICrawler(cfg)
        items = crawler.crawl(board, self.DEFAULT_TREE,
                              self.DEFAULT_BRANCH,
                              self.DEFAULT_DEFCONFIG)

        assert_equal(kernel_url, items['kernel'])
        assert_equal(dtb_url, items['dtb'])
        assert_equal(modules_url, items['modules'])

    @requests_mock.mock()
    def test_check_artifacts_all_missing_config(self, mock):
        release_url = self.RELEASE_URL % (
            self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        release_response = {
            'result': [{'kernel': self.DEFAULT_RELEASE}],
        }
        release_headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, json=release_response,
                 request_headers=release_headers)
        mock.get(config_url, status_code=404)

        crawler = KernelCICrawler(cfg)
        assert_raises(RemoteAccessError, crawler.crawl,
                      board, self.DEFAULT_TREE, self.DEFAULT_BRANCH,
                      self.DEFAULT_DEFCONFIG)

    @requests_mock.mock()
    def test_check_artifacts_all_missing_kernel(self, mock):
        release_url = self.RELEASE_URL % (
            self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        kernel_url = '%s/%s' % (config_url, self.DEFAULT_IMAGE)
        release_response = {
            'result': [{'kernel': self.DEFAULT_RELEASE}],
        }
        release_headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, json=release_response,
                 request_headers=release_headers)
        mock.get(config_url)
        mock.get(kernel_url, status_code=404)

        crawler = KernelCICrawler(cfg)
        assert_raises(RemoteAccessError, crawler.crawl,
                      board, self.DEFAULT_TREE, self.DEFAULT_BRANCH,
                      self.DEFAULT_DEFCONFIG)

    @requests_mock.mock()
    def test_check_artifacts_all_missing_modules(self, mock):
        release_url = self.RELEASE_URL % (
            self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        kernel_url = '%s/%s' % (config_url, self.DEFAULT_IMAGE)
        modules_url = '%s/%s' % (config_url, self.DEFAULT_MODULES)
        release_response = {
            'result': [{'kernel': self.DEFAULT_RELEASE}],
        }
        release_headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, json=release_response,
                 request_headers=release_headers)
        mock.get(config_url)
        mock.get(kernel_url)
        mock.get(modules_url, status_code=404)

        crawler = KernelCICrawler(cfg)
        assert_raises(RemoteAccessError, crawler.crawl,
                      board, self.DEFAULT_TREE, self.DEFAULT_BRANCH,
                      self.DEFAULT_DEFCONFIG)

    @requests_mock.mock()
    def test_check_artifacts_all_missing_dtb(self, mock):
        release_url = self.RELEASE_URL % (
            self.DEFAULT_TREE, self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        kernel_url = '%s/%s' % (config_url, self.DEFAULT_IMAGE)
        modules_url = '%s/%s' % (config_url, self.DEFAULT_MODULES)
        dtb_url = '%s/dtbs/%s.dtb' % (config_url, self.DEFAULT_DTB)
        release_response = {
            'result': [{'kernel': self.DEFAULT_RELEASE}],
        }
        release_headers = {
            'Authorization': self.DEFAULT_API_TOKEN,
        }
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, json=release_response,
                 request_headers=release_headers)
        mock.get(config_url)
        mock.get(kernel_url)
        mock.get(modules_url)
        mock.get(dtb_url, status_code=404)

        crawler = KernelCICrawler(cfg)
        assert_raises(RemoteAccessError, crawler.crawl,
                      board, self.DEFAULT_TREE, self.DEFAULT_BRANCH,
                      self.DEFAULT_DEFCONFIG)


class TestFECrawler(object):
    BASE_URL = 'http://lava.free-electrons.com/downloads/builds/'
    DEFAULT_API_TOKEN = 'foobar42'
    DEFAULT_ARCH = 'arm'
    DEFAULT_BRANCH = 'master'
    DEFAULT_DEFCONFIG = 'test_defconfig'
    DEFAULT_DTB = 'test'
    DEFAULT_IMAGE = 'zImage'
    DEFAULT_MODULES = 'modules.tar.xz'
    DEFAULT_RELEASE = 'version-deadcoffee-4.2'
    DEFAULT_TREE = 'mainline'

    @requests_mock.mock()
    def test_check_release(self, mock):
        url = '%s/%s/%s/latest' % (self.BASE_URL,
                                   self.DEFAULT_TREE,
                                   self.DEFAULT_BRANCH)
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, text=self.DEFAULT_RELEASE)

        crawler = FreeElectronsCrawler(cfg)
        assert_equal(self.DEFAULT_RELEASE,
                     crawler._get_latest_release(self.DEFAULT_TREE,
                                                 self.DEFAULT_BRANCH))

    @requests_mock.mock()
    def test_check_release_error(self, mock):
        url = '%s/%s/%s/latest' % (self.BASE_URL,
                                   self.DEFAULT_TREE,
                                   self.DEFAULT_BRANCH)
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, status_code=404)

        crawler = FreeElectronsCrawler(cfg)
        assert_raises(RemoteAccessError, crawler._get_latest_release,
                      self.DEFAULT_TREE, self.DEFAULT_BRANCH)

    @requests_mock.mock()
    def test_check_release_url(self, mock):
        url = '%s/%s/%s/latest' % (self.BASE_URL,
                                   self.DEFAULT_TREE,
                                   self.DEFAULT_BRANCH)
        base_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                          self.DEFAULT_TREE,
                                          self.DEFAULT_BRANCH,
                                          self.DEFAULT_RELEASE,
                                          self.DEFAULT_ARCH,
                                          self.DEFAULT_DEFCONFIG)
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(url, text=self.DEFAULT_RELEASE)

        crawler = FreeElectronsCrawler(cfg)
        assert_equal(base_url, crawler._get_base_url(self.DEFAULT_TREE,
                                                     self.DEFAULT_BRANCH,
                                                     self.DEFAULT_ARCH,
                                                     self.DEFAULT_DEFCONFIG))

    @requests_mock.mock()
    def test_check_artifacts_all(self, mock):
        release_url = '%s/%s/%s/latest' % (self.BASE_URL,
                                           self.DEFAULT_TREE,
                                           self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        kernel_url = '%s/%s' % (config_url, self.DEFAULT_IMAGE)
        modules_url = '%s/%s' % (config_url, self.DEFAULT_MODULES)
        dtb_url = '%s/dtbs/%s.dtb' % (config_url, self.DEFAULT_DTB)
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, text=self.DEFAULT_RELEASE)
        mock.get(config_url)
        mock.get(kernel_url)
        mock.get(modules_url)
        mock.get(dtb_url)

        crawler = FreeElectronsCrawler(cfg)
        items = crawler.crawl(board, self.DEFAULT_TREE,
                              self.DEFAULT_BRANCH,
                              self.DEFAULT_DEFCONFIG)

        assert_equal(kernel_url, items['kernel'])
        assert_equal(dtb_url, items['dtb'])
        assert_equal(modules_url, items['modules'])

    @requests_mock.mock()
    def test_check_artifacts_all_missing_config(self, mock):
        release_url = '%s/%s/%s/latest' % (self.BASE_URL,
                                           self.DEFAULT_TREE,
                                           self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, text=self.DEFAULT_RELEASE)
        mock.get(config_url, status_code=404)

        crawler = FreeElectronsCrawler(cfg)
        assert_raises(RemoteAccessError, crawler.crawl,
                      board, self.DEFAULT_TREE, self.DEFAULT_BRANCH,
                      self.DEFAULT_DEFCONFIG)

    @requests_mock.mock()
    def test_check_artifacts_all_missing_kernel(self, mock):
        release_url = '%s/%s/%s/latest' % (self.BASE_URL,
                                           self.DEFAULT_TREE,
                                           self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        kernel_url = '%s/%s' % (config_url, self.DEFAULT_IMAGE)
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, text=self.DEFAULT_RELEASE)
        mock.get(config_url)
        mock.get(kernel_url, status_code=404)

        crawler = FreeElectronsCrawler(cfg)
        assert_raises(RemoteAccessError, crawler.crawl,
                      board, self.DEFAULT_TREE, self.DEFAULT_BRANCH,
                      self.DEFAULT_DEFCONFIG)

    @requests_mock.mock()
    def test_check_artifacts_all_missing_modules(self, mock):
        release_url = '%s/%s/%s/latest' % (self.BASE_URL,
                                           self.DEFAULT_TREE,
                                           self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        kernel_url = '%s/%s' % (config_url, self.DEFAULT_IMAGE)
        modules_url = '%s/%s' % (config_url, self.DEFAULT_MODULES)
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, text=self.DEFAULT_RELEASE)
        mock.get(config_url)
        mock.get(kernel_url)
        mock.get(modules_url, status_code=404)

        crawler = FreeElectronsCrawler(cfg)
        assert_raises(RemoteAccessError, crawler.crawl,
                      board, self.DEFAULT_TREE, self.DEFAULT_BRANCH,
                      self.DEFAULT_DEFCONFIG)

    @requests_mock.mock()
    def test_check_artifacts_all_missing_dtb(self, mock):
        release_url = '%s/%s/%s/latest' % (self.BASE_URL,
                                           self.DEFAULT_TREE,
                                           self.DEFAULT_BRANCH)
        config_url = '%s/%s/%s/%s/%s/%s' % (self.BASE_URL,
                                            self.DEFAULT_TREE,
                                            self.DEFAULT_BRANCH,
                                            self.DEFAULT_RELEASE,
                                            self.DEFAULT_ARCH,
                                            self.DEFAULT_DEFCONFIG)
        kernel_url = '%s/%s' % (config_url, self.DEFAULT_IMAGE)
        modules_url = '%s/%s' % (config_url, self.DEFAULT_MODULES)
        dtb_url = '%s/dtbs/%s.dtb' % (config_url, self.DEFAULT_DTB)
        board = {
            'arch': self.DEFAULT_ARCH,
            'dt': self.DEFAULT_DTB,
            'name': 'test'
        }
        cfg = {
            'api_token': self.DEFAULT_API_TOKEN,
        }

        mock.get(release_url, text=self.DEFAULT_RELEASE)
        mock.get(config_url)
        mock.get(kernel_url)
        mock.get(modules_url)
        mock.get(dtb_url, status_code=404)

        crawler = FreeElectronsCrawler(cfg)
        assert_raises(RemoteAccessError, crawler.crawl,
                      board, self.DEFAULT_TREE, self.DEFAULT_BRANCH,
                      self.DEFAULT_DEFCONFIG)
