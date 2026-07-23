"""TopoFlow 配置加载模块"""

import os
import toml
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RedisConfig:
    host: str = "127.0.0.1"
    port: int = 6379
    db: int = 0
    password: str = ""
    queue_enabled: bool = False
    cache_enabled: bool = False


@dataclass
class GateATopologyConfig:
    max_triangle_pct: float = 5.0
    max_face_density_variance: float = 0.3
    require_watertight: bool = True


@dataclass
class GateBUVConfig:
    min_island_gap_px: int = 4
    min_first_quadrant_utilization: float = 0.8
    max_stretch_pct: float = 3.0


@dataclass
class GateCBakeConfig:
    normal_color_space: str = "linear"
    ao_color_space: str = "srgb"


@dataclass
class StandardsConfig:
    engine_target: str = "ue5"
    face_budget: str = "medium"
    uv_resolution: int = 2048
    normal_space: str = "directx"
    gate_a_topology: GateATopologyConfig = field(default_factory=GateATopologyConfig)
    gate_b_uv: GateBUVConfig = field(default_factory=GateBUVConfig)
    gate_c_bake: GateCBakeConfig = field(default_factory=GateCBakeConfig)


@dataclass
class Config:
    output_dir: str = "./output"
    temp_dir: str = "./.temp"
    keep_temp: bool = False
    log_level: str = "info"
    run_mode: str = "interactive"
    auto_pilot: bool = False
    watch_folder: str = ""
    engine_preset: str = "ue5_nanite"
    api_port: int = 8080
    api_webhook: str = ""
    meshy_key: str = ""
    deepseek_key: str = ""
    openai_key: str = ""
    anthropic_key: str = ""
    max_workers: int = 1
    worker_timeout: int = 3600
    cache_enabled: bool = True
    cache_max_entries: int = 20
    cache_backend: str = "file"
    redis: RedisConfig = field(default_factory=RedisConfig)
    standards: StandardsConfig = field(default_factory=StandardsConfig)


def load_config(path: str = "config.toml") -> Config:
    """从 TOML 文件加载配置，缺失字段使用默认值"""
    if not os.path.exists(path):
        return Config()

    raw = toml.load(path)
    cfg = Config()

    # general
    gen = raw.get("general", {})
    cfg.output_dir = gen.get("output_dir", cfg.output_dir)
    cfg.temp_dir = gen.get("temp_dir", cfg.temp_dir)
    cfg.keep_temp = gen.get("keep_temp", cfg.keep_temp)
    cfg.log_level = gen.get("log_level", cfg.log_level)

    # run_mode
    rm = raw.get("run_mode", {})
    cfg.run_mode = rm.get("default", cfg.run_mode)
    cfg.auto_pilot = rm.get("auto_pilot", cfg.auto_pilot)
    cfg.watch_folder = rm.get("watch_folder", cfg.watch_folder)
    cfg.engine_preset = rm.get("engine_preset", cfg.engine_preset)
    cfg.api_port = rm.get("api_port", cfg.api_port)
    cfg.api_webhook = rm.get("api_webhook", cfg.api_webhook)

    # api_keys
    ak = raw.get("api_keys", {})
    cfg.meshy_key = ak.get("meshy", cfg.meshy_key)
    cfg.deepseek_key = ak.get("deepseek", cfg.deepseek_key)
    cfg.openai_key = ak.get("openai", cfg.openai_key)
    cfg.anthropic_key = ak.get("anthropic", cfg.anthropic_key)

    # performance
    perf = raw.get("performance", {})
    cfg.max_workers = perf.get("max_workers", cfg.max_workers)
    cfg.worker_timeout = perf.get("worker_timeout", cfg.worker_timeout)
    cfg.cache_enabled = perf.get("cache_enabled", cfg.cache_enabled)
    cfg.cache_max_entries = perf.get("cache_max_entries", cfg.cache_max_entries)
    cfg.cache_backend = perf.get("cache_backend", cfg.cache_backend)

    # redis
    rd = raw.get("redis", {})
    cfg.redis.host = rd.get("host", cfg.redis.host)
    cfg.redis.port = rd.get("port", cfg.redis.port)
    cfg.redis.db = rd.get("db", cfg.redis.db)
    cfg.redis.password = rd.get("password", cfg.redis.password)
    cfg.redis.queue_enabled = rd.get("queue_enabled", cfg.redis.queue_enabled)
    cfg.redis.cache_enabled = rd.get("cache_enabled", cfg.redis.cache_enabled)

    # standards
    st = raw.get("standards", {})
    cfg.standards.engine_target = st.get("engine_target", cfg.standards.engine_target)
    cfg.standards.face_budget = st.get("face_budget", cfg.standards.face_budget)
    cfg.standards.uv_resolution = st.get("uv_resolution", cfg.standards.uv_resolution)
    cfg.standards.normal_space = st.get("normal_space", cfg.standards.normal_space)

    ga = st.get("gate_a_topology", {})
    cfg.standards.gate_a_topology.max_triangle_pct = ga.get("max_triangle_pct", cfg.standards.gate_a_topology.max_triangle_pct)
    cfg.standards.gate_a_topology.max_face_density_variance = ga.get("max_face_density_variance", cfg.standards.gate_a_topology.max_face_density_variance)
    cfg.standards.gate_a_topology.require_watertight = ga.get("require_watertight", cfg.standards.gate_a_topology.require_watertight)

    return cfg
