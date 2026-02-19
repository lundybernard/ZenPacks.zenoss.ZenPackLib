# ZenPackLib: Visual Architecture Reference

## High-Level Component Interactions

### Simplified Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  DEVELOPER'S ZENPACK                                            │
│  ↓ (writes)                                                     │
│  zenpack.yaml (declarative configuration)                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ZENPACKLIB LAYER (lib/)                                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ INTAKE LAYER                                             │   │
│  │ • helpers/utils.load_yaml()                              │   │
│  │ • helpers/loaders (YAML parsing)                         │   │
│  │ Creates: ZenPackSpec instance from YAML dict             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ SPECIFICATION LAYER (spec/)                              │   │
│  │ • ZenPackSpec (orchestrator)                             │   │
│  │ • ClassSpec, RRDTemplateSpec, EventClassSpec, etc.       │   │
│  │ Creates hierarchy; awaits .create() call                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ FACTORY LAYER (factory/)                                 │   │
│  │ • ModelTypeFactory (metaclass)                           │   │
│  │ • DeviceTypeFactory (device specialization)              │   │
│  │ • ComponentTypeFactory (component specialization)        │   │
│  │ Creates dynamic classes with proper MRO                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ BRIDGE LAYER (base/)                                     │   │
│  │ • DeviceBase, ComponentBase                              │   │
│  │ • ModelBase, CatalogBase                                 │   │
│  │ • Wraps Products.ZenModel.* classes                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ADAPTER REGISTRATION LAYER (gsm.py)                      │   │
│  │ • Zuul Info adapters (zuul.py)                           │   │
│  │ • Impact adapters (impact.py)                            │   │
│  │ • DynamicView adapters (dynamicview.py)                  │   │
│  │ • Catalog wrappers (wrapper/)                            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ZENOSS-PRODBIN LAYER                                           │
│                                                                  │
│  • ZODB (object database)                    [persistence]      │
│  • Products.ZenModel (model classes)         [data model]       │
│  • Zope (adapter registry, site manager)     [infrastructure]   │
│  • Products.Zuul (UI/API facades)            [ui/api]           │
│  • Acquisition (object composition)          [composition]      │
│  • ZenPacks.zenoss.Impact (relationships)    [optional]         │
│  • ZenPacks.zenoss.DynamicView (nav)         [optional]         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Dependency Graph

```
External Inputs
        ↓
    zenpack.yaml (YAML configuration file)
        ↓
    ┌───────────────────────────┐
    │ CONFIGURATION LOADING     │
    ├───────────────────────────┤
    │ zenpacklib.py             │ Entry point / CLI
    │ __init__.py               │ ZenPack installation hooks
    │ helpers/utils.py          │ load_yaml() function
    │ helpers/loaders.py        │ YAML OrderedLoader
    │ helpers/Dumper.py         │ YAML serialization
    └───────────────────────────┘
        ↓
    ┌───────────────────────────┐
    │ SPECIFICATION OBJECTS     │
    ├───────────────────────────┤
    │ spec/ZenPackSpec.py       │ Root spec (orchestrator)
    │ spec/Spec.py              │ Abstract base for specs
    │ spec/ClassSpec.py         │ ← Device/Component classes
    │ spec/RRDTemplateSpec.py   │ ← Monitoring templates
    │ spec/EventClassSpec.py    │ ← Event mappings
    │ spec/DeviceClassSpec.py   │ ← Device organizers
    │ ... (other spec types)    │
    └───────────────────────────┘
        ↓ (spec.create() called)
    ┌───────────────────────────┐
    │ FACTORY LAYER             │
    ├───────────────────────────┤
    │ factory/ModelTypeFactory  │ Metaclass (type creator)
    │ factory/DeviceTypeFactory │ Device specialization
    │ factory/ComponentTypeFactory
    └───────────────────────────┘
        ↓ (type() called)
    ┌───────────────────────────┐
    │ BRIDGE LAYER              │
    ├───────────────────────────┤
    │ base/DeviceBase.py        │ Device wrapper
    │ base/ComponentBase.py     │ Component wrapper
    │ base/ModelBase.py         │ Common methods
    │ base/CatalogBase.py       │ Search support
    └───────────────────────────┘
        ↓ (MRO + inheritance)
    ┌───────────────────────────┐
    │ PRODBIN CLASSES           │
    ├───────────────────────────┤
    │ Products.ZenModel.Device  │ Prodbin device
    │ Products.ZenModel.Component
    │ Products.ZenRelations     │ Relationships
    │ ZODB.Persistent          │ Persistence
    │ Acquisition.Implicit      │ Object composition
    └───────────────────────────┘
        ↓ (registrations)
    ┌───────────────────────────┐
    │ ADAPTER REGISTRATION      │
    ├───────────────────────────┤
    │ gsm.py                    │ Zope site manager
    └───────────────────────────┘
        ├─→ zuul.py              → Zuul Info adapters
        ├─→ impact.py            → Impact adapters (optional)
        ├─→ dynamicview.py       → DynamicView adapters (optional)
        └─→ wrapper/             → Catalog wrappers
             ├─ *IndexableWrapper → Search indexing
             ├─ *PathReporter    → Path info
             └─ *FormBuilder     → UI form generation


Runtime Access Paths:
    ↓
    User/External System (UI, API, Monitoring)
        ↓
    ┌───────────────────────────┐
    │ ACCESS LAYER              │
    ├───────────────────────────┤
    │ Zuul facades              │ → Info adapters → Model properties
    │ Impact engine             │ → ImpactDataProvider → Relationships
    │ DynamicView navigator     │ → IDynamicViewRelatable → Relations
    │ Catalog search            │ → IndexableWrapper → Indexed objects
    │ Collectors                │ → getRRDTemplates() → Monitoring
    │ Event processor           │ → EventClassSpec → Event mappings
    └───────────────────────────┘
```

---

## Specification Hierarchy

```
zenpack.yaml (root)
{
  "packages": {...},
  "classes": {
    "MyDevice": {                     ← ClassSpec
      "base": "Device",
      "properties": {...},
      "relationships": [{...}],
      "monitoring_templates": [{...}]
    },
    "MyComponent": {                  ← ClassSpec
      "base": "Component",
      "properties": {...},
      "relationships": [{...}]
    }
  },
  "device_classes": {
    "/Devices/MyType": {              ← DeviceClassSpec
      "templates": [{...}],           ← RRDTemplateSpec
      "zProperties": [{...}]          <- zPropertySpec
    }
  },
  "event_classes": {
    "/Events/Custom": {               ← EventClassSpec
      "mappings": [{...}]             ← EventMappingSpec
    }
  },
  "process_class_organizers": {...},  ← ProcessClassOrganizerSpec
  "link_providers": [...],            ← LinkProviderSpec
  "impact_triggers": [...]            ← ImpactTriggerSpec
}

↓ Each spec instance created (ZenPackSpec.__init__)
↓ Then spec.create() called (ZenPackSpec.create)
↓ Each creates Zope objects in appropriate registry/hierarchy
```

---

## Class Creation & Inheritance Flow

```
ClassSpec in YAML
  {
    "name": "MyComponent",
    "base": "Component",
    "properties": { "serial": "string" }
  }
  
       ↓ ClassSpec.create() called
       ↓
       → ComponentTypeFactory(
           'MyComponent',
           bases=[Component, ComponentBase, ...existing bases...]
         )
       
       ↓ ComponentTypeFactory.__new__() called
       ↓
       → ModelTypeFactory.__new__() called
       ↓
       ├─ Compute merged _relations (from all bases)
       ├─ Create _properties tuple (with 'serial')
       ├─ Create schema fields
       └─ Call type() to create new class
       
       ↓ Result: MyComponent class with MRO:
       ↓
       [MyComponent,
        ComponentBase,              ← ZenPackLib additions
        Component,                  ← Root component class
        Products.ZenModel.DeviceComponent,  ← Prodbin base
        Products.ZenModel.ManagedEntity,    ← Prodbin base
        Acquisition.Implicit,       ← Zope composition
        ZODB.Persistent,            ← Zope persistence
        object]
        
       ↓ Instance created:
       ↓
       device.myComponents.add(MyComponent('myComp'))
       
       ↓ What happens:
       ├─ Object persisted to ZODB (from Persistent)
       ├─ Object gets Acquisition wrappers (from Implicit)
       ├─ Properties initialized (from _properties)
       ├─ Relationships initialized (from _relations)
       └─ Object indexed in catalog (IndexableWrapper)
```

---

## Adapter Registration & Resolution

```
During Installation (ClassSpec.create):
    ↓
    ┌──────────────────────────────────────┐
    │ Create Info adapter (zuul.py)        │
    │ Create Impact adapter (impact.py)    │
    │ Create DynamicView adapter (dv.py)   │
    │ Create Catalog wrapper (wrapper/)    │
    └──────────────────────────────────────┘
    
    ↓
    
    For each adapter:
        ├─ Create adapter class
        │   @implementer(IInfo)
        │   @adapter(IMyComponent)
        │   class MyComponentInfo(InfoBase): ...
        │
        ├─ Register: gsm.registerAdapter(
        │   factory=MyComponentInfo,
        │   required=(IMyComponent,),
        │   provided=IInfo)
        │
        └─ Now in adapter registry


At Runtime (when accessing model):
    ↓
    Zuul/Impact/DynamicView/Catalog code runs
    
    ↓
    
    Needs: adapter = getAdapter(component, IInfo)
    
    ↓
    
    Zope's adapter registry lookup:
    ├─ What type is component?
    │   → MyComponent from factory
    ├─ What interface does MyComponent implement?
    │   → IMyComponent (registered during ClassSpec.create)
    ├─ What adapter is registered for IMyComponent → IInfo?
    │   → MyComponentInfo (registered during ClassSpec.create)
    └─ Return instance of MyComponentInfo wrapping component
    
    ↓
    
    Using adapter: info.name → reads component.name through wrapper
```

---

## Dataflow: From YAML to UI

```
Step 1: Installation
─────────────────────
  ZenPack installed
      ↓
  __init__.py runs
      ↓
  load_yaml('zenpack.yaml')
      ↓
  ZenPackSpec(loaded_dict)
      ↓
  .create() called recursively on all specs
      ↓
  Classes created by factories
      ↓
  Adapters registered in gsm
      ↓
  ZODB updated with new classes


Step 2: Device/Component Creation
──────────────────────────────────
  Admin adds device
      ↓
  Device instance created: Device('device_uid')
      ↓
  ZODB persists it
      ↓
  Acquisition wraps it
      ↓
  IndexableWrapper adapts it
      ↓
  index_object() called
      ↓
  Object added to global_catalog


Step 3: User Views Device in UI
────────────────────────────────
  User clicks device in Zenoss UI
      ↓
  UI calls: GET /api/v1/devices/device_uid
      ↓
  Zuul DeviceFacade processes request
      ↓
  Facade calls: getAdapter(device_instance, IInfo)
      ↓
  Zope looks up: IDevice → IInfo adapter
      ↓
  Returns: DeviceInfo adapter wrapping device
      ↓
  Facade reads properties through adapter
      ↓
  Facade returns JSON: { name: "device1", ... }
      ↓
  UI renders device details page


Step 4: User Searches
──────────────────────
  User enters search: "device1"
      ↓
  Zuul API: catalog.searchResults(text="device1")
      ↓
  Catalog searches indexed fields
      ↓
  Catalog returns matching UIDs
      ↓
  UIDs resolved to objects
      ↓
  Results returned to UI
      ↓
  UI displays search results
```

---

## Memory Layout Example

```
When MyComponent is created:

┌─────────────────────────────────────────────┐
│ MyComponent instance (in ZODB)              │
├─────────────────────────────────────────────┤
│ __class__ = MyComponent (factory-created)   │
│ __dict__ = {                                │
│    'serial': '12345',   ← from _properties  │
│    'device_id': uid,    ← relationship      │
│    '_v_local_relations': computed at class  │
│ }                                           │
├─────────────────────────────────────────────┤
│ inherited from ComponentBase:               │
│    .device()            ← method            │
│    .getStatus()         ← method            │
│    .getRRDTemplates()   ← method            │
├─────────────────────────────────────────────┤
│ inherited from Products.ZenModel.Component: │
│    .componentType()     ← method            │
│    .titleOrId()         ← method            │
│    ._relations          ← tuple (computed)  │
├─────────────────────────────────────────────┤
│ inherited from Acquisition.Implicit:        │
│    __parent__, __name__ ← composition ptrs  │
├─────────────────────────────────────────────┤
│ inherited from ZODB.Persistent:             │
│    _p_oid, _p_jar      ← persistence data   │
└─────────────────────────────────────────────┘

When wrapped for Catalog:
┌─────────────────────────────────────────────┐
│ ComponentIndexableWrapper:                  │
├─────────────────────────────────────────────┤
│ self.context = MyComponent instance ↑       │
│ self.indexed_attrs = ['uid', 'name', ...]  │
│ self.index_object() → adds to global_catalog
└─────────────────────────────────────────────┘

When adapted for Zuul:
┌─────────────────────────────────────────────┐
│ MyComponentInfo (adapter):                  │
├─────────────────────────────────────────────┤
│ self.context = MyComponent instance ↑       │
│ @property def serial → reads context.serial │
│ @property def name → reads context.titleId()│
│ Zope: context.__of__(parent) → Acquisition │
└─────────────────────────────────────────────┘
```

---

## Initialization Sequence Diagram

```
Installation Phase
──────────────────

ZenPack.install()
    ↓
ZenPacks/zenoss/ZenPackLib/__init__.py
    ↓
load_yaml('zenpack.yaml')  [helpers/utils.py]
    ↓
OrderedLoader parses YAML  [helpers/loaders.py]
    ↓
YAMLDict
    ↓
ZenPackSpec.__init__(dict)  [spec/ZenPackSpec.py]
    │
    ├─ ClassSpec.__init__()        [creates ClassSpec instances]
    ├─ DeviceClassSpec.__init__()  [creates spec instances]
    ├─ EventClassSpec.__init__()
    ├─ RRDTemplateSpec.__init__()
    └─ ... (other specs)
    
    [All specs now exist but haven't .create() yet]
    
    ↓
ZenPackSpec.create()  [iterates child specs]
    │
    ├─ ClassSpec.create()
    │   │
    │   └─ ModelTypeFactory()  [creates class]
    │       │
    │       └─ type().__new__()
    │           ├─ Compute _relations
    │           └─ Create new class with MRO
    │
    │       → Register Info adapter (zuul.py)
    │       → Register Impact adapter (impact.py if installed)
    │       → Register DynamicView adapter (dynamicview.py if installed)
    │       → Register IndexableWrapper (wrapper/)
    │       → All registered via gsm.py
    │
    ├─ RRDTemplateSpec.create()  [creates RRD objects]
    ├─ EventClassSpec.create()   [registers event mappings]
    └─ ... (other specs)


Runtime Phase (Objects created later)
──────────────────────────────────────

Device.add(new_device_instance)
    ↓
    Device instance created
    ↓
    Persisted to ZODB
    ↓
    Event: object_added
    ↓
    IndexableWrapper.index_object() called
    ↓
    index_object() adds to global_catalog
    ↓
    Object now searchable/accessible through:
    ├─ Zuul (via Info adapter)
    ├─ Impact (via ImpactDataProvider adapter)
    ├─ DynamicView (via IDynamicViewRelatable adapter)
    └─ Search (via Catalog)
```

---

## File Dependency Tree

```
zenpacklib.py (main entry)
├─ __init__.py
├─ bin/zenpacklib
├─ ... (ZenPack lifecycle code)
│
└─ lib/
    ├─ helpers/
    │   ├─ utils.py
    │   │   └─ depends: loaders.py
    │   ├─ loaders.py
    │   │   └─ depends: PyYAML
    │   └─ ZenPackLibLog.py
    │
    ├─ spec/
    │   ├─ ZenPackSpec.py (orchestrator)
    │   │   └─ depends: ClassSpec, RRDTemplateSpec, EventClassSpec, etc.
    │   ├─ Spec.py (abstract base)
    │   │   └─ depends: (no deps)
    │   ├─ ClassSpec.py
    │   │   └─ depends: factory/*, zuul.py, impact.py, wrapper/*
    │   ├─ RRDTemplateSpec.py
    │   ├─ EventClassSpec.py
    │   └─ ... (other specs)
    │
    ├─ factory/
    │   ├─ ModelTypeFactory.py
    │   │   └─ depends: base/*, Products.ZenModel
    │   ├─ DeviceTypeFactory.py
    │   └─ ComponentTypeFactory.py
    │
    ├─ base/
    │   ├─ Device.py
    │   │   └─ depends: factory/*, Products.ZenModel
    │   ├─ DeviceBase.py
    │   ├─ Component.py
    │   │   └─ depends: factory/*
    │   ├─ ComponentBase.py
    │   ├─ ModelBase.py
    │   └─ CatalogBase.py
    │
    ├─ gsm.py (adapter registry)
    │   └─ depends: zope.component.*
    │
    ├─ zuul.py (Zuul UI)
    │   ├─ depends: Products.Zuul, gsm.py
    │   └─ creates: Info adapters
    │
    ├─ impact.py (Impact)
    │   ├─ depends: ZenPacks.zenoss.Impact (optional)
    │   ├─ depends: gsm.py
    │   └─ creates: ImpactRelationshipDataProvider adapters
    │
    ├─ dynamicview.py (DynamicView)
    │   ├─ depends: ZenPacks.zenoss.DynamicView (optional)
    │   ├─ depends: gsm.py
    │   └─ creates: IDynamicViewRelatable adapters
    │
    ├─ links.py (Link provider)
    │   └─ depends: Products.Zuul.catalog
    │
    ├─ info.py (HW component info)
    ├─ utils.py (utilities)
    ├─ functions.py (public API)
    │
    ├─ wrapper/
    │   ├─ DeviceIndexableWrapper.py
    │   ├─ ComponentIndexableWrapper.py
    │   ├─ ComponentPathReporter.py
    │   └─ ComponentFormBuilder.py
    │
    ├─ params/ (parameter validation)
    ├─ libexec/ (CLI)
    ├─ migrate/ (install hooks)
    ├─ resources/ (templates)
    └─ tests/ (unit tests)
```

---

## Subsystem Integration Points

```
                    ┌─────────────────────────────┐
                    │  Created Model Classes      │
                    │  (from factory/)            │
                    └──────────┬──────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ↓                      ↓                      ↓
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ Zuul UI      │       │ Impact Rels  │       │ DynamicView  │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ Info adapter │       │ ImpactRelProvider    │ IDynamicView │
│ (zuul.py)    │       │ (impact.py)          │ (dv.py)      │
│              │       │  (optional)          │ (optional)   │
│ • Property   │       │ • Relationship        │ • Entity rel │
│   access     │       │   queries             │   queries    │
│ • Schema     │       │ • Impact graph        │ • Navigation │
│   generation │       │   calculation         │   relations  │
│ • Form build │       │ • Criticality comp    │ • View links │
└──────┬───────┘       └──────┬────────────────┘              │
       │                      │                      ┌────────┘
       │                      │                      │
       └──────────────────────┼──────────────────────┤
                              │                      │
                ┌─────────────┴───────────────┐      │
                │ gsm.py (Zope adapter        │      │
                │ registry)                   │      │
                │ • All adapters registered   │      │
                │ • All adapters looked up    │      │
                │   from here                 │      │
                └──────────────────────────────┘      │
                                                      │
                              ┌───────────────────────┘
                              │
                              ↓
                    ┌──────────────────────┐
                    │ Catalog/Search       │
                    ├──────────────────────┤
                    │ IndexableWrapper     │
                    │ (wrapper/*)          │
                    │ • index_object()     │
                    │ • unindex_object()   │
                    │ • global_catalog     │
                    └──────────────────────┘
```

---

## Key Insights

1. **YAML is the source of truth** - Everything starts from zenpack.yaml
2. **Specs are lazy** - ClassSpec instances created during __init__, but classes created during .create()
3. **Factories create classes once** - Not instance factory, but class factory (type factory)
4. **MRO is computed at class creation** - Relationships and methods resolved once, then cached
5. **Adapters are wrappers** - Models stay simple; subsystems access through adapters
6. **Zope registry is central** - All subsystems discovered through gsm.registerAdapter/queryAdapter
7. **Installation vs. runtime** - Two distinct phases with different responsibilities
8. **Optional subsystems** - Impact/DynamicView detected at import time; adapters registered only if available
9. **Catalog is automatic** - IndexableWrapper registered for every model; search happens automatically
10. **Inheritance is key** - Multiple inheritance from ZenPackLib + prodbin enables seamless integration

---

**Last Updated**: February 19, 2026
