from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Sequence, Optional

from netmiko import ConnectHandler


# =========================
# Что считаем ошибкой в выводе
# =========================
# У OcNOS/B4Com почти все проблемы в CLI подсвечиваются словами:
# invalid / error / failed / incomplete и т.п.
# Мы их не "лечим", а просто честно складываем в errors.log,
# чтобы потом можно было быстро понять, где устройство ругалось.
ERR_RE = re.compile(
    r"(^%{1,2}\s.*$|invalid|error|failed|ambiguous|incomplete|not\s+allowed|missing)",
    re.I | re.M,
)


def ts():
    # Короткий timestamp для имен файлов и группирования логов одного запуска
    return time.strftime("%Y%m%d-%H%M%S")


def ensure_dir(p: Path):
    # Создаёт директорию, если её ещё нет.
    # Нужно, чтобы out_b4/ не падал на первом же запуске.
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str, mode: str = "w"):
    # Универсальная запись текста в файл.
    # Перед записью гарантируем, что папка существует.
    ensure_dir(path.parent)
    with open(path, mode, encoding="utf-8") as f:
        f.write(text)


class B4:
    """
    Обёртка над Netmiko для реального B4Com/OcNOS.

    Что даёт:
    1) единая точка подключения (open/connect/close)
    2) понятные логи:
       - session.log  : сырой диалог с устройством
       - commands.log : какие команды мы отправляли
       - errors.log   : фрагменты вывода, где устройство ругалось
    3) заливка конфигурации пачками (per_batch), чтобы можно было лить тысячи команд.
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
        # Параметры Netmiko под реальное железо.
        # fast_cli=True — на реальном устройстве это ускоряет работу,
        # т.к. CLI работает стабильнее, чем в QEMU/GNS3.
        self.params = {
            "device_type": device_type,
            "host": host,
            "username": user,
            "password": password,
            "port": port,
            "fast_cli": True,
            "global_delay_factor": global_delay,
        }
        if secret:
            self.params["secret"] = secret

        # Папка, куда пишем все результаты запусков
        self.out_dir = Path(out_dir)
        ensure_dir(self.out_dir)

        # Один timestamp на весь запуск — чтобы потом не искать логи по кускам
        self.tag = tag
        self.stamp = ts()

        # Файлы логов
        self.session_log = self.out_dir / f"{self.stamp}_{self.tag}_session.log"
        self.error_log = self.out_dir / f"{self.stamp}_{self.tag}_errors.log"
        self.cmd_log = self.out_dir / f"{self.stamp}_{self.tag}_commands.log"

        self.conn = None

    def open(self):
        # Для удобства: r = B4(...).open()
        return self.connect()

    def connect(self):
        # Прокидываем session_log в Netmiko
        self.params["session_log"] = str(self.session_log)
        self.params["session_log_file_mode"] = "write"

        # Подключаемся с поднятыми таймаутами — на живом железе иногда долгий баннер/SSH
        self.conn = ConnectHandler(
            **self.params,
            banner_timeout=60,
            auth_timeout=60,
            conn_timeout=60,
            allow_agent=False,
            use_keys=False,
        )

        # Если есть enable — зайдём.
        # Если нет — просто идём дальше.
        try:
            self.conn.enable()
        except Exception:
            pass

        # Делаем терминал удобным для массовых show:
        # terminal length 0 — чтобы не было пагинации "--More--"
        try:
            self.conn.send_command("terminal length 0", expect_string=r"#", read_timeout=30)
        except Exception:
            pass

        # terminal no monitor — чтобы syslog не летел прямо в CLI и не мешал Netmiko
        try:
            self.conn.send_command("terminal no monitor", expect_string=r"#", read_timeout=30)
        except Exception:
            pass

        # B4Com по умолчанию "транзакционный" — без commit команды не применяются.
        # Мы это отключаем на время сессии, чтобы не вставлять commit после каждого шага.
        try:
            self.conn.send_command("cmlsh transaction disable", expect_string=r"#", read_timeout=30)
        except Exception as e:
            write_text(self.error_log, f"[cmlsh transaction disable] {e}\n", mode="a")

        return self

    def close(self):
        # Корректно закрываем сессию
        if self.conn:
            try:
                self.conn.disconnect()
            finally:
                self.conn = None

    def _scan_and_log_errors(self, block_title: str, output: str):
        # Вырезаем из вывода всё, что похоже на ошибку CLI,
        # и складываем это отдельным блоком в errors.log.
        if not output:
            return
        m = ERR_RE.findall(output)
        if m:
            hdr = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {block_title}\n"
            body = output if len(output) < 10000 else output[-10000:]
            write_text(self.error_log, hdr + body + "\n", mode="a")

    def show(self, cmd: str, read_timeout: int = 240) -> str:
        # Стандартный show с ожиданием промпта "#".
        # read_timeout берём из cfg, потому что на больших show устройство может отвечать долго.
        out = self.conn.send_command(cmd, expect_string=r"#", read_timeout=read_timeout)
        self._scan_and_log_errors(f"show: {cmd}", out)
        return out

    def cfg(
        self,
        commands: Sequence[str],
        per_batch: int = 50,
        read_timeout: int = 240,
        sleep_between: float = 0.05,
    ):
        """
        Массовая заливка конфигурации.

        Как работает:
        - режем команды на пачки per_batch
        - каждую пачку отправляем send_config_set(...)
        - команды пишем в commands.log
        - всё, где железка ругается, пишем в errors.log
        """
        i = 0
        while i < len(commands):
            chunk_cmds = list(commands[i : i + per_batch])

            # Логируем, что конкретно отправили
            write_text(self.cmd_log, "\n".join(chunk_cmds) + "\n\n", mode="a")

            # Льём конфиг без выхода из config-mode между пачками —
            # так быстрее и меньше лишних переходов
            out = self.conn.send_config_set(
                chunk_cmds,
                exit_config_mode=False,
                read_timeout=read_timeout,
                cmd_verify=False,
                strip_prompt=False,
                strip_command=False,
            )
            self._scan_and_log_errors(f"config-chunk {i // per_batch + 1}", out)

            time.sleep(sleep_between)
            i += per_batch

        # В конце пробуем выйти из режима конфигурации
        try:
            self.conn.exit_config_mode()
        except Exception:
            pass

    def save_text(self, name: str, text: str):
        # Удобный хелпер для сохранения любых show/verify в отдельный txt
        write_text(self.out_dir / f"{self.stamp}_{self.tag}_{name}.txt", text)
