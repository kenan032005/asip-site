# I3-C 生产同步计划（production_sync_plan.md）

> 本文件为 I3-C 的准备文档；I3-B 阶段不执行生产同步。

1. 前置：I3-B 关闭、人工核验通过、I3-C 单独获批
2. 备份：`git tag asip-production-backup-<date>` + gh-pages 当前树快照（已存 4703ab8）
3. 合并范围：仅 feature/asip-intelligence-v10-i3b-release-candidate → main（需人工确认；本阶段禁止自动合并）
4. 静态产物：`python scripts/build_site.py --no-embed` 从合并后 main 重新构建，路由 151 条
5. 部署方式：将 dist 全量发布到生产托管（替换现网），保留 release/i3b-rc1 产物与 sha256 供校验
6. 主导航：新增 `/intelligence/africa/` 入口（需产品确认）
7. 验证：预部署清单（pre_deploy_checklist.md）→ 发布 → 后置清单（post_deploy_checklist.md）
8. 回退：见 rollback_plan.md
