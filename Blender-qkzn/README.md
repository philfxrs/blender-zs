# Blender-QKZN

Blender-QKZN 是一款面向 Blender 3.6+ 的中文 AI 助手插件。在 3D 视图的侧边栏中新增 "AI 助手" 面板，可通过中文自然语言命令快速创建模型、应用材质与调整对象位置。插件内置规则解析器，可离线使用；同时也支持自定义 HTTP LLM 接口，扩展更复杂的语义理解。

## 功能特性

- 中文自然语言命令 → Blender 操作计划（Plan）
- 规则解析与可选外部 LLM 解析（HTTP 接口，可配置 API URL / Key / 超时）
- 安全执行器：逐步调用 `bpy.ops`，输出日志并捕获异常
- 内置材质预设（玻璃、金属、木纹、塑料）及常见颜色词识别
- Blender 面板操作：命令输入、启用 LLM、快速跳转首选项、执行/清空按钮
- 单元测试（pytest + mock），覆盖规划器与执行器核心逻辑
- 完整工程化支持：black、ruff、mypy、GitHub Actions CI、打包脚本

## 环境要求

- Blender 3.6 及以上版本
- Python 3.11（用于开发、单元测试与工程脚本）
- 依赖：`pydantic`, `requests`, `pytest`, `black`, `ruff`, `mypy`

## 安装与打包

1. 克隆或下载本仓库：
   ```bash
   git clone <repo-url>
   cd Blender-qkzn
   ```
2. 打包插件：
   ```bash
   python tools/make_zip.py
   ```
   执行成功后会在项目根目录生成 `blender_qkzn.zip`。
3. 打开 Blender，依次点击 `Edit > Preferences > Add-ons > Install...`，选择 `blender_qkzn.zip`，勾选启用插件。

## 使用步骤

1. 在 3D 视图侧边栏（`N` 键）切换到 "AI" 分类，找到 "AI 助手" 面板。
2. 在命令输入框中输入中文指令，例如：
   - “添加一个立方体并应用玻璃材质”
   - “添加一个蓝色球体，移动到 X1 Y-2 Z0.5”
   - “添加一个木纹材质的立方体，再添加一个金属球体”
3. 勾选 “使用 LLM” 可启用外部 LLM 接口（需先在首选项里配置 API URL 与 API Key）。
4. 点击 “执行” 按钮，执行器会逐步完成计划并在状态栏输出执行结果。
5. 如需重置输入，点击 “清空” 按钮。

## 配置外部 LLM

- 在 `Edit > Preferences > Add-ons` 中找到 Blender-QKZN，点击设置按钮。
- 填写 HTTP 接口的 `API URL`、`API Key`（如需）以及超时时间。
- LLM 服务需返回 JSON，包含 `plan` 字段或直接提供步骤数组，每个步骤形如：
  ```json
  {
    "op": "mesh.primitive_cube_add",
    "args": {}
  }
  ```
- 若未配置或调用失败，插件会自动回退到内置规则解析。

## 本地规则解析机制

- 通过正则匹配识别“立方体”“球体”“移动到 X/Y/Z”“玻璃/金属/木纹/塑料材质”等关键语句。
- 颜色词（红、绿、蓝、黄、白、黑、紫、青、品红、橙）会转换为材质颜色。
- 输出的 Plan 由多个步骤组成，依次交由执行器执行。

## 开发与测试

```bash
# 安装开发依赖
pip install .[dev]

# 代码风格检查
make lint

# 运行单元测试
make test

# 快速打包
make zip
```

如需在 Blender 中调试，可将 `Blender-qkzn/addons/blender_qkzn` 目录软链接或复制到 Blender 的 addons 目录，并在脚本编辑器中 `import importlib; import blender_qkzn; importlib.reload(blender_qkzn)`。

## 常见问题

- **Blender 找不到插件？** 请确认安装 zip 后在插件列表勾选启用，并查看 Blender 控制台输出日志。
- **Windows 权限问题？** 确保对 `%APPDATA%/Blender Foundation/Blender/3.6/scripts/addons` 目录具有写入权限。
- **macOS 沙盒提示？** 将插件放入 `~/Library/Application Support/Blender/3.6/scripts/addons`，并给予 Blender 读写权限。
- **Linux 路径？** 使用 `~/.config/blender/3.6/scripts/addons` 目录，或根据发行版具体路径调整。
- **如何接入本地 LLM？** 只需在首选项中设置本地 HTTP 服务地址（如 `http://127.0.0.1:8000/api`），服务需返回符合规范的 JSON。

## 许可证

本项目采用 [MIT License](LICENSE)。欢迎自由使用、修改与分发。
