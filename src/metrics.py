"""任务3：补全指标统计。"""
def summarize(raw, cfg):
    """返回字典，键名必须保留：
    payload_utilization=delivered_payload_bits/(cfg.ticks*cfg.slot_bits)
    wire_utilization=wire_sent_bits/(cfg.ticks*cfg.slot_bits)
    mean_delay_ms、max_delay_ms：完成记录的delay_ticks乘cfg.tick_ms；
      无完成记录时两者返回None，不能写0掩盖无送达。
    loss_ratio=dropped_payload_bits/generated_payload_bits；无生成数据时为0。
    backlog_payload_bits：所有未完成记录的原始payload总和，直接取raw对应值。
    只用观察窗口[0,ticks)，不追加排空时间；有效载荷按完整交付记录计数。
    raw['completed']元素含payload_bits、delay_ticks、user。
    要检查generated=delivered+dropped+backlog，不相等抛ValueError。
    """
    generated = raw['generated_payload_bits']
    delivered = raw['delivered_payload_bits']
    dropped = raw['dropped_payload_bits']
    backlog = raw['backlog_payload_bits']
    if generated != delivered + dropped + backlog:
        raise ValueError('payload conservation violated')

    capacity = cfg.ticks * cfg.slot_bits
    completed = raw['completed']
    if completed:
        delays = [record['delay_ticks'] * cfg.tick_ms for record in completed]
        mean_delay = sum(delays) / len(delays)
        max_delay = max(delays)
    else:
        mean_delay = None
        max_delay = None

    return dict(
        payload_utilization=delivered / capacity,
        wire_utilization=raw['wire_sent_bits'] / capacity,
        mean_delay_ms=mean_delay,
        max_delay_ms=max_delay,
        loss_ratio=dropped / generated if generated else 0,
        backlog_payload_bits=backlog,
    )
