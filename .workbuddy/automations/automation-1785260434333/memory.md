# Automation Memory: ASIP 每日日报运行（pipeline_runner, 北京）

## 2026-07-29 22:53 (北京时间) — 运行成功
- run_id: 20260729T225349+0800_37nrdr
- 退出码: 0（成功）
- 日报日期（北京）: 2026-07-29，窗口 2026-07-28 22:00 → 2026-07-29 22:00
- main commit: 6c0d1067c429a4204ceb7204b246378b93a8f035
- gh-pages commit: 544026eceb02ff609bf6d9d33580309697bc8aea
- 线上验证: ✅ run_id 一致, http 200, events_24h=0
- 注: 当日 24h 新增事件=0；持续跟踪 乍得2/贝宁3/南苏丹10/苏丹36/埃塞12 等。全流程（pull→单测→汇总→日报→校验→commit→push→build→dist校验→deploy→线上验证）通过。
- 日志: logs/pipeline_20260729T225349+0800_37nrdr.json

## 2026-08-01 22:14 (北京时间) — 运行失败
- run_id: 20260801T221428+0800_73lgls
- 退出码: 1（失败）
- 失败阶段: 第 1 步 `git pull --rebase origin main` 中止，未进入日报生成/部署流程
- 失败原因: 工作目录存在未暂存改动（unstaged changes），git 拒绝 rebase 拉取。涉及 .workbuddy/automations/.../memory.md、data/canonical/quarantine.json、data/public/published_events.json、data/sources.json、scripts/collectors/country_runner.py 及多个未跟踪脚本（add_sources.py、analyze_tchadone.py、audit_sources.py、collectors/framework.py、collectors/registry.py、smoke_*.py、stage3_collect_v2.py、test_*.py）。
- main commit: 空（未生成）
- gh-pages commit: 空（未生成）
- 线上验证: 未执行
- 处理: 按规则如实汇报失败，未重试、未手工部署。待清理/提交工作目录未暂存改动后可下次重跑。
- 日志: logs/pipeline_20260801T221428+0800_73lgls.json

## 经验
- 仅运行 `scripts/pipeline_runner.py --mode daily --trigger scheduled` 一条命令即可，脚本按北京时间自动算日报日期，无需传参。
- deploy.token 不可写入任何输出。
