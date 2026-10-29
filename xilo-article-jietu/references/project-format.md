# 项目清单与坐标

`editor.py create` 接收 UTF-8 JSON。这里只说明结构；每次执行的文章、图片和个人资料保存到执行项目，不放进 Skill。

```json
{
  "title": "文章截图精修",
  "images": [
    {
      "path": "/absolute/path/screenshot.png",
      "kind": "screenshot",
      "evidence": "用户说明为应用实拍截图",
      "context": "原文：在底部输入任务，并添加资料。",
      "style": {
        "width": 1600, "height": 1000,
        "padding": 70, "scale": 0.85,
        "offsetX": -90, "offsetY": 0,
        "radius": 24, "shadow": 25,
        "bg": ["#087f8c", "#b5e8ba"]
      },
      "annotations": [
        {"type":"mosaic","x":0.05,"y":0.05,"w":0.22,"h":0.08,"blockSize":20},
        {"type":"rect", "x":0.12,"y":0.82,"w":0.7,"h":0.1,"color":"#e5142a","lineWidth":4},
        {"type":"arrow","bend":0,"lineStyle":"solid","x":0.83,"y":0.87,"x2":1.03,"y2":0.87,"color":"#e5142a","lineWidth":4},
        {"type":"text","x":1.05,"y":0.84,"text":"输入任务\n添加资料","fontSize":48,"color":"#e5142a"}
      ]
    },
    {"path":"/absolute/path/illustration.png","kind":"ai-generated","reason":"来自本篇文章生图记录"},
    {"path":"/absolute/path/unknown.png","kind":"unknown","reason":"没有可确认的来源记录"}
  ]
}
```

示例坐标仅用于格式说明，不是任何实际截图的默认目标。所有标注的 x/y/w/h/x2/y2 均相对**完整原图**归一化；文字可放在原图范围之外，例如 `x=1.05`，但必须落在画布内。字号、线宽是最终画布像素，不随截图缩放，以保持标注可读；目标坐标随截图变换。

`mosaic` 用 x/y/w/h 和 `blockSize`；`rect` 用 x/y/w/h；`arrow` 用起点 x/y 与终点 x2/y2；`text` 用 x/y/text，支持换行，默认 48 px、400 字重，可按画面在 46–50 px 内微调；`number` 用中心 x/y/text，默认 28 px、600 字重，字号控制圆圈大小。文字、框、箭头和马赛克是独立对象。马赛克先处理截图像素，其余标注按数组顺序叠放在上层。

画布宽高建议 320–4096 px；源图限 PNG/JPEG/WebP。较多或高分辨率图片导致项目超过 200 MB 时按章节分组创建项目并说明，不能静默漏图。项目保存内嵌图片和背景，`originals` 另保留副本。自定义背景以 cover 居中覆盖画布；原截图等比 contain 后乘以 scale。

`project.json` 是编辑状态，`project.previous.json` 是上一次保存的恢复副本。导出在 `exports/<时间>-<唯一后缀>/`；每张 PNG 使用顺序名，并通过 `mapping.json` 对应来源和 reviewed 状态。恢复备份时先另存当前项目，再由用户选择恢复版本，不自动覆盖。

## 整篇文章绑定与一键回填

先运行 `editor.py scan --article <本地.md> --vault <可选库根目录> --output <清单.json>`。输出顶层 `article_path`、`article_hash`、`vault`，每张图记录 `references`，例如 `[{"start":120,"end":133,"original":"screenshot.png","syntax":"markdown"}]`。这些偏移使用 Python Unicode 字符数，包含中文和换行；不要用 JavaScript UTF-16 长度重新估计。只允许替换图片链接的地址部分。`scan` 不负责视觉识别，所有图片初始分类为 `unknown`，模型看图后填写 `kind` 与标注。未找到文件或短链有多个候选时先解决路径。

`create` 校验原文哈希及引用边界，把原文快照、引用区间、目标文章路径保存在仅服务端读取的 `article-binding.json`。网页提交导入时只传 ID 与 PNG，不能指定任意文章路径或替换文本。导入重新解析当前文章，以绑定记录中的精确图片目的地址定位仍存在的引用：正文和段落变化、新增非绑定配图均保留，已删除的唯一绑定引用跳过，不从旧快照重新插回。首次导入在文章旁创建 `screenshot-assets/<唯一批次>/` 并更新引用；若当前绑定已全部指向该项目生成的同一安全批次，后续导入覆盖原路径下的 PNG，文章链接保持不变，并把旧 PNG 备份到项目的 `returned-image-backups/<唯一批次>/`。普通 Markdown 使用文章相对路径；Obsidian 提供 vault 时使用库根相对路径，保留 `|600` 等显示参数。`last-import.json` 保存最近回填结果、模式、跳过数量、已移除 ID 和备份位置。

若同一目的地址绑定给不同成图，外部编辑又改变了它的出现次数，剩余引用存在归属歧义，回填必须停止。文章已无任何绑定引用、请求缺少仍在使用的截图，或生成后写入前检测到并发编辑，也必须停止且不改文章。用户确认文章的增删结果后，可运行 `editor.py rebind --project <项目目录>`：它不改文章，只把绑定刷新为当前精确引用，并从 `project.json` 列表中移除已删除的截图；运行前先在项目目录外备份项目和绑定文件。

同一图在正文不同位置可有不同标注，每处单独一个 slide；同一 slide 的 `references` 也可包含多个相同用途的位置。AI 图不加入绑定。文章被外部编辑后按精确图片目的地址重新定位；能唯一对应就保留改动并继续，存在同名多成图歧义才拒绝回填。需要刷新编辑列表时保留已有标注并重新核对语义。

## 线条、箭头走向与编号

`lineWidth` 为 2、4 或 6；`lineStyle` 为 `solid` / `dashed`，默认实线。水平可直指时设 `bend=0`，起止 y 相同；位置错开需斜指时用 `bend=0.14` 或 `-0.14` 的轻弧，方向以避开文字为准。`bend` 为控制点相对起止连线长度的法向偏移；默认自动模式（缺省或 null），接近水平的线采用直线，否则采用 0.14 轻弧。手动画箭头时，自动模式在约 5 度内吸附为水平线。模型生成清单时应明确设定起止坐标和 bend，不依赖自动模式替代构图判断。

箭头尖端沿终点切线方向绘制，虚线只影响路径，不影响箭头尖端。用户可选直线、轻弧、反向弧，也可拖动中点微调。采用同一渲染函数，直线是 bend 为 0 的情形，导出与预览一致。

有两个及以上语义标注点时，添加 `number` 对象，text 为连续的 `1`、`2`、`3`，放在各自说明前。示例：`{"type":"number","x":1.04,"y":0.5,"text":"1","fontSize":28,"color":"#e5142a"}`。坐标按当前图布局实际计算，数字圆与说明留出间距，不压在截图文字上。一个点的框、箭头、说明和数字是多个独立可编辑对象，但语义计数仍为一个点。

文字直接绘制，无白色底板。布局按最终画布像素核对短箭头、两端等距和外侧留白，再换算到原图归一化坐标；不得把本示例坐标复制到实际截图。单张和整组导出均在服务端落盘；页面提供实际目录、打开文件夹和受限导出文件下载，不依赖 data URL 下载完成。

## 马赛克对象

马赛克示例：`{"type":"mosaic","x":0.1,"y":0.1,"w":0.28,"h":0.09,"blockSize":20}`。`blockSize` 只允许 12 / 20 / 32，分别对应小 / 中 / 大，缺省或非法值按 20 渲染。坐标仍相对完整原图归一化，超出截图的部分被裁掉。编辑器从原始截图对应区域采样并像素化，不改写 `originals` 中的原图；选区轮廓仅用于编辑，不进入无选中状态下的导出。预览、单张导出、批量导出和文章回填必须调用同一绘制路径。

### IP 水印
项目 `defaultWatermark` 为创建时读取的用户默认水印 data URL，未设置时为 null。`style.watermark` 可省略（有默认水印时默认开启，否则关闭）：`{"enabled":true,"size":182,"position":"right","src":null,"x":null,"y":null}`。size 可选 80/112/152/182 px，position 为 left/right，src 为自定义图片 data URL 或 null。x/y 为印章左上角相对画布的归一化坐标，null 使用截图角落叠盖预设。水印不改变导出尺寸。
