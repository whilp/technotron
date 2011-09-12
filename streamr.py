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

def pop(store, opts):
    item = store.pop()
    sys.stderr.write("{link}\n".format(**item))
    sys.stdout.write("{url}\n".format(**item))

def next(store, opts):
    item = iter(store).next()
    sys.stderr.write("{link}\n".format(**item))
    sys.stdout.write("{url}\n".format(**item))

def remove(store, opts, item):
    store.remove(item)

commandfns = dict(
    next=next,
    pop=pop,
    remove=remove,
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

def parserss(source):
    context = etree.iterparse(source, events=("start", "end"))
    wasinitem = False
    for action, elem in context:
        if elem.tag == "item":
            stillinitem = action == "start"
            if wasinitem is not stillinitem:
                wasinitem = stillinitem
                yield elem
                elem.clear()
        if wasinitem and action == "end":
            yield elem
            elem.clear()

def rss(source):
    data = {}
    for elem in parserss(source):
        if elem.tag == "link":
            data["link"] = elem.text
        elif elem.tag == "enclosure":
            data["url"] = elem.get("url")
        elif elem.tag == "item":
            yield Item(**data)
            data = {}

def fact(source):
    data = None
    for elem in parserss(source):
        if elem.tag == "title" and "FACT mix" in elem.text:
            data = {}
        if data is None:
            continue

        if elem.tag == "link":
            data["link"] = elem.text
        elif elem.tag == "{http://purl.org/rss/1.0/modules/content/}encoded":
            for line in elem.text.splitlines(): 
                if "Direct download: <a href=" in line:
                    data["url"] = [x for x in line.split('"') if x.startswith("http")][0]
                    break
            yield Item(**data)
            data = parser = None

fns = {}

if json is not None:
    fns["soundcloud"] = soundcloud

if etree is not None:
    fns["rss"] = rss
    fns["fact"] = fact

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != 17:
            raise

class Item(dict):
    
    def __init__(self, **kwargs):
        kwargs["path"] = self.descheme(kwargs["link"]).strip("/")
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
                full = os.path.join(dirpath, fname)
                with open(full, 'r') as fd:
                    yield Item(**dict(line.strip().split(" ", 1) for line in fd))
    
    def add(self, item):
        if item not in self:
            fname = os.path.join(self.store, str(item))
            makedirs(os.path.dirname(fname))
            with open(os.path.join(self.store, str(item)), 'w') as fd:
                for k, v in item.items():
                    fd.write("{0} {1}\n".format(k, v))

    def clear(self):
        shutil.rmtree(self.store)
        shutil.rmtree(self.seen)
        self.init()

    def pop(self):
        item = iter(self).next()
        self.remove(item)

        return item

    def remove(self, item):
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
