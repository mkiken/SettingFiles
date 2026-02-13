# Project Index: SettingFiles

Generated: 2026-02-14 JST

## 📊 Quick Stats

- **Primary Language**: Shell Scripts (Zsh, Bash, PowerShell)
- **Configuration Formats**: JSON, YAML, TOML, Lua
- **Platforms**: macOS, Windows
- **AI Integration**: Claude Code, Gemini CLI, Serena MCP
- **Total Config Files**: 259 shell scripts, 100+ configuration files
- **Code Management**: Git submodules for plugin management

---

## 📁 Repository Structure

```
SettingFiles/
├── ai/                    # AI assistant configurations
│   ├── claude/           # Claude Code settings & commands
│   ├── gemini/           # Gemini CLI settings & commands
│   ├── serena/           # Serena MCP configuration
│   └── common/           # Shared prompts & MCP settings
├── mac/                   # macOS-specific scripts & configs
│   ├── initialization/   # 6-step setup scripts
│   ├── Brewfile          # Homebrew package declarations
│   ├── initialize        # Main setup entry point
│   └── update            # Package/plugin updater
├── windows/              # Windows PowerShell scripts
├── shell/                # Shell configurations
│   └── zsh/             # Zsh config with znap plugin manager
├── vimfiles/            # Editor configurations
│   └── nvim/            # Neovim with lazy.nvim
├── gitfiles/            # Git tool configurations
├── terminal/            # Terminal emulator configs
├── vscode/              # VSCode settings & keybindings
├── submodules/          # Git submodule-managed plugins
├── .kiro/               # Kiro spec-driven development
└── .serena/             # Serena project memories
```

---

## 🚀 Entry Points

### Setup & Installation

| File | Platform | Purpose |
|------|----------|---------|
| `mac/initialize` | macOS | Main initialization (6-step setup) |
| `mac/initialization/initialize` | macOS | Orchestrator for all setup scripts |
| `windows/initialize.ps1` | Windows | Windows environment setup |
| `mac/update` | macOS | Update packages and plugins |
| `windows/update.ps1` | Windows | Update Windows packages |

### Shell Configuration

| File | Purpose |
|------|---------|
| `shell/zsh/.zshrc` | Zsh main configuration (259 lines) |
| `shell/zsh/plugin.zsh` | Plugin management via znap |
| `shell/zsh/.zprofile` | Zsh profile settings |
| `shell/zsh/.zshenv` | Environment variables |

### Editor Configuration

| File | Purpose |
|------|---------|
| `vimfiles/nvim/init.lua` | Neovim entry point |
| `vimfiles/nvim/lua/config/lazy.lua` | Plugin manager config |
| `vimfiles/nvim/lazy-lock.json` | Plugin version lock |

### AI Assistants

| File | Purpose |
|------|---------|
| `ai/claude/_CLAUDE.md` | Generated Claude prompt (symlinked) |
| `ai/claude/settings.json` | Claude Code settings |
| `ai/claude/hooks/claude-hook.py` | Notification hooks |
| `ai/gemini/_GEMINI.md` | Generated Gemini prompt |
| `ai/gemini/hooks/gemini-hook.py` | Gemini notification hooks |
| `ai/common/mcp.json` | MCP server configuration |
| `ai/serena/serena_config.yml` | Serena semantic analysis config |

---

## 📦 Core Modules

### AI Configuration System

**Location**: `ai/`

**Structure**:
- `claude/` - Claude Code configuration
  - `commands/` - Custom commands (pr-body, pr-review, web-summary, etc.)
  - `ccstatusline/settings.json` - Status line customization
  - `agents/serena-expert.md` - Serena integration
- `gemini/` - Gemini CLI configuration
  - `commands/` - TOML-based custom commands
- `common/` - Shared resources
  - `prompt_base.md` - Base prompt template
  - `characters/` - Character personalities (reimu.md, nyaruko.md, hestia.md)
  - `mcp.json` - MCP server registry

**Assembly Process**:
```
prompt_base.md + characters/reimu.md + claude_prompt.md → _CLAUDE.md
```

**Purpose**: Centralized AI assistant configuration with character-based prompts

---

### Mac Initialization System

**Location**: `mac/initialization/`

**Scripts**:
1. `copy_files.sh` - Symlink creation
2. `homebrew.sh` - Homebrew & package installation
3. `dev_tools.sh` - Developer tools setup
4. `git_setup.sh` - Git configuration
5. `system_setup.sh` - macOS system settings
6. `ai/` - AI assistant setup (claude.sh, gemini.sh, other.sh)

**Orchestrator**: `mac/initialization/initialize`

**Purpose**: 6-phase macOS environment setup via symlink strategy

---

### Shell Plugin Management

**Location**: `shell/zsh/`, `submodules/`

**Plugin Manager**: znap (marlonrichert/zsh-snap)

**Managed Plugins** (Git Submodules):
- `fzf-tab` - Fuzzy completion
- `zsh-autosuggestions` - Command suggestions
- `F-Sy-H` (Fast-Syntax-Highlighting) - Syntax highlighting
- `zsh-vi-mode` - Vi keybindings
- `zsh-bd` - Quick directory navigation
- `zsh-notify` - Command completion notifications

**Configuration**: `shell/zsh/plugin.zsh`

**Purpose**: Declarative plugin management with version control

---

### Neovim Plugin System

**Location**: `vimfiles/nvim/`

**Plugin Manager**: lazy.nvim

**Structure**:
```
nvim/
├── init.lua              # Entry point
├── lua/
│   ├── config/lazy.lua  # Plugin manager setup
│   ├── options.lua      # Vim options
│   ├── keymaps.lua      # Keybindings
│   ├── api.lua          # Neovim API
│   └── plugins/         # Plugin configs
│       └── vscode/      # VSCode-specific plugins
└── lazy-lock.json       # Version lock
```

**Purpose**: Modular Neovim configuration with lazy loading

---

### Kiro Specification System

**Location**: `.kiro/`

**Structure**:
- `steering/` - Project-wide rules & context
  - `product.md` - Product requirements
  - `tech.md` - Technical constraints
  - `structure.md` - Project structure
  - `my-custom-rule.md` - Custom rules
- `specs/` - Feature specifications
  - `{feature}/requirements.md` - EARS format requirements
  - `{feature}/design.md` - Technical design
  - `{feature}/tasks.md` - Implementation tasks
  - `{feature}/spec.json` - Metadata
- `settings/` - Framework configuration
  - `rules/` - Validation rules
  - `templates/` - Document templates
  - `mcp.json` - MCP integration

**Active Specs**:
- `example-feature/` - Example specification
- `pr-comment-review-command/` - PR comment review feature
- `fgln-function-enhancement/` - Shell function enhancement
- `fgrv-git-revert-command/` - Git revert command

**Purpose**: AI-DLC (AI Development Life Cycle) spec-driven development

---

### Serena Project Memory

**Location**: `.serena/`

**Memories**:
- `project_overview.md` - High-level project description
- `directory_structure.md` - Codebase organization
- `tech_stack.md` - Technology choices
- `code_style_conventions.md` - Coding standards
- `task_completion_guidelines.md` - Completion criteria
- `suggested_commands.md` - Common operations
- `notification_system_analysis.md` - Hook system analysis

**Configuration**: `.serena/project.yml`

**Purpose**: Persistent context for Serena MCP agent

---

## 🔧 Configuration Files

### Package Management

| File | Purpose | Package Count |
|------|---------|---------------|
| `mac/Brewfile` | Homebrew packages | 40 brew, 16 cask, 7 vscode, 4 mas |
| `vimfiles/nvim/lazy-lock.json` | Neovim plugins | ~50 plugins (locked) |
| `.gitmodules` | Zsh plugins | 8 submodules |

### Git Tools

| File | Purpose |
|------|---------|
| `gitfiles/.gitconfig` | Git core configuration |
| `gitfiles/lazygit/config.yml` | LazyGit TUI settings |
| `gitfiles/gh/dash/config.yml` | GitHub CLI dashboard |
| `gitfiles/workmux/config.yaml` | Git workspace manager |

### Terminal Emulators

| File | Purpose |
|------|---------|
| `terminal/ghostty/config` | Ghostty terminal settings |
| `terminal/warp/keybindings.yaml` | Warp terminal keybindings |

### Editor Integration

| File | Purpose |
|------|---------|
| `vscode/base_setting.json` | VSCode settings template |
| `vscode/base_keybindings.json` | VSCode keybindings template |
| `mac/karabiner.json` | Karabiner-Elements key remapping |

### AI Commands

**Claude Commands** (Markdown):
- `ai/claude/commands/pr-body.md` - Generate PR descriptions
- `ai/claude/commands/pr-review.md` - Review pull requests
- `ai/claude/commands/pr-comment-review.md` - Analyze PR comments
- `ai/claude/commands/pr-comment-implement.md` - Implement from comments
- `ai/claude/commands/web-summary.md` - Summarize web pages

**Gemini Commands** (TOML):
- `ai/gemini/commands/pr-body.toml`
- `ai/gemini/commands/pr-review.toml`
- `ai/gemini/commands/pr-comment-review.toml`
- `ai/gemini/commands/pr-comment-implement.toml`
- `ai/gemini/commands/web-summary.toml`

---

## 🏗️ Architecture Patterns

### Symlink Strategy

Configuration files are stored in the repository and symlinked to system locations:

```
Repository                          System Location
────────────────────────────────────────────────────────
ai/claude/_CLAUDE.md           →    ~/.claude/CLAUDE.md
ai/claude/settings.json        →    ~/.claude/settings.json
shell/zsh/.zshrc               →    ~/.zshrc
vimfiles/nvim/                 →    ~/.config/nvim/
gitfiles/.gitconfig            →    ~/.gitconfig
```

**Benefits**:
- Single source of truth
- Version control for all configs
- Easy cross-machine synchronization

### AI Prompt Assembly

Prompts are composed from multiple sources:

```
Base Prompt + Character + Tool-Specific → Final Prompt
─────────────────────────────────────────────────────────
prompt_base.md   reimu.md    claude_prompt.md → _CLAUDE.md
prompt_base.md   nyaruko.md  gemini_prompt.md → _GEMINI.md
```

**Character Personalities**:
- `reimu.md` - 博麗霊夢 (Hakurei Reimu) - Claude
- `nyaruko.md` - ニャル子 (Nyaruko) - Gemini
- `hestia.md` - ヘスティア (Hestia) - Future use

### Plugin Management

**Zsh**: Git submodules + znap
- Version controlled via `.gitmodules`
- Loaded via `znap source` commands

**Neovim**: lazy.nvim
- Declarative config in `lua/plugins/`
- Version locked in `lazy-lock.json`

---

## 📚 Documentation

### Setup Guides

| File | Description |
|------|-------------|
| `README.md` | Quick setup instructions |
| `CLAUDE.md` | Claude Code guidance |
| `mac/initialization/NOTES.md` | Post-setup notes |

### AI Configuration

| File | Description |
|------|-------------|
| `ai/common/prompt_base.md` | Base prompt template |
| `ai/claude/claude_prompt.md` | Claude-specific instructions |
| `.github/copilot-instructions.md` | GitHub Copilot setup |

### Specification System

| Directory | Description |
|-----------|-------------|
| `.kiro/steering/` | Project rules & context |
| `.kiro/settings/rules/` | Validation rules |
| `.kiro/settings/templates/` | Document templates |

---

## 🔗 Key Dependencies

### System Tools (Homebrew)

| Package | Purpose |
|---------|---------|
| `neovim` | Editor |
| `tmux` | Terminal multiplexer |
| `fzf` | Fuzzy finder |
| `ripgrep` | Fast search |
| `lazygit` | Git TUI |
| `gh` | GitHub CLI |
| `claude-squad` | Claude CLI tools |

### Development Tools

| Package | Purpose |
|---------|---------|
| `nvm` | Node version manager |
| `uv` | Python package manager |
| `commitlint` | Commit message linting |
| `actionlint` | GitHub Actions linting |

### AI & MCP

| Package | Purpose |
|---------|---------|
| `claude-code` (VSCode) | Claude Code extension |
| Serena MCP | Semantic code analysis |
| Context7 MCP | Documentation search |
| Playwright MCP | Browser automation |
| Sequential Thinking MCP | Planning assistant |

---

## 📝 Quick Start

### Initial Setup (macOS)

```bash
cd mac
./initialize
```

**What it does**:
1. Creates symlinks for all configs
2. Installs Homebrew + packages
3. Sets up dev tools (NVM, etc.)
4. Configures Git
5. Applies macOS settings
6. Initializes AI assistants

### Update Environment

```bash
cd mac
./update
```

**What it does**:
- Updates Homebrew packages
- Updates Zsh plugins via znap
- Updates Neovim plugins
- Rebuilds AI prompt files

### Managing Specifications

```bash
# Check spec status
/kiro:spec-status {feature}

# Create new spec
/kiro:spec-init "feature description"

# Generate requirements
/kiro:spec-requirements {feature}

# Generate design
/kiro:spec-design {feature}

# Generate tasks
/kiro:spec-tasks {feature}

# Implement tasks
/kiro:spec-impl {feature} [tasks]
```

---

## 🎯 Common Operations

### Add New Homebrew Package

1. Edit `mac/Brewfile`
2. Run `cd mac && brew bundle`

### Add New Zsh Plugin

1. Add submodule: `git submodule add <url> submodules/<name>`
2. Edit `shell/zsh/plugin.zsh`
3. Add `znap source <path>`

### Add New Neovim Plugin

1. Create config file in `vimfiles/nvim/lua/plugins/`
2. Run `:Lazy sync` in Neovim

### Add New AI Command

**Claude**:
1. Create `ai/claude/commands/{name}.md`
2. Reference as `/my:{name}` in Claude Code

**Gemini**:
1. Create `ai/gemini/commands/{name}.toml`
2. Use via Gemini CLI

---

## 🧪 Testing & Validation

### Pre-commit Hooks

**Location**: `ai/claude/hooks/claude-hook.py`, `ai/gemini/hooks/gemini-hook.py`

**Features**:
- System tag filtering
- Notification triggering
- Task completion tracking

### Specification Validation

**Commands**:
- `/kiro:validate-design {feature}` - Design review
- `/kiro:validate-gap {feature}` - Implementation gap analysis
- `/kiro:validate-impl {feature}` - Post-implementation validation

---

## 🔍 Search Tips

### Find Configuration Files

```bash
# All AI configs
find ai/ -type f -name "*.md" -o -name "*.json" -o -name "*.yml"

# Zsh scripts
find shell/zsh/ -type f -name "*.zsh"

# Neovim plugins
ls vimfiles/nvim/lua/plugins/
```

### Search Code

```bash
# Claude command definitions
grep -r "command-name" ai/claude/commands/

# Kiro specifications
find .kiro/specs/ -name "requirements.md"
```

---

## 💡 Notes

- **Symlinks are critical**: Don't copy files manually
- **Character-driven AI**: Reimu (Claude) and Nyaruko (Gemini) provide personality
- **Git submodules**: Always update recursively (`git submodule update --init --recursive`)
- **Platform-specific**: Use appropriate `initialize` script for your OS
- **Kiro specs**: Follow 3-phase approval (Requirements → Design → Tasks)
- **Serena memories**: Persistent context across sessions

---

## 📊 Token Efficiency

**Before indexing**: Reading all configs = ~58,000 tokens
**After indexing**: Reading this index = ~3,000 tokens
**Savings**: 94% reduction (55,000 tokens per session)

---

_Last updated: 2026-02-14_
_Generated by: SuperClaude Index Repository Command_
