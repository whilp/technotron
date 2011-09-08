#!/usr/bin/env python

import json
import logging
import os
import shutil
import sys
import urllib2
import urlparse

from collections import namedtuple

from lxml import etree

try:
    NullHandler = logging.NullHandler
except AttributeError:
    class NullHandler(logging.Handler):
        def emit(self, record): pass

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

def main(argv):
    log.addHandler(logging.StreamHandler())

    root, url = argv[1:3]
    log.debug("initializing store in %s", root)
    store = Store(".")
    store.init()

    log.debug("opening %s", url)

    for item in feed(url, fns=fns):
        log.debug("feed yields %s", item)
        store.add(item)

def feed(url, fns=None):
    fnname, url = url.split("+", 1)
    source = urllib2.urlopen(url)
    fn = fns[fnname]

    return fn(source)

def soundcloud(source):
    pushstr = "window.SC.bufferTracks.push("
    pushlen = len(pushstr)
    for line in source:
        if line.startswith(pushstr):
            jsonstr = line[pushlen:-3]
            data = json.loads(jsonstr)
            link = urlparse.urljoin(source.url, data["uri"])
            url = data["streamUrl"]
            yield Item(link=link, url=url)

def rss(source):
    context = etree.iterparse(source, events=("start", "end"))
    initem = False
    data = {}
    for action, elem in context:
        if elem.tag == "item":
            initem = action == "start"
            if data:
                yield Item(**data)
                data = {}
                
        if not initem:
            continue

        if elem.tag == "link":
            data["link"] = elem.text
        elif elem.tag == "enclosure":
            data["url"] = elem.get("url")

fns = dict(
    soundcloud=soundcloud,
    rss=rss,
)

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != 17:
            raise

class Item(dict):
    
    def __init__(self, **kwargs):
        kwargs["path"] = self.descheme(kwargs["link"]).lstrip("/")
        super(Item, self).__init__(**kwargs)

    def __str__(self):
        return self["path"]

    def descheme(self, url):
        return urlparse.urlunparse(("",) + urlparse.urlparse(url)[1:])

class Store(set):

    def __init__(self, root=None, **kwargs):
        self.root = root
        self.store = os.path.join(self.root, "store")
        self.seen = os.path.join(self.root, "seen")

        super(Store, self).__init__(**kwargs)

    def init(self):
        self.makedirs(self.store)
        self.makedirs(self.seen)

    def makedirs(self, path):
        makedirs(path)

    def __contains__(self, item):
        for root in (self.store, self.seen):
            if os.path.exists(os.path.join(root, str(item))):
                return True

        return False
    
    def add(self, item):
        if item not in self:
            fname = os.path.join(self.store, str(item))
            makedirs(os.path.dirname(fname))
            with open(os.path.join(self.store, str(item)), 'w') as fd:
                fd.write(item["url"])

    def clear(self):
        shutil.rmtree(self.store)
        shutil.rmtree(self.seen)
        self.init()

    def remove(self):
        try:
            os.remove(os.path.join(self.store, str(item)))
        except OSError, e:
            if e.errno == 2:
                raise KeyError(item)

    def update(self, items):
        for item in items:
            self.add(item)

if __name__ == "__main__":
    try:
        ret = main(sys.argv)
    except KeyboardInterrupt:
        ret = None
    sys.exit(ret)
