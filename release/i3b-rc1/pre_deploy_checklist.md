# 预部署检查清单（pre_deploy_checklist.md）
- [ ] Git 工作树干净；分支=feature/asip-intelligence-v10-i3b-release-candidate
- [ ] 全部测试通过（I3-B：PASS 390+，FAIL 0）
- [ ] 构建成功：python scripts/build_site.py --no-embed（151 路由）
- [ ] 数据质量门通过（deep=13、basic=0、empty=0、dup=0）
- [ ] 证据 verified>=55、pending<=12、stale<=3
- [ ] 浏览器验收 55 页零错误；公网预览验证通过
- [ ] 生产隔离：production_isolation_results.json 确认 288 文件零变更
- [ ] release/i3b-rc1 14 个文件齐备；build_sha256.txt 与 dist 一致
- [ ] 备份：生产树快照 + 回退标签
