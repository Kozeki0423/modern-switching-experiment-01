"""自拟反例：2用户2tick手算例 + 空闲、跨tick续传、窗口末尾积压。"""
from collections import deque
import pytest

from src.models import Arrival, Config, Pending
from src.part1_circuit import serve_circuit
from src.part2_packet import serve_packet
from src.metrics import summarize
from src.utils import simulate


def test_two_user_two_tick_handwork():
    """cfg(users=2, ticks=2, slot_bits=128)，两条记录都来自用户0。

    电路：t0 服务用户0 发 96；t1 轮到用户1 但队列为空，用户0 的第二条
    只能等 t2，已超出窗口 -> 积压。
    手算电路：generated=192, delivered=96, backlog=96, wire=96。
    分组：t0 发 user0 的 96+32=128，t1 发第二条 128，均完整送达。
    手算分组：delivered=192, backlog=0, wire=256, 两条时延均为 1。
    """
    cfg = Config(users=2, ticks=2, slot_bits=128)
    traffic = [Arrival(0, 0, 96), Arrival(1, 0, 96)]

    c = simulate(traffic, cfg, 'circuit')
    assert c['delivered_payload_bits'] == 96
    assert c['backlog_payload_bits'] == 96
    assert c['wire_sent_bits'] == 96

    p = simulate(traffic, cfg, 'packet')
    assert p['delivered_payload_bits'] == 192
    assert p['backlog_payload_bits'] == 0
    assert p['wire_sent_bits'] == 256
    assert [d['delay_ticks'] for d in p['completed']] == [1, 1]


def test_circuit_idle_slot_not_borrowed():
    """tick0 属于用户0；用户1 的 32 bit 必须原样等到 tick1。"""
    a = Pending(1, 0, 32, 32)
    queues = [deque(), deque([a])]
    assert serve_circuit(queues, 0, Config(users=2)) == (0, [])
    assert a.remaining_wire_bits == 32
    assert len(queues[1]) == 1


def test_packet_large_record_resumes_without_second_header():
    """232 bit 记录拆成 128 + 104，两个 tick 后完成，续传不得再加 32 bit 头。"""
    a = Pending(0, 0, 200, 232)
    queue = deque([a])
    assert serve_packet(queue, 0, Config()) == (128, [])
    assert a.remaining_wire_bits == 104
    assert serve_packet(queue, 1, Config()) == (104, [a])


def test_window_end_backlog_is_not_loss():
    """观察窗口只有 1 tick：200 bit 未发完，是积压而非丢包，时延无样本。"""
    cfg = Config(ticks=1)
    raw = simulate([Arrival(0, 0, 200)], cfg, 'packet')
    m = summarize(raw, cfg)
    assert m['loss_ratio'] == 0
    assert m['backlog_payload_bits'] == 200
    assert m['mean_delay_ms'] is None
    assert m['max_delay_ms'] is None
    assert m['payload_utilization'] == 0


def test_metrics_conservation_violation_raises():
    raw = dict(generated_payload_bits=100, delivered_payload_bits=40,
               dropped_payload_bits=20, backlog_payload_bits=30,
               wire_sent_bits=64, completed=[])
    with pytest.raises(ValueError):
        summarize(raw, Config(ticks=1))
