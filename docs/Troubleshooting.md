# 故障排查

## Blender 未找到

在 `config.toml` 的 `[tools].blender_path` 配置 `E:/blender/blender.exe`。

## 团结引擎 Gate D 未运行

确认 `[tools].tuanjie_path` 指向 `Tuanjie.exe`，验证项目目录可写且没有正在打开的同名批处理项目。

## UVPackmaster 未安装

这是正常情况。TopoFlow 默认使用 Blender Native Smart UV Project，不要求购买插件。

## Gate A/B/C 失败

系统会自动调整目标面数、UV 间距或烘焙参数并重试两次。仍失败时查看 `report.json` 的 `errors` 和 `repair_attempt`。

## 中文路径乱码

第三方工具建议安装到纯英文目录，例如 `D:\Unity`、`D:\TopoFlowApp`。模型输出可使用中文文件名，但外部工具目录尽量避免中文。

## Web UI ResourceWarning

Python 3.13 与当前 Gradio 退出时可能报告未关闭事件循环警告，不影响实际运行和输出。

