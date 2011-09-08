#!/usr/bin/env python

import logging
import os
import shutil
import sys
import urllib2
import urlparse

from collections import namedtuple
from optparse import OptionParser, make_option as Option

try:
    from lxml import etree
except ImportError:
    etree = None
try:
    import json
except ImportError:
    json = None

try:
    NullHandler = logging.NullHandler
except AttributeError:
    class NullHandler(logging.Handler):
        def emit(self, record): pass

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

options = [
    Option("-q", "--quiet", default=0, action="count"),
    Option("-s", "--silent", default=False, action="store_true"),
    Option("-v", "--verbose", default=0, action="count"),
    Option("--store", default="."),
]

def main(argv):
    optparser = OptionParser(
        option_list=options,
    )
    (opts, args) = optparser.parse_args(args=argv)

    if not opts.silent:
        log.addHandler(logging.StreamHandler())
        log.level = max(1, logging.WARNING - (10 * (opts.verbose - opts.quiet)))

    log.debug("initializing store in %s", opts.store)
    store = Store(opts.store)
    store.init()

    script = args.pop(0)
    command = args.pop(0)
    commandfn = commandfns.get(command, None)
    if commandfn is None:
        optparser.error("unsupported command %r" % command)

    return commandfn(store, opts, *args)

def update(store, opts, url):
    for item in feed(url, fns=fns):
        log.debug("feed yields %s", item)
        store.add(item)

commandfns = dict(
    update=update,
)

def feed(url, fns=None):
    fnname, url = url.split("+", 1)
    source = urllib2.urlopen(url)
    fn = fns[fnname]
    log.debug("dispatching %s to %s", url, fnname)

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

fns = {}

if json is not None:
    fns["soundcloud"] = soundcloud

if etree is not None:
    fns["rss"] = rss

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

    def __iter__(self):
        for dirpath, dirnames, filenames in os.walk(self.store):
            for fname in filenames:
                full = os.path.join(self.store, dirpath, fname)
                with open(full, 'r') as fd:
                    url = fd.read()
                yield Item(link=full, url=url)
    
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
            os.renames(
                os.path.join(self.store, str(item)),
                os.path.join(self.seen, str(item))
            )
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
