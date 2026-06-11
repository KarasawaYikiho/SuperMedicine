# OpenCode Alignment Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align SuperMedicine's architecture and structure with OpenCode's proven patterns while preserving domain-specific medical research capabilities.

**Architecture:** Adopt OpenCode's modular package structure, effect-based core, and plugin system while maintaining SuperMedicine's microkernel architecture and medical domain focus.

**Tech Stack:** TypeScript (OpenCode) vs Python (SuperMedicine) - maintain Python implementation but adopt structural patterns.

---

## 1. Structure Comparison

### OpenCode Structure
```
opencode/
├── packages/                    # Monorepo with multiple packages
│   ├── core/                    # Core functionality
│   │   ├── src/                 # Source code
│   │   │   ├── account/         # Account management
│   │   │   ├── config/          # Configuration
│   │   │   ├── database/        # Database layer
│   │   │   ├── effect/          # Effect system
│   │   │   ├── event/           # Event system
│   │   │   ├── filesystem/      # File operations
│   │   │   ├── permission/      # Permission system
│   │   │   ├── plugin/          # Plugin system
│   │   │   ├── session/         # Session management
│   │   │   ├── tool/            # Tool system
│   │   │   └── ...              # Other modules
│   │   ├── migration/           # Database migrations
│   │   ├── script/              # Scripts
│   │   └── test/                # Tests
│   ├── cli/                     # CLI interface
│   ├── tui/                     # Terminal UI
│   ├── web/                     # Web interface
│   ├── desktop/                 # Desktop app
│   ├── sdk/                     # SDK
│   ├── plugin/                  # Plugin system
│   └── ...                      # Other packages
├── specs/                       # Specifications
├── infra/                       # Infrastructure
└── script/                      # Build scripts
```

### SuperMedicine Structure
```
SuperMedicine/
├── core/                        # Microkernel core
│   ├── config_center.py         # Configuration
│   ├── event_bus.py             # Event system
│   ├── kernel.py                # Kernel
│   ├── llm_client.py            # LLM client
│   ├── session_manager.py       # Session management
│   └── ...                      # Other modules
├── agents/                      # Agent orchestration
│   ├── base_agent.py            # Base agent
│   ├── orchestrator.py          # Orchestrator
│   └── state_machine.py         # State machine
├── plugins/                     # Plugin system
│   ├── base_plugin.py           # Base plugin
│   ├── rag/                     # RAG plugins
│   ├── harness/                 # Harness plugins
│   ├── tools/                   # Tool plugins
│   └── standards/               # Standards plugins
├── adapters/                    # Platform adapters
│   ├── base_adapter.py          # Base adapter
│   ├── opencode/                # OpenCode adapter
│   ├── claude_code/             # Claude Code adapter
│   └── standalone/              # Standalone adapter
├── permission/                  # Permission system
├── tests/                       # Tests
└── ...                          # Other files
```

## 2. Architecture Comparison

### OpenCode's Brain→Planner→Coder→Tester Chain
OpenCode uses a sophisticated agent orchestration system:
- **Brain**: Central dispatcher that routes tasks
- **Planner**: Creates execution plans
- **Coder**: Implements code changes
- **Tester**: Verifies implementations

### SuperMedicine's Kernel→Plugin System
SuperMedicine uses a microkernel architecture:
- **Kernel**: Central coordinator with ConfigCenter, EventBus, PluginRegistry
- **Agents**: Alpha (Analyst), Beta (Reviewer), Gamma (Writer), Delta (Orchestrator)
- **Plugins**: RAG, harness, tools, standards
- **Adapters**: OpenCode, Claude Code, standalone

### Key Differences
1. **Language**: TypeScript vs Python
2. **Architecture**: Effect-based vs Microkernel
3. **Agent System**: 4-agent role-based vs Brain→Planner→Coder→Tester chain
4. **Plugin System**: Package-based vs Manifest-based
5. **State Management**: Effect-based vs Event-driven

## 3. Gap Analysis

### Critical Gaps (Must Address)
1. **Missing Effect System**: OpenCode uses Effect-TS for functional programming
2. **Incomplete Agent Chain**: SuperMedicine lacks Brain→Planner→Coder→Tester pattern
3. **Database Layer**: No structured database like OpenCode's Drizzle ORM
4. **Package Structure**: Not modular enough for independent packages
5. **Type Safety**: Less strict typing than OpenCode's TypeScript

### Important Gaps (Should Address)
1. **Tool System**: OpenCode has more sophisticated tool management
2. **Session Management**: OpenCode has more advanced session handling
3. **Permission System**: OpenCode has more granular permissions
4. **Plugin Discovery**: OpenCode has more robust plugin system
5. **Testing Infrastructure**: OpenCode has better test organization

### Minor Gaps (Nice to Have)
1. **Documentation Structure**: OpenCode has better docs organization
2. **Build System**: OpenCode has more sophisticated build pipeline
3. **Desktop App**: SuperMedicine lacks desktop application
4. **Web Interface**: SuperMedicine lacks web interface
5. **SDK**: SuperMedicine lacks SDK for external integration

## 4. Migration Plan

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Establish modular package structure

#### Task 1.1: Create Package Structure
- [ ] **Step 1: Create packages directory**
  ```bash
  mkdir -p packages/{core,cli,tui,web,plugin,sdk}
  ```

- [ ] **Step 2: Move core functionality**
  ```bash
  mv core/* packages/core/src/
  mv agents/* packages/core/src/agent/
  mv permission/* packages/core/src/permission/
  ```

- [ ] **Step 3: Create package.json files**
  ```json
  // packages/core/package.json
  {
    "name": "@supermedicine/core",
    "version": "0.4.2",
    "main": "src/index.py",
    "dependencies": {}
  }
  ```

- [ ] **Step 4: Update imports**
  ```python
  # Before
  from core.config_center import ConfigCenter
  
  # After
  from packages.core.src.config_center import ConfigCenter
  ```

#### Task 1.2: Implement Effect System
- [ ] **Step 1: Create effect module**
  ```python
  # packages/core/src/effect/__init__.py
  from .effect import Effect
  from .runtime import Runtime
  from .layer import Layer
  ```

- [ ] **Step 2: Implement basic Effect class**
  ```python
  # packages/core/src/effect/effect.py
  from typing import TypeVar, Generic, Callable, Any
  from dataclasses import dataclass
  
  T = TypeVar('T')
  E = TypeVar('E')
  
  @dataclass
  class Effect(Generic[T, E]):
      success: bool
      value: T | None = None
      error: E | None = None
      
      @staticmethod
      def succeed(value: T) -> 'Effect[T, Any]':
          return Effect(success=True, value=value)
      
      @staticmethod
      def fail(error: E) -> 'Effect[Any, E]':
          return Effect(success=False, error=error)
      
      def map(self, f: Callable[[T], Any]) -> 'Effect[Any, E]':
          if self.success:
              return Effect.succeed(f(self.value))
          return self
      
      def flat_map(self, f: Callable[[T], 'Effect[Any, E]']) -> 'Effect[Any, E]':
          if self.success:
              return f(self.value)
          return self
  ```

- [ ] **Step 3: Integrate with existing code**
  ```python
  # Update core modules to use Effect
  from packages.core.src.effect import Effect
  
  def risky_operation() -> Effect[Result, Error]:
      try:
          result = perform_operation()
          return Effect.succeed(result)
      except Exception as e:
          return Effect.fail(Error(str(e)))
  ```

### Phase 2: Agent System (Weeks 3-4)
**Goal**: Implement Brain→Planner→Coder→Tester chain

#### Task 2.1: Create Agent Chain
- [ ] **Step 1: Create agent base classes**
  ```python
  # packages/core/src/agent/base.py
  from abc import ABC, abstractmethod
  from typing import Any
  from packages.core.src.effect import Effect
  
  class Agent(ABC):
      @abstractmethod
      def execute(self, task: str) -> Effect[Any, str]:
          pass
  ```

- [ ] **Step 2: Implement Brain agent**
  ```python
  # packages/core/src/agent/brain.py
  from .base import Agent
  from .planner import Planner
  from .coder import Coder
  from .tester import Tester
  
  class Brain(Agent):
      def __init__(self):
          self.planner = Planner()
          self.coder = Coder()
          self.tester = Tester()
      
      def execute(self, task: str) -> Effect[Any, str]:
          # Route task to appropriate agent
          if self._needs_planning(task):
              return self.planner.execute(task)
          elif self._needs_coding(task):
              return self.coder.execute(task)
          elif self._needs_testing(task):
              return self.tester.execute(task)
          else:
              return Effect.fail("Unknown task type")
  ```

- [ ] **Step 3: Implement Planner agent**
  ```python
  # packages/core/src/agent/planner.py
  from .base import Agent
  from packages.core.src.effect import Effect
  
  class Planner(Agent):
      def execute(self, task: str) -> Effect[Any, str]:
          # Create execution plan
          plan = self._create_plan(task)
          return Effect.succeed(plan)
  ```

- [ ] **Step 4: Implement Coder agent**
  ```python
  # packages/core/src/agent/coder.py
  from .base import Agent
  from packages.core.src.effect import Effect
  
  class Coder(Agent):
      def execute(self, task: str) -> Effect[Any, str]:
          # Implement code changes
          result = self._implement_code(task)
          return Effect.succeed(result)
  ```

- [ ] **Step 5: Implement Tester agent**
  ```python
  # packages/core/src/agent/tester.py
  from .base import Agent
  from packages.core.src.effect import Effect
  
  class Tester(Agent):
      def execute(self, task: str) -> Effect[Any, str]:
          # Run tests
          result = self._run_tests(task)
          return Effect.succeed(result)
  ```

#### Task 2.2: Update Orchestrator
- [ ] **Step 1: Refactor orchestrator**
  ```python
  # packages/core/src/agent/orchestrator.py
  from .brain import Brain
  from packages.core.src.effect import Effect
  
  class Orchestrator:
      def __init__(self):
          self.brain = Brain()
      
      def process_request(self, request: str) -> Effect[Any, str]:
          return self.brain.execute(request)
  ```

- [ ] **Step 2: Update state machine**
  ```python
  # packages/core/src/agent/state_machine.py
  from enum import Enum
  from typing import Dict, Any
  
  class AgentState(Enum):
      IDLE = "idle"
      PLANNING = "planning"
      DISPATCH = "dispatch"
      RUNNING = "running"
      VERIFYING = "verifying"
      COMPLETED = "completed"
      FAILED = "failed"
  
  class StateMachine:
      def __init__(self):
          self.state = AgentState.IDLE
          self.transitions: Dict[AgentState, Dict[str, AgentState]] = {
              AgentState.IDLE: {"start": AgentState.PLANNING},
              AgentState.PLANNING: {"plan_created": AgentState.DISPATCH},
              AgentState.DISPATCH: {"dispatched": AgentState.RUNNING},
              AgentState.RUNNING: {"completed": AgentState.VERIFYING, "failed": AgentState.FAILED},
              AgentState.VERIFYING: {"verified": AgentState.COMPLETED, "failed": AgentState.RETRY},
              AgentState.RETRY: {"retry": AgentState.PLANNING, "max_retries": AgentState.FAILED},
          }
      
      def transition(self, action: str) -> bool:
          if action in self.transitions.get(self.state, {}):
              self.state = self.transitions[self.state][action]
              return True
          return False
  ```

### Phase 3: Plugin System (Weeks 5-6)
**Goal**: Enhance plugin system with package-based approach

#### Task 3.1: Create Plugin Package Structure
- [ ] **Step 1: Create plugin packages**
  ```bash
  mkdir -p packages/plugin/{rag,harness,tools,standards}
  ```

- [ ] **Step 2: Move existing plugins**
  ```bash
  mv plugins/rag/* packages/plugin/rag/
  mv plugins/harness/* packages/plugin/harness/
  mv plugins/tools/* packages/plugin/tools/
  mv plugins/standards/* packages/plugin/standards/
  ```

- [ ] **Step 3: Create plugin interface**
  ```python
  # packages/plugin/base.py
  from abc import ABC, abstractmethod
  from typing import Any, Dict
  from packages.core.src.effect import Effect
  
  class Plugin(ABC):
      @abstractmethod
      def name(self) -> str:
          pass
      
      @abstractmethod
      def version(self) -> str:
          pass
      
      @abstractmethod
      def execute(self, **kwargs) -> Effect[Any, str]:
          pass
  ```

#### Task 3.2: Implement Plugin Discovery
- [ ] **Step 1: Create plugin registry**
  ```python
  # packages/core/src/plugin/registry.py
  import importlib
  import pkgutil
  from typing import Dict, Type
  from packages.plugin.base import Plugin
  
  class PluginRegistry:
      def __init__(self):
          self.plugins: Dict[str, Plugin] = {}
      
      def discover_plugins(self, package_name: str) -> None:
          package = importlib.import_module(package_name)
          for importer, modname, ispkg in pkgutil.walk_packages(
              path=package.__path__,
              prefix=package.__name__ + '.'
          ):
              try:
                  module = importlib.import_module(modname)
                  for attr_name in dir(module):
                      attr = getattr(module, attr_name)
                      if (isinstance(attr, type) and 
                          issubclass(attr, Plugin) and 
                          attr is not Plugin):
                          plugin_instance = attr()
                          self.plugins[plugin_instance.name()] = plugin_instance
              except Exception as e:
                  print(f"Failed to load plugin {modname}: {e}")
      
      def get_plugin(self, name: str) -> Plugin | None:
          return self.plugins.get(name)
  ```

- [ ] **Step 2: Update kernel to use plugin registry**
  ```python
  # packages/core/src/kernel.py
  from .plugin.registry import PluginRegistry
  
  class Kernel:
      def __init__(self):
          self.plugin_registry = PluginRegistry()
          self.plugin_registry.discover_plugins('packages.plugin')
      
      def execute_plugin(self, plugin_name: str, **kwargs):
          plugin = self.plugin_registry.get_plugin(plugin_name)
          if plugin:
              return plugin.execute(**kwargs)
          return Effect.fail(f"Plugin {plugin_name} not found")
  ```

### Phase 4: Database Layer (Weeks 7-8)
**Goal**: Add structured database layer

#### Task 4.1: Implement Database Layer
- [ ] **Step 1: Create database module**
  ```python
  # packages/core/src/database/__init__.py
  from .database import Database
  from .repository import Repository
  ```

- [ ] **Step 2: Implement database class**
  ```python
  # packages/core/src/database/database.py
  import sqlite3
  from typing import Any, Dict, List, Optional
  from pathlib import Path
  
  class Database:
      def __init__(self, db_path: str = "supermedicine.db"):
          self.db_path = db_path
          self.connection = None
      
      def connect(self) -> None:
          self.connection = sqlite3.connect(self.db_path)
          self.connection.row_factory = sqlite3.Row
      
      def disconnect(self) -> None:
          if self.connection:
              self.connection.close()
      
      def execute(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
          cursor = self.connection.cursor()
          cursor.execute(query, params)
          self.connection.commit()
          return [dict(row) for row in cursor.fetchall()]
      
      def create_tables(self) -> None:
          # Create necessary tables
          self.execute("""
              CREATE TABLE IF NOT EXISTS sessions (
                  id TEXT PRIMARY KEY,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  data JSON
              )
          """)
          
          self.execute("""
              CREATE TABLE IF NOT EXISTS agents (
                  id TEXT PRIMARY KEY,
                  type TEXT,
                  state TEXT,
                  session_id TEXT,
                  FOREIGN KEY (session_id) REFERENCES sessions(id)
              )
          """)
          
          self.execute("""
              CREATE TABLE IF NOT EXISTS plugins (
                  name TEXT PRIMARY KEY,
                  version TEXT,
                  enabled BOOLEAN DEFAULT TRUE
              )
          """)
  ```

- [ ] **Step 3: Create repository pattern**
  ```python
  # packages/core/src/database/repository.py
  from abc import ABC, abstractmethod
  from typing import Any, Dict, List, Optional
  from .database import Database
  
  class Repository(ABC):
      def __init__(self, database: Database):
          self.database = database
      
      @abstractmethod
      def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
          pass
      
      @abstractmethod
      def find_all(self) -> List[Dict[str, Any]]:
          pass
      
      @abstractmethod
      def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
          pass
      
      @abstractmethod
      def update(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
          pass
      
      @abstractmethod
      def delete(self, id: str) -> bool:
          pass
  ```

### Phase 5: Testing Infrastructure (Weeks 9-10)
**Goal**: Improve testing infrastructure

#### Task 5.1: Create Test Structure
- [ ] **Step 1: Create test directories**
  ```bash
  mkdir -p packages/core/test/{unit,integration,e2e}
  mkdir -p packages/plugin/test
  mkdir -p packages/agent/test
  ```

- [ ] **Step 2: Create test utilities**
  ```python
  # packages/core/test/utils.py
  import pytest
  from typing import Any, Dict
  from packages.core.src.effect import Effect
  
  class TestUtils:
      @staticmethod
      def assert_effect_success(effect: Effect, expected_value: Any = None) -> None:
          assert effect.success is True
          if expected_value is not None:
              assert effect.value == expected_value
      
      @staticmethod
      def assert_effect_failure(effect: Effect, expected_error: str = None) -> None:
          assert effect.success is False
          if expected_error is not None:
              assert effect.error == expected_error
      
      @staticmethod
      def create_mock_plugin(name: str, version: str = "1.0.0") -> 'Plugin':
          from packages.plugin.base import Plugin
          
          class MockPlugin(Plugin):
              def name(self) -> str:
                  return name
              
              def version(self) -> str:
                  return version
              
              def execute(self, **kwargs) -> Effect[Any, str]:
                  return Effect.succeed(f"Executed {name}")
          
          return MockPlugin()
  ```

- [ ] **Step 3: Create test fixtures**
  ```python
  # packages/core/test/conftest.py
  import pytest
  from packages.core.src.kernel import Kernel
  from packages.core.src.database.database import Database
  
  @pytest.fixture
  def kernel():
      return Kernel()
  
  @pytest.fixture
  def database():
      db = Database(":memory:")
      db.connect()
      db.create_tables()
      yield db
      db.disconnect()
  ```

#### Task 5.2: Implement Unit Tests
- [ ] **Step 1: Test effect system**
  ```python
  # packages/core/test/unit/test_effect.py
  import pytest
  from packages.core.src.effect import Effect
  
  class TestEffect:
      def test_succeed(self):
          effect = Effect.succeed("value")
          assert effect.success is True
          assert effect.value == "value"
          assert effect.error is None
      
      def test_fail(self):
          effect = Effect.fail("error")
          assert effect.success is False
          assert effect.value is None
          assert effect.error == "error"
      
      def test_map_success(self):
          effect = Effect.succeed(5)
          mapped = effect.map(lambda x: x * 2)
          assert mapped.success is True
          assert mapped.value == 10
      
      def test_map_failure(self):
          effect = Effect.fail("error")
          mapped = effect.map(lambda x: x * 2)
          assert mapped.success is False
          assert mapped.error == "error"
      
      def test_flat_map_success(self):
          effect = Effect.succeed(5)
          flat_mapped = effect.flat_map(lambda x: Effect.succeed(x + 1))
          assert flat_mapped.success is True
          assert flat_mapped.value == 6
      
      def test_flat_map_failure(self):
          effect = Effect.fail("error")
          flat_mapped = effect.flat_map(lambda x: Effect.succeed(x + 1))
          assert flat_mapped.success is False
          assert flat_mapped.error == "error"
  ```

- [ ] **Step 2: Test agent system**
  ```python
  # packages/core/test/unit/test_agent.py
  import pytest
  from packages.core.src.agent.brain import Brain
  from packages.core.src.agent.planner import Planner
  from packages.core.src.agent.coder import Coder
  from packages.core.src.agent.tester import Tester
  
  class TestAgentSystem:
      def test_brain_creation(self):
          brain = Brain()
          assert brain.planner is not None
          assert brain.coder is not None
          assert brain.tester is not None
      
      def test_planner_execution(self):
          planner = Planner()
          result = planner.execute("Create a plan")
          assert result.success is True
      
      def test_coder_execution(self):
          coder = Coder()
          result = coder.execute("Implement feature")
          assert result.success is True
      
      def test_tester_execution(self):
          tester = Tester()
          result = tester.execute("Run tests")
          assert result.success is True
  ```

### Phase 6: Documentation (Weeks 11-12)
**Goal**: Improve documentation structure

#### Task 6.1: Create Documentation Structure
- [ ] **Step 1: Create docs directory**
  ```bash
  mkdir -p docs/{api,guides,examples}
  ```

- [ ] **Step 2: Create API documentation**
  ```markdown
  # docs/api/README.md
  
  # SuperMedicine API Documentation
  
  ## Core Modules
  
  ### Effect System
  - `Effect[T, E]`: Functional error handling
  - `Runtime`: Effect execution runtime
  - `Layer`: Dependency injection layer
  
  ### Agent System
  - `Brain`: Central dispatcher
  - `Planner`: Execution planning
  - `Coder`: Code implementation
  - `Tester`: Verification
  
  ### Plugin System
  - `Plugin`: Base plugin interface
  - `PluginRegistry`: Plugin discovery
  - `Kernel`: Core coordinator
  ```

- [ ] **Step 3: Create user guides**
  ```markdown
  # docs/guides/getting-started.md
  
  # Getting Started with SuperMedicine
  
  ## Installation
  
  ```bash
  pip install supermedicine
  ```
  
  ## Basic Usage
  
  ```python
  from packages.core.src.kernel import Kernel
  
  kernel = Kernel()
  result = kernel.process_request("Analyze medical paper")
  ```
  
  ## Configuration
  
  Create `config.yaml`:
  ```yaml
  llm:
    provider: openai
    api_key: ${OPENAI_API_KEY}
  
  plugins:
    rag:
      enabled: true
    harness:
      enabled: true
  ```
  ```

## 5. Effort Estimates

### Phase 1: Foundation (Weeks 1-2)
- **Effort**: 2 weeks (80 hours)
- **Resources**: 1 developer
- **Risk**: Medium (structural changes)

### Phase 2: Agent System (Weeks 3-4)
- **Effort**: 2 weeks (80 hours)
- **Resources**: 1 developer
- **Risk**: High (core functionality)

### Phase 3: Plugin System (Weeks 5-6)
- **Effort**: 2 weeks (80 hours)
- **Resources**: 1 developer
- **Risk**: Medium (plugin compatibility)

### Phase 4: Database Layer (Weeks 7-8)
- **Effort**: 2 weeks (80 hours)
- **Resources**: 1 developer
- **Risk**: Low (new functionality)

### Phase 5: Testing Infrastructure (Weeks 9-10)
- **Effort**: 2 weeks (80 hours)
- **Resources**: 1 developer
- **Risk**: Low (testing improvements)

### Phase 6: Documentation (Weeks 11-12)
- **Effort**: 2 weeks (80 hours)
- **Resources**: 1 developer
- **Risk**: Low (documentation)

### Total Effort
- **Duration**: 12 weeks
- **Total Hours**: 480 hours
- **Resources**: 1 developer full-time
- **Risk Assessment**: Medium overall risk

## 6. Implementation Priorities

### High Priority (Must Have)
1. Package structure alignment
2. Effect system implementation
3. Agent chain implementation
4. Plugin system enhancement

### Medium Priority (Should Have)
1. Database layer
2. Testing infrastructure
3. Documentation structure
4. Build system improvements

### Low Priority (Nice to Have)
1. Desktop application
2. Web interface
3. SDK development
4. Advanced tooling

## 7. Success Metrics

### Technical Metrics
1. **Code Coverage**: >80% test coverage
2. **Type Safety**: 100% type annotations
3. **Performance**: <100ms response time for core operations
4. **Reliability**: <1% error rate in production

### Quality Metrics
1. **Documentation**: 100% API documentation
2. **User Experience**: <5 minute setup time
3. **Maintainability**: <10 minutes to fix bugs
4. **Extensibility**: <1 hour to add new plugins

### Business Metrics
1. **User Adoption**: 100 active users within 3 months
2. **Community Growth**: 50 contributors within 6 months
3. **Feature Completeness**: 90% feature parity with OpenCode
4. **Performance**: 2x improvement in research效率

## 8. Risk Mitigation

### Technical Risks
1. **Breaking Changes**: Maintain backward compatibility
2. **Performance Issues**: Profile and optimize critical paths
3. **Integration Problems**: Comprehensive integration testing
4. **Security Vulnerabilities**: Regular security audits

### Resource Risks
1. **Developer Burnout**: Realistic timelines and scope
2. **Skill Gaps**: Training and knowledge sharing
3. **Tooling Issues**: Invest in development tools
4. **External Dependencies**: Minimize external dependencies

### Schedule Risks
1. **Scope Creep**: Strict scope management
2. **Timeline Pressure**: Buffer time for unexpected issues
3. **Dependency Delays**: Parallel work where possible
4. **Quality Compromise**: Never sacrifice quality for speed

## 9. Next Steps

### Immediate Actions (This Week)
1. [ ] Review and approve this plan
2. [ ] Set up development environment
3. [ ] Create package structure
4. [ ] Begin Phase 1 implementation

### Short-term (Next 2 Weeks)
1. [ ] Complete package restructuring
2. [ ] Implement basic effect system
3. [ ] Create agent base classes
4. [ ] Set up testing framework

### Medium-term (Next Month)
1. [ ] Complete agent chain implementation
2. [ ] Enhance plugin system
3. [ ] Add database layer
4. [ ] Improve documentation

### Long-term (Next Quarter)
1. [ ] Achieve feature parity with OpenCode
2. [ ] Optimize performance
3. [ ] Build community
4. [ ] Release stable version

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-10-opencode-alignment.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**