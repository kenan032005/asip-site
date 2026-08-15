# 网络 QA

## 预览 / 网络类测试
- `test_i3a_preview`：deep country 页面构建校验 — 通过（依赖 `dist/`）。
- `test_i3b_public_preview`：`PASS=8 FAIL=0` — 预览 URL 记录、可达性（HTTP 200）、serves HTML、gh-pages 分支存活等全部通过，退出码 0。

## 来源链接
- 新增 16 个 Pack B 来源 + 1 去重改写指向既有来源（`expd-mapping-ansaroul-islam`）。
- `test_africa_evidence_quality` 的 origin 校验经 §5.1 修复后通过；无 `dup_urls`（去重生效）。

## 结论
网络/预览可达性校验通过；来源 URL 无重复、枚举合法。
