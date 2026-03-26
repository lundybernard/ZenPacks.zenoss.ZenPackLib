##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016-2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import importlib
import keyword
import os
import re
import sys

from collections import OrderedDict

import yaml

from yaml.constructor import ConstructorError

from ..base.types import Severity
from ..functions import (
    ZENOSS_KEYWORDS,
    JS_WORDS,
    relname_from_classname,
    find_keyword_cls,
)

from .composer import ComposerFromDict
from .ZenPackLibLog import ZPLOG, DEFAULTLOG

# Version dependent import
try:
    # import for PyYAML >= 5.1
    from yaml import FullLoader as YamlLoader
    from yaml.constructor import FullConstructor as YamlConstructor
except ImportError:
    # import for the older version of PyYaml
    from yaml import Loader as YamlLoader
    from yaml.constructor import Constructor as YamlConstructor


class OrderedLoader(YamlLoader):
    """Basic ordered mapping YAML loader.

    This loader doesn't know about ZenPackSpec. It merely maintains the order
    of mappings as they're read from the file.

    """

    def dict_constructor(self, node):
        """constructor for OrderedDict"""
        return OrderedDict(self.construct_pairs(node))


OrderedLoader.add_constructor(
    "tag:yaml.org,2002:map", OrderedLoader.dict_constructor
)
OrderedLoader.add_constructor(
    "tag:yaml.org,2002:omap", OrderedLoader.dict_constructor
)
OrderedLoader.add_constructor("!ZenPackSpec", OrderedLoader.dict_constructor)
OrderedLoader.add_path_resolver("!ZenPackSpec", [])


class ZenPackSpecMixin(object):
    def dict_constructor(self, node):
        """constructor for OrderedDict"""
        return OrderedDict(self.construct_pairs(node))

    def construct_severity(self, node):
        value = node.value
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = str(value)
        Severity.LOG = self.LOG
        sev = Severity(value)
        return sev.orig

    def construct_specsparameters(self, node, spectype):
        """constructor for SpecsParameters"""
        from ..spec.Spec import Spec

        spec_class = {x.__name__: x for x in Spec.get_subclasses()}.get(
            spectype, None
        )

        if not spec_class:
            self.yaml_error(
                ConstructorError(
                    None,
                    None,
                    "Unrecognized Spec class {}".format(spectype),
                    node.start_mark,
                )
            )
            return

        if not isinstance(node, yaml.MappingNode):
            self.yaml_error(
                ConstructorError(
                    None,
                    None,
                    "expected a mapping node, but found {}".format(node.id),
                    node.start_mark,
                )
            )
            return

        param_defs = spec_class.init_params
        specs = OrderedDict()
        for spec_key_node, spec_value_node in node.value:
            try:
                spec_key = str(self.construct_scalar(spec_key_node))
                self.verify_key(
                    spec_class, param_defs, spec_key, spec_key_node.start_mark
                )

            except yaml.MarkedYAMLError as e:
                self.yaml_error(e)

            specs[spec_key] = self.construct_spec(spec_class, spec_value_node)

        return specs

    def construct_spec(self, cls, node):
        """
        Generic constructor for deserializing specs from YAML.   Should be
        the opposite of represent_spec, and works in the same manner (with its
        parsing and validation directed by the init_params of each spec class)
        """
        from ..spec.RRDDatapointSpec import RRDDatapointSpec

        if issubclass(cls, RRDDatapointSpec) and isinstance(
            node, yaml.ScalarNode
        ):
            # Special case- we allow for a shorthand in specifying datapoint
            # specs.
            return {"shorthand": self.construct_scalar(node)}

        # raise an error if this won't parse correctly
        if not isinstance(node, yaml.MappingNode):
            self.yaml_error(
                ConstructorError(
                    None,
                    None,
                    "expected a mapping node, but found {}".format(node.id),
                    node.start_mark,
                )
            )

        # Create new dictionary containing instance parameters.
        # Note the YAML source lines.
        params = {
            "_source_location": "{}: {}-{}".format(
                os.path.basename(node.start_mark.name),
                node.start_mark.line + 1,
                node.end_mark.line + 1,
            )
        }

        # TODO: When deserializing, we should check if required
        # properties are present.

        # dictionary of class initialization parameters
        param_defs = cls.init_params

        extra_params = None
        # map attribute keys to yaml parameters if they differ
        param_name_map = {}
        for key, attributes in param_defs.items():
            yaml_key = attributes.get("yaml_param")
            param_name_map[yaml_key] = key
            # ensure that extra parameters are only defined once
            if attributes.get("type") == "ExtraParams":
                if extra_params:
                    self.yaml_error(
                        ConstructorError(
                            None,
                            None,
                            "Only one ExtraParams parameter may be specified.",
                            node.start_mark,
                        )
                    )
                extra_params = key
                # set this to an empty dict for now
                params[extra_params] = {}

        for key_node, value_node in node.value:
            yaml_key = self.construct_object(key_node)
            # make sure this isn't a reserved keyword
            self.verify_key(cls, param_defs, yaml_key, key_node.start_mark)

            # handle the case of extra parameters
            if yaml_key not in param_name_map:
                if extra_params:
                    # If an 'extra_params' parameter is defined for this spec,
                    # we take all unrecognized paramters and stuff them into
                    # a single parameter, which is a dictonary of "extra"
                    # parameters.
                    #
                    # Note that the values of these extra parameters need to be
                    # scalars, not nested maps or something like that.
                    params[extra_params][yaml_key] = self.construct_object(
                        value_node
                    )
                    continue
                else:
                    self.yaml_error(
                        ConstructorError(
                            None,
                            None,
                            "Unrecognized parameter '{}' found while "
                            "processing {}".format(yaml_key, cls.__name__),
                            key_node.start_mark,
                        )
                    )
                    continue

            key = param_name_map.get(yaml_key)
            if not key:
                self.LOG.error(
                    "No key found for %s in %s", yaml_key, param_name_map
                )

            # default construction
            if value_node.tag == "!ZenPackSpec" and isinstance(
                value_node, yaml.MappingNode
            ):
                self.LOG.debug(
                    "Obsolete tag '!ZenPackSpec' found, changing to "
                    "'tag:yaml.org,2002:map'."
                )
                value_node.tag = "tag:yaml.org,2002:map"

            yaml_value = self.construct_object(value_node)

            # expected type should fall back to string if not given
            expected_type = param_defs.get(key, {}).get("type", "str")

            # override yaml_value if needed
            try:
                # handle badly formatted things like unquoted hex strings
                if expected_type == "str" and not isinstance(yaml_value, str):
                    value_node.value = str(value_node.value)
                    yaml_value = self.construct_python_str(value_node)
                elif expected_type == "float":
                    if isinstance(yaml_value, int):
                        yaml_value = value_node.value = float(value_node.value)
                    elif not isinstance(yaml_value, float):
                        yaml_value = self.construct_yaml_float(value_node)
                elif expected_type.startswith("dict(SpecsParameter("):
                    m = re.match(
                        r"^dict\(SpecsParameter\((.*)\)\)$", expected_type
                    )
                    if m:
                        spectype = m.group(1)
                        if not isinstance(node, yaml.MappingNode):
                            self.yaml_error(
                                ConstructorError(
                                    None,
                                    None,
                                    "expected a mapping node, "
                                    "but found {}".format(node.id),
                                    node.start_mark,
                                )
                            )
                            continue
                        specs = OrderedDict()
                        for spec_key_node, spec_value_node in value_node.value:
                            spec_key = self.construct_python_str(spec_key_node)
                            specs[spec_key] = self.construct_specsparameters(
                                spec_value_node, spectype
                            )
                        yaml_value = specs
                    else:
                        raise Exception(
                            "Unable to determine specs parameter "
                            "type in '{}'".format(expected_type)
                        )

                elif expected_type == "list(class)":
                    classnames = self.construct_sequence(value_node)
                    classes = []
                    for c in classnames:
                        class_ = self.str_to_class(c)
                        if class_ is None:
                            # local reference to a class being defined in
                            # this zenpack.  (ideally we should verify that
                            # the name is valid, but this is not possible
                            # in a one-pass parsing of the yaml).
                            classes.append(c)
                        else:
                            classes.append(class_)
                    # ZPL defines "class" as either a string representing a
                    # class in this definition, or a class object representing
                    # an external class.
                    yaml_value = classes

                elif expected_type == "list(ExtraPath)":
                    if not isinstance(value_node, yaml.SequenceNode):
                        raise ConstructorError(
                            None,
                            None,
                            "expected a sequence node, but found {}".format(
                                value_node.id
                            ),
                            value_node.start_mark,
                        )
                    extra_paths = []
                    for path_node in value_node.value:
                        extra_paths.append(self.construct_sequence(path_node))
                    yaml_value = extra_paths

                elif expected_type == "list(RelationshipSchemaSpec)":
                    schemaspecs = []
                    for s in self.construct_sequence(value_node):
                        schemaspecs.append(self.str_to_relschemaspec(s))
                    yaml_value = schemaspecs

                elif expected_type == "RelationshipSchemaSpec":
                    schemastr = self.construct_python_str(value_node)
                    yaml_value = self.str_to_relschemaspec(schemastr)

                elif expected_type == "Severity":
                    yaml_value = self.construct_severity(value_node)

                elif expected_type == "multiline":
                    yaml_value = self.construct_python_str(value_node)

                elif re.match(r"^SpecsParameter\((.*)\)$", expected_type):
                    m = re.match(r"^SpecsParameter\((.*)\)$", expected_type)
                    if m:
                        spectype = m.group(1)
                        yaml_value = self.construct_specsparameters(
                            value_node, spectype
                        )
                    else:
                        raise Exception(
                            "Unhandled type '{}'".format(expected_type)
                        )
                else:
                    if expected_type != type(yaml_value).__name__:
                        if not isinstance(
                            yaml_value, OrderedDict
                        ) and expected_type not in [
                            "dict(str)",
                            "list(str)",
                            "ZPropertyDefaultValue",
                        ]:
                            self.LOG.warning(
                                "Possible type mismatch for %s: %s: "
                                "expected: %s got: %s",
                                key,
                                yaml_value,
                                expected_type,
                                type(yaml_value).__name__,
                            )
            except ConstructorError as e:
                self.yaml_error(e)
            except Exception as e:
                self.yaml_error(
                    ConstructorError(
                        None,
                        None,
                        "Unable to deserialize {} object (param {}): "
                        "{}".format(cls.__name__, key_node.value, e),
                        value_node.start_mark,
                    ),
                    exc_info=sys.exc_info(),
                )

            params[key] = yaml_value

        return params

    def construct_zenpackspec(self, node):
        """"""
        log_name = self.find_name_from_node()
        if log_name:
            self.LOG = ZPLOG.add_log(
                log_name, quiet=self.QUIET, level=self.LEVEL
            )

        from ..spec.ZenPackSpec import ZenPackSpec

        params = self.construct_spec(ZenPackSpec, node)
        params["zplog"] = self.LOG
        name = params.pop("name")

        fatal = not getattr(self, "warnings", False)
        yaml_errored = getattr(self, "yaml_errored", False)

        try:
            return ZenPackSpec(name, **params)
        except Exception as e:
            if yaml_errored and not fatal:
                self.LOG.error("(possibly because of earlier errors) %s", e)
            else:
                raise

        return None

    def construct_relschemaspec(self, node):
        """"""
        schemastr = str(self.construct_scalar(node))
        return self.str_to_relschemaspec(schemastr)

    def str_to_class(self, classstr):
        if classstr == "object":
            return object

        if "." not in classstr:
            # TODO: Support non qualfied class names, searching zenpack,
            # zenpacklib, and ZenModel namespaces

            # An unqualified class name is assumed to be referring to one in
            # the classes defined in this ZenPackSpec.   We can't validate
            # this, or return a class object for it, if this is the case.
            # So we return no class object, and the caller will assume that
            # it refers to a class being defined.
            return None

        modname, classname = classstr.rsplit(".", 1)
        # ensure that 'zenpacklib' refers to *this* zenpacklib, if more than
        # one is loaded in the system.
        if modname in [
            "zenpacklib",
            "ZenPacks.zenoss.ZenPackLib.lib.factory.ModelTypeFactory",
        ]:
            modname = "ZenPacks.zenoss.ZenPackLib.zenpacklib"
        try:
            class_ = getattr(importlib.import_module(modname), classname)
        except Exception as e:
            raise ValueError("Class '{}' is not valid: {}".format(classstr, e))

        return class_

    _schema_search = re.compile(
        r"^\s*(?P<left>\S+)"
        r"\s+(?P<cardinality>1:1|1:M|1:MC|M:M)"
        r"\s+(?P<right>\S+)\s*$",
    ).search

    _class_rel_search = re.compile(
        r"(\((?P<pre_relname>[^\)\s]+)\))?"
        r"(?P<class>[^\(\s]+)"
        r"(\((?P<post_relname>[^\)\s]+)\))?"
    ).search

    _reltypes = {
        "1:1": ("ToOne", "ToOne"),
        "1:M": ("ToMany", "ToOne"),
        "1:MC": ("ToManyCont", "ToOne"),
        "M:M": ("ToMany", "ToMany"),
    }

    def str_to_relschemaspec(self, schemastr):
        m = self._schema_search(schemastr)
        if not m:
            raise ValueError(
                "RelationshipSchemaSpec '{}' is not valid".format(schemastr)
            )

        ml = self._class_rel_search(m.group("left"))
        if not ml:
            raise ValueError(
                "RelationshipSchemaSpec '{}' left side is not valid".format(
                    m.group("left")
                )
            )

        mr = self._class_rel_search(m.group("right"))
        if not mr:
            raise ValueError(
                "RelationshipSchemaSpec '{}' right side is not valid".format(
                    m.group("right")
                )
            )

        left_class = ml.group("class")
        right_class = mr.group("class")
        left_type = self._reltypes.get(m.group("cardinality"))[0]
        right_type = self._reltypes.get(m.group("cardinality"))[1]

        left_relname = ml.group("pre_relname") or ml.group("post_relname")
        if left_relname is None:
            left_relname = relname_from_classname(
                right_class, plural=left_type != "ToOne"
            )

        right_relname = mr.group("pre_relname") or mr.group("post_relname")
        if right_relname is None:
            right_relname = relname_from_classname(
                left_class, plural=right_type != "ToOne"
            )

        return {
            "left_class": left_class,
            "left_relname": left_relname,
            "left_type": left_type,
            "right_type": right_type,
            "right_class": right_class,
            "right_relname": right_relname,
        }

    _severity_values_map = {
        "crit": 5,
        "critical": 5,
        "err": 4,
        "error": 4,
        "warn": 3,
        "warning": 3,
        "info": 2,
        "information": 2,
        "informational": 2,
        "debug": 1,
        "debugging": 1,
        "clear": 0,
    }

    def str_to_severity(self, value):
        """
        Return numeric severity given a string representation of severity.
        """
        try:
            severity = int(value)
        except (TypeError, ValueError):
            severity = self._severity_values_map.get(value.lower())

        if severity is None:
            raise ValueError(
                "'{}' is not a valid value for severity.".format(value)
            )

        return severity

    def format_message(self, e):
        message = []

        mark = e.context_mark or e.problem_mark
        if mark:
            position = "{}:{}:{}".format(
                mark.name, mark.line + 1, mark.column + 1
            )
        else:
            position = "[unknown]"
        if e.context is not None:
            message.append(e.context)

        if e.problem is not None:
            message.append(e.problem)

        if e.note is not None:
            message.append("(note: {})".format(e.note))

        return "{}: {}".format(position, message)

    def yaml_warning(self, e):
        # Given a MarkedYAMLError exception, either log or raise
        # the error, depending on the 'fatal' argument.
        self.LOG.warning(self.format_message(e))

    def yaml_error(self, e, exc_info=None):
        # Given a MarkedYAMLError exception, either log or raise
        # the error, depending on the 'fatal' argument.
        fatal = not getattr(self, "warnings", False)
        self.yaml_errored = True
        if exc_info:
            # When we're given the original exception (which was wrapped in
            # a MarkedYAMLError), we can provide more context for debugging.
            from traceback import format_exception

            e.note = "\nOriginal exception:\n{}".format(
                "".join(format_exception(*exc_info))
            )
        if fatal:
            raise e
        self.LOG.error(self.format_message(e))

    def verify_key(self, cls, params, key, start_mark):
        # always ok to use a param name (description, name, etc.)
        if key in params.keys():
            return True
        # never use a python reserved word
        if key in keyword.kwlist:
            self.yaml_error(
                ConstructorError(
                    None,
                    None,
                    "Found reserved keyword '{}' while processing {}".format(
                        key, cls.__name__
                    ),
                    start_mark,
                )
            )
        elif key in ZENOSS_KEYWORDS.union(JS_WORDS):
            # should be ok to use a zenoss word to define these
            # some items, like sysUpTime are pretty common datapoints
            if cls.__name__ not in [
                "RRDDatasourceSpec",
                "RRDDatapointSpec",
                "RRDTemplateSpec",
                "GraphDefinitionSpec",
                "GraphPointSpec",
            ]:
                klasses = ", ".join(find_keyword_cls(key))
                self.yaml_warning(
                    ConstructorError(
                        None,
                        None,
                        "Found reserved Zenoss keyword '{}' from {}".format(
                            key, klasses
                        ),
                        start_mark,
                    )
                )
        return False

    def find_name_from_node(self):
        """determine zenpack name"""
        for k in self.recursive_objects.keys():
            for v in k.value:
                if isinstance(v, tuple) and len(v) == 2:
                    key, value = str(v[0].value), str(v[1].value)
                    if key == "name":
                        return value
        return None


class ZenPackSpecLoader(ZenPackSpecMixin, OrderedLoader):
    """
    These subclasses exist so that each copy of zenpacklib installed on a
    zenoss system provide their own loader (for add_constructor and yaml.load)
    and its own dumper (for add_representer) so that the proper methods will
    be used for this specific zenpacklib.
    """

    LOG = DEFAULTLOG
    QUIET = False
    LEVEL = 0

    def __init__(self, *args, **kwargs):
        OrderedLoader.__init__(self, *args, **kwargs)


ZenPackSpecLoader.add_constructor(
    "tag:yaml.org,2002:seq", ZenPackSpecLoader.construct_sequence
)

ZenPackSpecLoader.add_constructor(
    "!ZenPackSpec", ZenPackSpecLoader.construct_zenpackspec
)


class FromDictLoader(ComposerFromDict, YamlConstructor):
    def __init__(self, dataDict, tag):
        ComposerFromDict.__init__(self, dataDict, tag)
        YamlConstructor.__init__(self)


class ZenPackSpecFromDictLoader(ZenPackSpecMixin, FromDictLoader):
    LOG = DEFAULTLOG
    QUIET = False
    LEVEL = 0

    def __init__(self, *args, **kwargs):
        kwargs["tag"] = "!ZenPackSpec"
        FromDictLoader.__init__(self, *args, **kwargs)

    def construct_bool(self, node):
        return node.value

    def construct_existing(self, node):
        return node.value

    def construct_object(self, node, deep=True):
        return FromDictLoader.construct_object(self, node, deep=deep)

    # def construct_document(self, node):
    #     return self.construct_object(node, deep=True)


ZenPackSpecFromDictLoader.add_constructor(
    "tag:yaml.org,2002:seq", ZenPackSpecFromDictLoader.construct_sequence
)
ZenPackSpecFromDictLoader.add_constructor(
    "!ZenPackSpec", ZenPackSpecFromDictLoader.construct_zenpackspec
)
ZenPackSpecFromDictLoader.add_constructor(
    "tag:yaml.org,2002:bool", ZenPackSpecFromDictLoader.construct_bool
)
ZenPackSpecFromDictLoader.add_constructor(
    "tag:yaml.org,2002:int", ZenPackSpecFromDictLoader.construct_existing
)
ZenPackSpecFromDictLoader.add_constructor(
    "tag:yaml.org,2002:float", ZenPackSpecFromDictLoader.construct_existing
)


class WarningLoader(ZenPackSpecLoader):
    """
    These subclasses exist so that each copy of zenpacklib installed on a
    zenoss system provide their own loader (for add_constructor and yaml.load)
    and its own dumper (for add_representer) so that the proper methods will
    be used for this specific zenpacklib.
    """

    warnings = True
    yaml_errored = False


yaml.add_path_resolver("!ZenPackSpec", [], Loader=ZenPackSpecLoader)
