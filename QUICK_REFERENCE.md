# ZenPackLib Quick Reference Guide

## Module Directory Structure

```
lib/
├── __init__.py                      # Namespace package
│
├── base/                            ← BRIDGE LAYER
│   ├── Device.py                    # Device root class
│   ├── DeviceBase.py                # Device method extensions
│   ├── Component.py                 # Component base class
│   ├── ComponentBase.py             # Component method extensions
│   ├── ModelBase.py                 # Common model methods
│   └── CatalogBase.py               # Catalog/search support
│
├── factory/                         ← FACTORY LAYER
│   ├── ModelTypeFactory.py          # Base factory (type metaclass)
│   ├── DeviceTypeFactory.py         # For device classes
│   └── ComponentTypeFactory.py      # For component classes
│
├── spec/                            ← SPECIFICATION LAYER
│   ├── ZenPackSpec.py               # Root spec orchestrator
│   ├── Spec.py                      # Abstract spec base
│   ├── ClassSpec.py                 # Device/component definitions
│   ├── DeviceClassSpec.py           # Device organizers
│   ├── EventClassSpec.py            # Event mappings
│   ├── ProcessClassOrganizerSpec.py # Process monitoring
│   ├── LinkProviderSpec.py          # Link providers
│   ├── ImpactTriggerSpec.py         # Impact relationships
│   ├── RRDTemplateSpec.py           # Monitoring templates
│   ├── RRDDatasourceSpec.py         # Data sources
│   ├── RRDDatapointSpec.py          # Data points
│   └── ...                          # Other spec types
│
├── helpers/                         ← CONFIGURATION LOADING
│   ├── utils.py                     # load_yaml(), merge configs
│   ├── loaders.py                   # YAML OrderedLoader
│   ├── Dumper.py                    # YAML serialization
│   └── ZenPackLibLog.py             # Logging
│
├── wrapper/                         ← CATALOG/ZUUL WRAPPERS
│   ├── DeviceIndexableWrapper.py    # Device search indexing
│   ├── ComponentIndexableWrapper.py # Component search indexing
│   ├── ComponentPathReporter.py     # Path info adapter
│   └── ComponentFormBuilder.py      # UI form generation
│
├── gsm.py                           ← ADAPTER REGISTRATION HUB
├── zuul.py                          ← ZUUL UI INTEGRATION
├── info.py                          ← INFO ADAPTER REGISTRATION
├── impact.py                        ← IMPACT SUBSYSTEM ADAPTER
├── dynamicview.py                   ← DYNAMICVIEW SUBSYSTEM ADAPTER
├── links.py                         ← DEVICE LINK PROVIDERS
├── utils.py                         ← UTILITY FUNCTIONS
├── functions.py                     ← PUBLIC API
├── params/                          ← PARAMETER VALIDATION
├── libexec/                         ← CLI IMPLEMENTATION
│   └── ZPLCommand.py
├── resources/                       ← STATIC RESOURCES
├── migrate/                         ← MIGRATION/INSTALL SCRIPTS
└── tests/                           ← UNIT TESTS
```

## Layer Responsibilities

### Bridge Layer (base/)

**What it does**: Wraps zenoss-prodbin classes and adds ZenPackLib-specific methods

**Key Classes**:

- `DeviceBase` - Adds methods like `getStatus()`, `getRRDTemplates()`
- `ComponentBase` - Adds methods like `device()`, type checking
- `ModelBase` - Common methods: `getProduct()`, `getIcon()`
- `CatalogBase` - Catalog/search support

**Integration**: Inherits from `Products.ZenModel.*` classes

---

### Factory Layer (factory/)

**What it does**: Dynamically creates classes at runtime with proper inheritance

**Key Classes**:

- `ModelTypeFactory` - Metaclass that creates new types
  - Computes `_relations` from bases
  - Generates schema properties
  - Uses Python's `type()` builtin

- `DeviceTypeFactory` - Specializes for device classes
- `ComponentTypeFactory` - Specializes for component classes

**Integration**: Creates classes that inherit from both ZenPackLib bases + prodbin

---

### Specification Layer (spec/)

**What it does**: Converts declarative YAML to Zope objects

**Architecture**:

```
ZenPackSpec (root)
├── ClassSpec (models)
├── DeviceClassSpec (/Devices/... hierarchy)
├── EventClassSpec (event mappings)
├── ProcessClassOrganizerSpec (process monitoring)
├── RRDTemplateSpec (monitoring templates)
│   ├── RRDDatasourceSpec
│   └── RRDDatapointSpec
├── LinkProviderSpec
└── ImpactTriggerSpec
```

**Key Method**: `.create()` - Called on each spec to materialize declarations

---

### Adapter Registration (gsm.py)

**What it does**: Registers Zope adapters for subsystem integration

**Registered Adapters**:

1. **Zuul Info Adapter** - UI access to model properties
2. **Impact Adapter** - Relationship data provider
3. **DynamicView Adapter** - Navigation relationships
4. **Indexable Wrapper** - Catalog indexing
5. **Path Reporter** - Component path info

**Integration Point**: Used by `zuul.py`, `impact.py`, `dynamicview.py`, `wrapper/*`

---

### Subsystem Adapters

#### zuul.py (Zuul UI)

- Creates `InfoBase` subclass for each model
- Registers Info adapter in Zope
- Provides field definitions for forms
- Enables UI access to model properties

#### impact.py (Impact Relationships)

- Creates `IImpactRelationshipDataProvider` adapter
- Only if `ZenPacks.zenoss.Impact` installed
- Returns component relationships for impact graph

#### dynamicview.py (DynamicView Navigation)

- Creates `IDynamicViewRelatable` adapter
- Only if `ZenPacks.zenoss.DynamicView` installed
- Provides entity relations for dynamic navigation

#### links.py (Device Linking)

- Implements `ILinkProvider` interface
- Enables linking between devices
- Integrates with link catalog

---

## Data Flow Cheat Sheet

### Installation (One-time)

```
zenpack.yaml
  → load_yaml()
  → ZenPackSpec.__init__()
  → spec.create()
  → ModelTypeFactory()
  → Class created
  → Adapters registered
```

### Runtime Access

```
User action
  → Zuul API
  → Adapter lookup (gsm.py)
  → Model instance
  → Property access
  → MRO resolution
  → UI display
```

### Search

```
Model instance created
  → IndexableWrapper wraps it
  → index_object() called
  → Added to global_catalog
  → User searches
  → Catalog results
  → Objects displayed
```

### Impact

```
Impact engine starts
  → Queries model
  → ImpactRelationshipDataProvider adapter
  → Returns _relations
  → Calculates graph
  → Updates UI
```

---

## Key Design Decisions

| Decision                                   | Why                                               | Where                                     |
| ------------------------------------------ | ------------------------------------------------- | ----------------------------------------- |
| **YAML over code**                         | Simpler for operators; no Python knowledge needed | `helpers/utils.py`                        |
| **Dynamic class creation**                 | No boilerplate; proper inheritance with type()    | `factory/ModelTypeFactory.py`             |
| **\_relations computed at class creation** | Thread-safe, cached, immutable                    | `factory/ModelTypeFactory.py`             |
| **Zope adapters for subsystems**           | Loose coupling; optional subsystem support        | `gsm.py`                                  |
| **Specification pattern**                  | Declarative vs. imperative; testable              | `spec/Spec.py`                            |
| **MRO via multiple inheritance**           | Natural Python; no explicit routing needed        | `base/` layer                             |
| **Conditional imports**                    | Works with/without Impact/DynamicView             | `utils.py`, `impact.py`, `dynamicview.py` |

---

## Common Code Patterns

### Pattern 1: Define a Model in YAML

```yaml
classes:
  MyDevice:
    base: Device
    properties:
      customProp:
        type: string
        default: value
    relationships:
      - name: myComponents
        cardinality: M:N
        class: MyComponent
  MyComponent:
    base: Component
    monitoring_templates:
      - MyTemplate
```

### Pattern 2: Access Model in Code

```python
from ZenPacks.zenoss.myzenpack.MyPack import MyDevice, MyComponent

device = MyDevice('device_uid')
component = device.myComponents()[0]
status = device.getStatus()  # From DeviceBase
properties = device.customProp  # From _properties
```

### Pattern 3: Adapter Lookup

```python
from zope.component import getAdapter
from Products.Zuul.interfaces import IInfo

model_instance = ...  # Device/Component
info = getAdapter(model_instance, IInfo)  # Zope looks up registered adapter
print(info.name)  # Zuul info facade access
```

### Pattern 4: Register Custom Adapter

```python
from zope.component import getGlobalSiteManager
from zope.interface import implementer

@implementer(IMyCustomInterface)
class MyAdapter:
    def __init__(self, context):
        self.context = context

gsm = getGlobalSiteManager()
gsm.registerAdapter(MyAdapter)  # Register for components of context's type
```

---

## Troubleshooting Checklist

| Issue                            | Check                                                                            |
| -------------------------------- | -------------------------------------------------------------------------------- |
| Model class not found            | Is `ClassSpec.create()` being called? Check ZenPackSpec instantiation            |
| UI form not showing properties   | Is Info adapter registered? Check `zuul.py` and `gsm.py`                         |
| Search not finding objects       | Is IndexableWrapper registered? Check `wrapper/ComponentIndexableWrapper.py`     |
| Impact relationships missing     | Is `ZenPacks.zenoss.Impact` installed? Check conditional import in `impact.py`   |
| Monitoring templates not applied | Is `getRRDTemplates()` returning templates? Check `DeviceBase.getRRDTemplates()` |
| Relationships broken             | Are `_relations` computed correctly? Check factory `_compute_relations()`        |
| Events not classifying           | Is `EventClassSpec.create()` called? Check event mappings in `spec/`             |

---

## Files to Examine First

For different goals:

**Understanding Overall Architecture**:

1. `__init__.py` - ZenPack lifecycle entry point
2. `lib/spec/ZenPackSpec.py` - Root spec orchestrator
3. `lib/factory/ModelTypeFactory.py` - Class creation engine
4. `lib/base/DeviceBase.py` - Bridge abstraction

**Understanding Zuul Integration**:

1. `lib/zuul.py` - Info adapter creation
2. `lib/gsm.py` - Adapter registration
3. `lib/wrapper/DeviceIndexableWrapper.py` - Search indexing

**Understanding Subsystem Integration**:

1. `lib/impact.py` - Impact adapter
2. `lib/dynamicview.py` - DynamicView adapter
3. `lib/links.py` - Link provider

**Understanding Configuration Loading**:

1. `lib/helpers/utils.py` - load_yaml() function
2. `lib/helpers/loaders.py` - YAML loader customization
3. `lib/spec/ClassSpec.py` - Class specification parsing

---

## Quick API Reference

### Top-Level Functions (lib/functions.py)

```python
# Load and process ZenPack specification
from ZenPacks.zenoss.ZenPackLib.lib.functions import load_zenpack_configuration

config = load_zenpack_configuration('path/to/zenpack.yaml')
```

### Key Classes

```python
# Access created classes
from ZenPacks.zenoss.myzenpack.MyPack import MyDevice, MyComponent

# Access base classes for extension
from ZenPacks.zenoss.ZenPackLib.lib.base import DeviceBase, ComponentBase

# Access specifications
from ZenPacks.zenoss.ZenPackLib.lib.spec import ClassSpec, ZenPackSpec
```

### Adapter Access

```python
from zope.component import queryAdapter
from Products.Zuul.interfaces import IInfo

# Get Info adapter for model
info = queryAdapter(model_instance, IInfo)
if info:
    form_fields = info.getFields()
```

---

## Version & Dependency Map

| Component           | Dependency                     | Required? | Notes                 |
| ------------------- | ------------------------------ | --------- | --------------------- |
| Core Framework      | PyYAML                         | Yes       | YAML parsing          |
| Core Framework      | Zope                           | Yes       | Object/adapter system |
| Core Framework      | ZODB                           | Yes       | Persistence           |
| Core Framework      | Products.ZenModel              | Yes       | Zenoss model classes  |
| Zuul Integration    | Products.Zuul                  | Yes       | UI/API integration    |
| Search/Catalog      | Products.Zuul.catalog          | Yes       | Search indexing       |
| Impact Support      | ZenPacks.zenoss.Impact         | No        | Optional subsystem    |
| DynamicView Support | ZenPacks.zenoss.DynamicView    | No        | Optional subsystem    |
| Process Monitoring  | Products.ZenModel.ProcessClass | No        | Optional feature      |
| Job Scheduling      | Products.Jobber                | No        | Optional feature      |

---

**Last Updated**: February 19, 2026
