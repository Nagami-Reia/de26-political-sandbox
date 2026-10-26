# 从这里开始

下载 `00_FULL_PORTABLE_APP.zip` 即可获得完整的 Hakoniwa。

解压后先读 `AI_START_HERE.md`。最小检查命令：

```bash
python3 -m hakoniwa validate --pretty
python3 -m hakoniwa actors
python3 -m hakoniwa scenarios
```

十个 ZIP 本次都已重新生成；不能只上传新增文件，因为原有核心代码、
人物卡、制度规则、场景、测试和文档也都有修改。旧的 `kfrage_model`
包名已由 `hakoniwa` 替代，K-Frage 2024 仅作为 legacy calibration 保留。
