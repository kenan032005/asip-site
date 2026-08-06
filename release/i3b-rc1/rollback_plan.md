# 回退计划（rollback_plan.md）

## 预览回退（本阶段唯一已部署内容）
- 方式：从 gh-pages 删除 `previews/asip-intelligence-v1.0-rc1/` 目录并推送（非 force 追加删除提交）
- 验证：raw/github.io 该前缀返回 404；生产文件哈希不变
- 备份：发布提交 4703ab8 保留在 gh-pages 历史中，可随时恢复

## 生产发布回退（I3-C 时使用）
1. 发布前备份：生产树快照（文件哈希清单）+ `git tag asip-production-backup-<date>` + 当前 gh-pages 提交 SHA
2. 回退 Git：`git revert <release-commit>` 或 `git reset --hard <backup-tag>`（按当时确认的方式）
3. 回退静态产物：用备份快照重建/重传 dist（build_sha256.txt 校验）
4. 回退导航：移除或还原主导航入口变更
5. 回退缓存：CDN/浏览器缓存用版本号或 cache-busting 处理
6. 回退验证：预部署清单逐项复检（路由、数据、图谱、Demo、主站）
7. 操作顺序：备份确认 → 停止流量/灰度 → 回退产物 → 校验哈希 → 恢复流量 → 验证 30 分钟
