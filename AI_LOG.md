# AI协作记录

姓名：刘梓皓  学号：2024280422  GitHub：Kozeki0423  提交编号：34 <p>
工具与模型：Claude（Claude Code 编程助手），用于辅助实现与检查。Deepseek v4.1 Flash。

## 一项真实协作过程

**需求与输入**：按 `src/part2_packet.py` 的 docstring 和 `docs/model_contract.md` 实现共享 FIFO 分组发送 `serve_packet(queue, tick, cfg)`。函数需要原地更新 deque，每 tick 最多发送 `cfg.slot_bits`，发完队首才能处理下一项；`remaining_wire_bits` 已由框架初始化为 payload + header，跨 tick 续传时不得重加包头；返回本 tick 线速发送比特数和完整发送的记录列表。

**AI建议**：用一个 `budget = cfg.slot_bits` 和 `sent` 计数器循环处理队首：若队首剩余量不超过预算，则扣减预算、清零剩余量、`popleft` 并加入完成列表；否则只扣减预算中可用部分，保留剩余量并结束本 tick。`remaining_wire_bits` 直接复用框架的初始化，任何分支都不再修改包头。

**我的手算与测试**：先写 2 用户 2 tick、两条 96 bit 记录都来自用户 0 的小例子，手算分组结果应为 delivered=192、wire=256、两次时延均为 1 tick，电路结果应为 delivered=96、backlog=96、wire=96。随后运行 `student_tests/test_my_case.py`。初版测试把两条记录分别放在不同用户上，手算后发现两种方式的 delivered 都是 192，断言无法区分实现是否正确；于是改成同一用户连续到达，得到上表预期，再核对代码。该测试以及 `test_packet_large_record_resumes_without_second_header`（232 bit 记录拆成 128+104 续传）均通过。

**修正或采纳理由**：采纳该循环结构，因为它与模型合同中的“先发完队首、部分发送保留剩余 wire bit、发完队首后才继续下一条”逐条对应；续传路径只扣减已有的 `remaining_wire_bits`，从结构上避免重复加头。测试设计经过修正：原到达序列对两种模式结果相同，没有区分能力；改为同一用户连续到达后，电路必须等待自己的下一个时隙，而分组可以立即发送，测试才真正覆盖固定预约与统计复用的差异。首次实现即通过时也保留了边界验证（部分发送、跨 tick 续传、窗口末尾积压）。

**我能解释的核心逻辑**：`serve_packet` 在一个 tick 内循环扣减队首记录的 `remaining_wire_bits`，只有剩余量归零才 `popleft` 并计入完成；`remaining_wire_bits` 在准入时已经包含一次包头，因此续传只减少剩余量，不会重复增加 32 bit。`serve_circuit` 先由 `tick % cfg.users` 确定唯一可服务的用户，循环同样只操作该用户队列，绝不把其他用户的时隙转给本用户。`summarize` 从 `raw` 直接读取积压，并用 `generated = delivered + dropped + backlog` 校验，未完成记录既不被重复计数，也不被误记为丢失；没有完成记录时平均/最大时延返回 `None` 而不是 0。
