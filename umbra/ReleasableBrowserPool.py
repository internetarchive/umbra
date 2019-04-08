from brozzler import BrowserPool


class ReleasableBrowserPool(BrowserPool):

    def release_everything(self):
          for browser in  self._in_use:
              browser.stop()  # make sure
          with self._lock:
              self._in_use.clear()
