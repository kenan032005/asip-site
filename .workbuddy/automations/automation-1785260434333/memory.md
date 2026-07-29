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

## 经验
- 仅运行 `scripts/pipeline_runner.py --mode daily --trigger scheduled` 一条命令即可，脚本按北京时间自动算日报日期，无需传参。
- deploy.token 不可写入任何输出。
