# I3-B 生产差异摘要（production_diff_summary.md）

- 新增目录：`previews/asip-intelligence-v1.0-rc1/`（gh-pages 隔离预览，314 个文件）
- 修改共享文件：无（gh-pages 根目录 288 个生产文件 git 对象哈希逐一比对，零变更，见 production_isolation_results.json）
- 主站首页：未修改
- 现有国家页/日报/新闻模块：未修改（预览完全隔离于 previews/ 子目录）
- 导航：未修改
- 构建脚本：仅仓库内开发脚本更新（scripts/gen、scripts/build_intelligence_africa.py），不触及生产部署配置
- 路径冲突：无（预览前缀 `previews/asip-intelligence-v1.0-rc1/` 与生产路径无交集）
- 删除操作：无（deleted_paths=[]）
- 预览回退：删除 `previews/asip-intelligence-v1.0-rc1/` 目录即可（生产文件不受影响）
