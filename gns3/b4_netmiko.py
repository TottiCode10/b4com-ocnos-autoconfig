# b4_netmiko.py
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Sequence, Optional, Iterable, List, Any

from netmiko import ConnectHandler
from netmiko.exceptions import ReadTimeout

# =========================
# Общие утилиты
# =========================
# В выводе OcNOS/B4Com при ошибках обычно встречаются слова вроде:
# invalid / error / failed / incomplete и т.п.
# Мы их ловим и складируем в отдельный errors.log.
ERR_RE = re.compile(
    r"(^%{1,2}\s.*$|invalid|error|failed|ambiguous|incomplete|not\s+allowed|missing)",
    re.I | re.M,
)

def ts() -> str:
    return time.strftime("%Y%m%d-%H%M%S")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def write_text(path: Path, text: str, mode: str = "w"):
    ensure_dir(path.parent)
    with open(path, mode, encoding="utf-8") as f:
        f.write(text)

def chunk(seq: Sequence[str], size: int) -> Iterable[List[str]]:
    """Режем команды на пачки. Это ключ к стабильности при больших объёмах."""
    for i in range(0, len(seq), size):
        yield list(seq[i:i + size])

class B4:
    """
    Обёртка Netmiko под OcNOS/B4Com.

    Что делает:
    - держит соединение (open/close)
    - отправляет "разогревающие" команды терминала
    - льёт конфиг пачками и пишет:
        * session.log — полностью сырой диалог
        * commands.log — какие команды отправляли
        * errors.log — ответы устройства, где оно ругалось
    """

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        device_type: str = "ipinfusion_ocnos",
        port: int = 22,
        secret: Optional[str] = None,
        global_delay: float = 1.0,
        out_dir: str = "out_b4",
        tag: str = "session",
    ):
        # Базовые параметры Netmiko.
        # fast_cli=False — сознательно: OcNOS в эмуляции “шумит”, fast_cli только усугубляет.
        self.params = {
            "device_type": device_type,
            "host": host,
            "username": user,
            "password": password,
            "port": port,
            "fast_cli": False,
            "global_delay_factor": global_delay,
        }
        if secret:
            self.params["secret"] = secret

        self.out_dir = Path(out_dir)
        ensure_dir(self.out_dir)

        # Все файлы логов привязываем к одному timestamp, чтобы было удобно смотреть.
        self.tag = tag
        self.stamp = ts()
        self.session_log = self.out_dir / f"{self.stamp}_{self.tag}_session.log"
        self.error_log = self.out_dir / f"{self.stamp}_{self.tag}_errors.log"
        self.cmd_log = self.out_dir / f"{self.stamp}_{self.tag}_commands.log"

        self.conn = None

    def open(self) -> "B4":
        return self.connect()

    def connect(self) -> "B4":
        # session_log подключаем прямо в Netmiko
        self.params["session_log"] = str(self.session_log)
        self.params["session_log_file_mode"] = "write"

        # Коннект с увеличенными таймаутами — OcNOS иногда долго отдаёт баннер.
        self.conn = ConnectHandler(
            **self.params,
            banner_timeout=60,
            auth_timeout=60,
            conn_timeout=60,
            allow_agent=False,
            use_keys=False,
        )

        # Если есть enable — зайдём. Если нет, ок.
        try:
            self.conn.enable()
        except Exception:
            pass

        # Приводим терминал в “тихий” режим:
        # - без пагинации
        # - без вывода логов в консоль
        for pre_cmd in ("terminal length 0", "terminal no monitor"):
            try:
                self.conn.send_command(
                    pre_cmd,
                    expect_string=r"[#>]",
                    read_timeout=30,
                    cmd_verify=False,
                )
            except Exception:
                pass

        # На B4Com по умолчанию transactional config.
        # Команда отключает commit в рамках сессии.
        try:
            self.conn.send_command(
                "cmlsh transaction disable",
                expect_string=r"[#>]",
                read_timeout=30,
                cmd_verify=False,
            )
        except Exception as e:
            write_text(self.error_log, f"[cmlsh transaction disable] {e}\n", mode="a")

        # После всех “разогревов” чистим буфер.
        # Это снижает шанс таймаутов на шумной консоли.
        try:
            self.conn.clear_buffer()
        except Exception:
            pass

        return self

    def close(self):
        if self.conn:
            try:
                self.conn.disconnect()
            finally:
                self.conn = None

    def _scan_and_log_errors(self, block_title: str, output: str):
        """Если в выводе есть ругань устройства — тащим её в errors.log."""
        if not output:
            return
        m = ERR_RE.findall(output)
        if m:
            hdr = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {block_title}\n"
            body = output if len(output) < 10000 else output[-10000:]
            write_text(self.error_log, hdr + body + "\n", mode="a")

    def _ensure_config_mode(self, read_timeout: int = 60):
        """
        Входим в config mode один раз.
        OcNOS под нагрузкой иногда шумит, поэтому:
        - сначала пробуем штатно
        - если таймаут — форсим через configure terminal timing-методом.
        """
        if not self.conn:
            return
        try:
            self.conn.clear_buffer()
        except Exception:
            pass

        try:
            if not self.conn.check_config_mode():
                self.conn.config_mode()
        except ReadTimeout:
            try:
                self.conn.send_command_timing("configure terminal")
            except Exception:
                pass
        except Exception:
            try:
                self.conn.send_command_timing("configure terminal")
            except Exception:
                pass

    def show(self, cmd: str, read_timeout: int = 240, expect_string: str = r"[#>]") -> str:
        """
        show-команды.
        cmd_verify=False — OcNOS может “утопить” эхо команды в шуме,
        из-за этого Netmiko без этого флага часто ловит ReadTimeout.
        """
        out = self.conn.send_command(
            cmd,
            expect_string=expect_string,
            read_timeout=read_timeout,
            cmd_verify=False,
        )
        self._scan_and_log_errors(f"show: {cmd}", out)
        return out

    def cfg(
        self,
        commands: Sequence[str],
        per_batch: int = 50,
        read_timeout: int = 240,
        sleep_between: float = 0.05,
        commit: bool = False,
        **_: Any,
    ):
        """
        Массовая заливка конфигурации.

        Ключевые моменты:
        - входим в config mode один раз
        - режем команды на пачки per_batch
        - перед каждой пачкой чистим буфер 
        - enter_config_mode=False: Netmiko не пытается каждый раз
          проверять/входить в конфиг, что и было причиной таймаутов.
        """
        if not self.conn:
            raise RuntimeError("Connection is not open")

        self._ensure_config_mode(read_timeout=min(60, read_timeout))

        i = 0
        while i < len(commands):
            cmd_chunk = list(commands[i:i + per_batch])

            # Логируем реальные команды, которые отправили
            write_text(self.cmd_log, "\n".join(cmd_chunk) + "\n\n", mode="a")

            try:
                self.conn.clear_buffer()
            except Exception:
                pass

            out = self.conn.send_config_set(
                cmd_chunk,
                enter_config_mode=False,
                exit_config_mode=False,
                read_timeout=read_timeout,
                cmd_verify=False,
                strip_prompt=False,
                strip_command=False,
            )
            self._scan_and_log_errors(f"config-chunk {i // per_batch + 1}", out)

            time.sleep(sleep_between)
            i += per_batch

 
        try:
            self.conn.exit_config_mode()
        except Exception:
            try:
                self.conn.send_command(
                    "end",
                    expect_string=r"[#>]",
                    cmd_verify=False,
                    read_timeout=30,
                )
            except Exception:
                pass

    def save_text(self, name: str, text: str):
        """Сохраняем произвольный вывод в out_dir с понятным именем."""
        write_text(self.out_dir / f"{self.stamp}_{self.tag}_{name}.txt", text)
