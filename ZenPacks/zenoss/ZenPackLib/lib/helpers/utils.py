##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016-2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import inspect
import io
import os
import re
import sys
import time

from collections.abc import Mapping
from io import StringIO

import yaml

from .loaders import (
    OrderedLoader,
    ZenPackSpecLoader,
    ZenPackSpecFromDictLoader,
)
from .ZenPackLibLog import DEFAULTLOG

# list of yaml sections with DEFAULTS capability
YAML_HAS_DEFAULTS = [
    "classes",
    "datapoints",
    "datasources",
    "graphpoints",
    "graphs",
    "properties",
    "relationships",
    "thresholds",
    "zProperties",
]


def load_yaml(path=None, verbose=False, level=0):
    """"""
    # determine caller directory and attempt to load from it
    if not path:
        path = _get_calling_dir()
        if path is None:
            raise RuntimeError("Unable to determine location of yaml files")

    if not isinstance(path, list):
        if os.path.isdir(path):
            yamls = _get_yamls(path, verbose=verbose, level=level)
            if not yamls:
                raise RuntimeError("No yaml files found in {}".format(path))
        else:
            yamls = [path]
    else:
        yamls = path

    if len(yamls) == 1:
        yaml_doc = yamls[0]
        loader = ZenPackSpecLoader
    else:
        # build python dict of merged YAML data
        yaml_doc = get_merged_docs(yamls)
        loader = ZenPackSpecFromDictLoader

    return _load_yaml(yaml_doc, loader, verbose, level)


def _load_yaml(yaml_doc, loader, verbose, level):
    loader.QUIET = not verbose
    loader.LEVEL = level

    # load YAML and create ZenPackSpec
    start = time.time()
    CFG = None

    try:
        CFG = load_yaml_single(yaml_doc, loader=loader)
    except Exception as e:
        DEFAULTLOG.exception(e)

    if CFG:
        CFG.create()
        end = time.time() - start
        DEFAULTLOG.debug("Loaded {} in {:0.2f}s".format(CFG.name, end))
    else:
        DEFAULTLOG.error("Unable to load {}".format(yaml_doc))
    return CFG


def _get_calling_dir():
    """determine source directory of ZenPack's load_yaml call"""
    for i in inspect.stack():
        frame, filename, lineno, method_name, lines, idx = i
        if "__init__.py" not in filename:
            continue
        for line in lines:
            if "load_yaml" in line:
                return os.path.dirname(filename)
    return None


def _get_yamls(path, verbose=False, level=0):
    files = []
    for f in os.listdir(path):
        if not f.endswith(".yaml"):
            continue
        files.append("{}/{}".format(path, f))
    return files


_zenpacks_name_search = re.compile(r"^\s{0,2}name: ZenPacks").search
_must_load_search = re.compile(
    r"^\s*classes:|^\s*class_relationships:|^\s{0,2}zProperties:|^\s*link_providers:"
).search


def load_yaml_single(yaml_doc, loader=ZenPackSpecLoader):
    """return YAML loaded from string or file with given loader."""
    # if it's a string
    if isinstance(yaml_doc, str) and os.path.isfile(yaml_doc):
        DEFAULTLOG.debug("Loading YAML from {}".format(yaml_doc))
        yaml_file = open(yaml_doc, "r")
        # only certain yaml needs to be loaded when not during ZP install
        if not sys.argv[0].endswith("zenpack.py"):
            must_load = False
            name_line = ""
            for line in yaml_file:
                # Top level of yaml can be indented, but we'll only account
                # for 2 spaces to avoid picking up a similar attribute at
                # another indent level.
                if _zenpacks_name_search(line):
                    name_line = line
                    continue
                # zProperties can occur at top level or within event classes,
                # so only match them with up to a 2-space indentation to avoid
                # the event class ones.
                if _must_load_search(line):
                    must_load = True
                    break
            if must_load:
                yaml_file.seek(0)
            else:
                DEFAULTLOG.debug(
                    "Not doing a ZP install so not loading %s", yaml_doc
                )
                yaml_file.close()
                yaml_file = StringIO(name_line)
        return yaml.load(yaml_file, loader)  # noqa: S506
    else:
        return yaml.load(yaml_doc, loader)  # noqa: S506


def get_merged_docs(docs=None):
    """return recursively merged dictionary"""
    if docs is None:
        docs = []
    new = {}
    for doc in docs:
        zp_id = new.get("name")
        cfg = load_yaml_single(doc, loader=yaml.FullLoader)
        # If yaml has no "name:" line and will not be loaded because we
        # aren't doing a ZP install, load_yaml_single will return a None,
        # so don't try to merge.
        if cfg:
            # check for conflicting zenpack ids
            if zp_id:
                name = cfg.get("name")
                if name and name != zp_id:
                    DEFAULTLOG.error(
                        "Skipping {} since conflicting ZenPack names "
                        "found: {} vs {}".format(doc, zp_id, name)
                    )
                    continue
            _merge_dict(new, cfg)
            del cfg
    return new


def _merge_dict(target, source):
    for k in source:
        if k in target:
            if isinstance(target[k], dict) and isinstance(source[k], Mapping):
                _merge_dict(target[k], source[k])
            elif isinstance(target[k], list) and isinstance(source[k], list):
                target[k].extend(source[k])
        else:
            target[k] = source[k]


def optimize_yaml(orig_yaml):
    """optimize layout of YAML file"""
    # apply log verbosity settings
    ZenPackSpecLoader.QUIET = False
    ZenPackSpecLoader.LEVEL = 0
    # Load as data values
    orig_data = load_yaml_single(orig_yaml, loader=OrderedLoader)
    # create optimized YAML based on original data
    optimized_yaml = get_optimized_yaml(orig_data)
    # Load optimized data values
    _ = load_yaml_single(optimized_yaml, loader=OrderedLoader)
    if not compare_zenpackspecs(orig_yaml, optimized_yaml):
        DEFAULTLOG.warn(
            "OPTIMIZATION FAILED VERIFICATION!  "
            "Please review optimized YAML prior to use"
        )
        diff = compare_specparam_yaml_files(orig_yaml, optimized_yaml)
        if diff:
            print(diff)
    return optimized_yaml


def get_specparam_yaml_pair(orig_yaml, new_yaml):
    """return a pair of YAML files after loading"""
    from .Dumper import Dumper

    orig_cfg = load_yaml_single(orig_yaml)
    orig_cfg.create()
    new_cfg = load_yaml_single(new_yaml)
    new_cfg.create()
    orig_dump = yaml.dump(orig_cfg.specparams, Dumper=Dumper)
    new_dump = yaml.dump(new_cfg.specparams, Dumper=Dumper)
    return orig_dump, new_dump


def compare_specparam_yaml_files(orig_yaml, new_yaml):
    """return diff between ZenPackSpecParams-derived YAML files"""
    from ..base.ZenPack import ZenPack

    orig_dump, new_dump = get_specparam_yaml_pair(orig_yaml, new_yaml)
    return ZenPack.get_yaml_diff(orig_dump, new_dump)


def compare_specparam_data(orig_yaml, new_yaml):
    """return diff between ZenPackSpecParams-derived YAML files"""
    orig_dump, new_dump = get_specparam_yaml_pair(orig_yaml, new_yaml)
    orig_data = load_yaml_single(orig_dump, loader=OrderedLoader)
    new_data = load_yaml_single(new_dump, loader=OrderedLoader)
    return dict_modified(orig_data, new_data)


def compare_zenpackspecs(orig_yaml, new_yaml):
    """report whether different YAML documents are identical"""
    # apply log verbosity settings
    ZenPackSpecLoader.QUIET = False
    ZenPackSpecLoader.LEVEL = 0
    # data should be unchanged
    if compare_specparam_data(orig_yaml, new_yaml):
        return False
    # dump back out to YAML for comparison
    if compare_specparam_yaml_files(orig_yaml, new_yaml):
        return False
    # our tests have passed
    return True


def dict_modified(d1, d2):
    """return False if the dictionary has been modified"""
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    return any((added, removed, modified))


def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    DEFAULTLOG.warning("ADDED: %s", added)
    DEFAULTLOG.warning("REMOVED: %s", removed)
    DEFAULTLOG.warning("MODIFIED: %s", modified)


def get_optimized_yaml(data):
    """
    return optimized YAML representing ZenPackSpec
    """
    from .Dumper import Dumper

    # set DEFAULTS throughout
    descend_defaults(data)
    # optimized output
    return yaml.dump(data, default_flow_style=False, Dumper=Dumper).replace(
        "!!map", ""
    )


def descend_defaults(input):
    """
    descend YAML dictionary and optimize DEFAULTS
    """
    for k, v in input.items():
        if not isinstance(v, dict):
            continue
        if k == "DEFAULTS":
            continue
        if k in YAML_HAS_DEFAULTS:
            if len(v.keys()) > 1:
                set_defaults(v)
        descend_defaults(v)


def set_defaults(source):
    """
    if dict has multiple entries, look for identical key/value
    pairs and move them to DEFAULTS
    """
    defaults = _initialize_defaults(source)
    # disqualify defaults if not universal
    _disqualify_defaults(defaults, source)
    if not defaults:
        return
    # remove universal parameters from individual spec
    _remove_defaults_from_spec(defaults, source)
    # add defaults to original data
    if "DEFAULTS" in source.keys():
        source["DEFAULTS"].update(defaults)
    else:
        source["DEFAULTS"] = defaults


def _initialize_defaults(source):
    defaults = {}
    for params in source.values():
        if not isinstance(params, dict):
            continue
        for k, v in params.items():
            if isinstance(v, dict):
                continue
            if k not in defaults.keys():
                defaults[k] = v
    return defaults


def _disqualify_defaults(defaults, source):
    for k, v in defaults.items():
        for params in source.values():
            if not isinstance(params, dict):
                continue
            value = params.get(k)
            if v != value and k in defaults.keys():
                defaults.pop(k)


def _remove_defaults_from_spec(defaults, source):
    for params in source.values():
        if not isinstance(params, dict):
            continue
        for k in params.keys():
            if k in defaults.keys():
                params.pop(k)


def writeDataToFile(keywords=None):
    """
    This is a decorator that will save arguments sent to a function.
    It will write to the /tmp directory using the class name, method name
    and write time as the file name.  It depends upon the 'ZPL_DUMP_DATA' env
    variable existing to dump the pickle.  It then passes the args to the
    original function.  Be sure to unset ZPL_DUMP_DATA or you'll see a peck
    of pickles.

    keywords is a list of words that, if a match is found, will cause an
    object to not be pickled.

    usage:
    class test1(object):
        my_password = ''
        my_datasource = ''
        def __init__(self, pw, ds):
            self.my_password = pw
            self.my_datasource = ds

    t1 = test1()

    class foo(object):
        @writeDataToFile()
        def bar1(self, x, y):
            print('x: {}, y: {}'.format(x, y))

        @writeDataToFile(keywords=['my_password', 'my_datasource'])
        def bar2(self, x, y):
            print('testing')

    f = foo()
    f.bar1(1, 2)
    # int(1) and int(2) will be pickled
    f.bar2(t1, 'bar2')
    # t1 will not be pickled, str('bar2') will be pickled

    $ export ZPL_DUMP_DATA=1; python foo.py; unset ZPL_DUMP_DATA
    """
    if keywords is None:
        keywords = []

    def wrap(f):
        def dumper(self, *args, **kwargs):
            import os

            if os.environ.get("ZPL_DUMP_DATA", None):
                _dump_arguments(self, keywords, f, args, kwargs)
            return f(self, *args, **kwargs)

        return dumper

    return wrap


_file_types = (io.TextIOBase, io.BufferedIOBase, io.RawIOBase, io.IOBase)
try:
    import __builtin__  # Only in Python 2
except ImportError:
    pass
else:
    _file_types = _file_types + (__builtin__.file,)


def _dump_arguments(self, keywords, f, args, kwargs):
    import pickle
    import time
    import logging

    words = keywords
    if not isinstance(words, list):
        words = list(words)
    filetime = time.strftime("%H%M%S", time.localtime())
    fname = "_".join((self.__class__.__name__, f.func_name, filetime))
    pathname = os.path.join("/tmp", fname + ".pickle")  # noqa: S108
    with open(pathname, "w") as pkl_file:
        arguments = []
        for thing in args:
            # ignore Logger, file objects, and user
            # defined keywords
            if (
                isinstance(thing, logging.Logger)
                or isinstance(thing, _file_types)
                or any(kw == a for a in dir(thing) for kw in words)
            ):
                continue
            arguments.append(thing)
        for name, thing in kwargs.items():
            # ignore Logger, file objects, and user
            # defined keywords
            if (
                isinstance(thing, logging.Logger)
                or isinstance(thing, _file_types)
                or any(kw == a for a in dir(thing) for kw in words)
            ):
                continue
            arguments.append("{}={}".format(name, thing))
        try:
            pickle.dump(arguments, pkl_file)
        except TypeError:
            pass
        pkl_file.close()
