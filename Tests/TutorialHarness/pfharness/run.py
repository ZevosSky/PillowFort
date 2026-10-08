"""
    @author Tutorial harness
    @brief  Runs a built SandboxGame on Mesa lavapipe under a private Xvfb, with
            the Khronos validation layer, frame-exact screenshots and input
            (tools/pf_framehook.c), and a pass/fail verdict from the log.
    @copyright 2026 Gary Yang

    A run FAILS on: any validation error (an `[ERROR]` line, or any message
    carrying a VUID-, SYNC-, or UNASSIGNED- id), a non-zero exit, a crash, a
    hang past the timeout, or a missing --expect pattern. Warnings are reported
    and do not fail the run.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

from . import build as pfbuild

HARNESS_DIR = pfbuild.HARNESS_DIR
TOOLS_DIR = os.path.join(pfbuild.BUILD_ROOT, "_tools")

# Messages every Debug run prints that are not problems. Each one is explained.
EXPECTED_WARNINGS = [
    # Chapter 02 section 2 asks for sync validation with the deprecated "enables"
    # setting on purpose (a vkconfig override cannot switch it off) and says to
    # expect exactly this warning.
    (re.compile(r'"enables".*deprecated|deprecated.*"enables"|enables.*validate_sync', re.S),
     "chapter 02 section 2: deliberate use of the deprecated \"enables\" layer setting"),
]
# Mesa prints this itself (not through Vulkan) on every lavapipe instance.
DRIVER_NOISE = re.compile(r"lavapipe is not a conformant vulkan implementation", re.I)
ID_PATTERN = re.compile(r"\b(VUID-[\w-]+|SYNC-[\w-]+|UNASSIGNED-[\w.-]+|BestPractices-[\w-]+)")


@dataclass
class Message:
    severity: str       # error / warning / info
    text: str
    ids: list[str] = field(default_factory=list)
    expected: str = ""  # why it is tolerated, if it is


@dataclass
class RunResult:
    executable: str
    args: list[str]
    out_dir: str
    exit_code: Optional[int] = None
    signal: Optional[str] = None
    timed_out: bool = False
    seconds: float = 0.0
    presents: int = 0
    screenshots: list[dict] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)          # what the program printed
    layer_messages: list[Message] = field(default_factory=list)    # the layer's own log, with IDs
    missing_expectations: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    environment: dict = field(default_factory=dict)
    sync_settings: dict = field(default_factory=dict)
    heuristic_only: list[str] = field(default_factory=list)   # errors that vanish without the heuristic
    heuristic_recheck: str = ""                               # out dir of the heuristic-off re-run

    @property
    def ok(self) -> bool:
        return not self.failures


# ------------------------------------------------------------- tools

def tool(name: str, source: str, flags: list[str], libs: list[str]) -> str:
    out = os.path.join(TOOLS_DIR, name)
    src = os.path.join(HARNESS_DIR, "tools", source)
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return out
    os.makedirs(TOOLS_DIR, exist_ok=True)
    tmp = f"{out}.{os.getpid()}.tmp"
    proc = subprocess.run(["gcc", "-O1", *flags, "-o", tmp, src, *libs],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"building {name}: {proc.stdout}")
    os.replace(tmp, out)
    return out


def framehook() -> str:
    return tool("pf_framehook.so", "pf_framehook.c", ["-shared", "-fPIC", f"-I{pfbuild.VULKAN_SDK}/Include"], ["-ldl"])


def xclose() -> str:
    return tool("pf_xclose", "pf_xclose.c", [], ["-lX11"])


# ------------------------------------------------------------- environment

def lavapipe_icd() -> str:
    for d in ("/usr/share/vulkan/icd.d", "/usr/local/share/vulkan/icd.d", "/etc/vulkan/icd.d"):
        for name in ("lvp_icd.json", "lvp_icd.x86_64.json"):
            if os.path.exists(os.path.join(d, name)):
                return os.path.join(d, name)
    raise RuntimeError("lavapipe ICD not found: apt-get install mesa-vulkan-drivers")


def vulkan_environment(force_sync: bool, shader_heuristic: bool = True) -> dict:
    sdk = pfbuild.VULKAN_SDK
    layer_dir = os.path.join(sdk, "share", "vulkan", "explicit_layer.d")
    if not os.path.exists(os.path.join(layer_dir, "VkLayer_khronos_validation.json")) \
            and not os.environ.get("PF_ALLOW_NO_LAYER"):
        raise RuntimeError(f"validation layer missing from {layer_dir}: run setup_linux.sh")
    env = {
        "VULKAN_SDK": sdk,
        "PATH": f"{sdk}/Bin:" + os.environ.get("PATH", ""),
        "LD_LIBRARY_PATH": f"{sdk}/Lib" + (":" + os.environ["LD_LIBRARY_PATH"] if os.environ.get("LD_LIBRARY_PATH") else ""),
        "VK_ADD_LAYER_PATH": layer_dir,
        "VK_DRIVER_FILES": lavapipe_icd(),
        "VK_ICD_FILENAMES": lavapipe_icd(),
        # Neutralize anything inherited that could configure the layer behind our back -
        # the Linux equivalent of the vkconfig override chapter 01 section 5 warns about.
        "VK_LAYER_SETTINGS_PATH": "/nonexistent",
    }
    if force_sync:
        env["VK_LAYER_VALIDATE_SYNC"] = "1"
    # Without this, VVL 1.4.363's sync validation does not see shader reads and writes made
    # through descriptors (storage buffers/images, sampled images) at all; its default is off.
    # The layer warns it can produce false positives, so a run that fails only with it on is
    # re-checked without it and reported as such (see run()). Atomics stay untracked either way.
    # None leaves it unset, so the program's own VK_EXT_layer_settings request decides -
    # the only way to prove that request works, since an environment variable overrides it.
    if shader_heuristic is not None:
        env["VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC"] = "1" if shader_heuristic else "0"
    return env


def sync_settings(env: dict) -> dict:
    """What configured synchronization validation for a run, for result.json."""
    return {
        "program_request": "whatever the program asks for itself (the tutorial: VK_EXT_layer_settings "
                           "\"enables\" = SYNCHRONIZATION_VALIDATION); not visible to the harness",
        "VK_LAYER_VALIDATE_SYNC": env.get("VK_LAYER_VALIDATE_SYNC", "unset"),
        "VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC": env.get("VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC", "unset"),
        "VK_LAYER_SETTINGS_PATH": env.get("VK_LAYER_SETTINGS_PATH", "unset") + " (no vk_layer_settings.txt override)",
        "layer_defaults_left_alone": "syncval_full_validation=true, syncval_record_time_validation=true, "
                                     "syncval_load_op_after_store_op_validation=false",
    }


def layer_log_environment(path: str) -> dict:
    """The layer's own log, beside the program's callback: it carries the message IDs
    (VUID-..., SYNC-HAZARD-...) that the tutorial's callback does not print."""
    return {"VK_LAYER_DEBUG_ACTION": "VK_DBG_LAYER_ACTION_LOG_MSG",
            "VK_LAYER_LOG_FILENAME": path,
            "VK_LAYER_REPORT_FLAGS": "error,warn,perf"}


class Xvfb:
    def __init__(self, size: str):
        self.size = size
        self.proc: Optional[subprocess.Popen] = None
        self.display = ""

    def __enter__(self) -> "Xvfb":
        for number in range(90, 190):
            if os.path.exists(f"/tmp/.X{number}-lock") or os.path.exists(f"/tmp/.X11-unix/X{number}"):
                continue
            self.proc = subprocess.Popen(["Xvfb", f":{number}", "-screen", "0", f"{self.size}x24",
                                          "-nolisten", "tcp", "-noreset"],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(100):
                if os.path.exists(f"/tmp/.X11-unix/X{number}"):
                    self.display = f":{number}"
                    return self
                if self.proc.poll() is not None:
                    break
                time.sleep(0.05)
            if self.proc.poll() is None:
                self.proc.kill()
        raise RuntimeError("could not start Xvfb")

    def __exit__(self, *_):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


# ------------------------------------------------------------- scripts

def parse_script(path: Optional[str], shots: list[int]) -> dict[int, list[str]]:
    events: dict[int, list[str]] = {}
    for frame in shots:
        events.setdefault(frame, []).append("shot")
    if path:
        with open(path) as handle:
            for number, raw in enumerate(handle, 1):
                line = raw.split("#", 1)[0].strip()
                if not line:
                    continue
                frame_text, _, command = line.partition(" ")
                if not frame_text.isdigit() or not command.strip():
                    raise ValueError(f"{path}:{number}: expected '<frame> <command>', got {raw!r}")
                events.setdefault(int(frame_text), []).append(command.strip())
    return events


def _xdotool(env: dict, *args: str) -> str:
    proc = subprocess.run(["xdotool", *args], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.stdout.strip()


def find_window(env: dict, pid: int) -> str:
    for args in (["search", "--pid", str(pid)], ["search", "--name", "."]):
        out = _xdotool(env, *args)
        ids = [line for line in out.splitlines() if line.strip().isdigit()]
        if ids:
            return ids[-1]
    return ""


def run_command(command: str, frame: int, env: dict, window: str, out_dir: str, result: RunResult) -> None:
    verb, _, rest = command.partition(" ")
    args = shlex.split(rest.replace("{win}", window))
    if verb == "shot":
        label = args[0] if args else f"frame{frame:05d}"
        png = os.path.join(out_dir, f"{label}.png")
        proc = subprocess.run(["import", "-window", window or "root", png], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        geometry = _xdotool(env, "getwindowgeometry", window) if window else ""
        result.screenshots.append({"frame": frame, "path": png, "ok": proc.returncode == 0,
                                   "error": proc.stdout.strip(), "geometry": geometry})
    elif verb == "resize":
        _xdotool(env, "windowsize", window, *args)
    elif verb == "move":
        _xdotool(env, "mousemove", "--window", window, *args)
    elif verb == "click":
        x, y, *button = args
        _xdotool(env, "mousemove", "--window", window, x, y, "click", button[0] if button else "1")
    elif verb == "down":
        x, y, *button = args
        _xdotool(env, "mousemove", "--window", window, x, y, "mousedown", button[0] if button else "1")
    elif verb == "up":
        x, y, *button = args
        _xdotool(env, "mousemove", "--window", window, x, y, "mouseup", button[0] if button else "1")
    elif verb == "key":
        _xdotool(env, "key", *args)
    elif verb == "type":
        _xdotool(env, "type", "--delay", "20", rest)
    elif verb == "xdotool":
        _xdotool(env, *args)
    elif verb == "close":
        subprocess.run([xclose(), window], env=env)
    elif verb == "sleep":
        time.sleep(float(args[0]))
    else:
        raise ValueError(f"unknown script command {verb!r} at frame {frame}")


# ------------------------------------------------------------- log parsing

def parse_log(text: str, allow: list[str]) -> list[Message]:
    messages: list[Message] = []
    current: Optional[Message] = None
    allowed = [re.compile(a, re.S) for a in allow]
    for line in text.splitlines():
        m = re.match(r"^\[(ERROR|WARNING|INFO)\]\s?(.*)$", line)
        if m:
            current = Message(severity=m.group(1).lower(), text=m.group(2))
            messages.append(current)
        elif DRIVER_NOISE.search(line):
            current = None
        elif current is not None and line.strip() and not line.startswith("["):
            current.text += "\n" + line          # continuation of a multi-line pMessage
        elif ID_PATTERN.search(line) or "Validation Error" in line or "Validation Warning" in line:
            # The layer's own output, printed without going through the app's callback.
            current = Message(severity="error" if "Error" in line or "VUID" in line else "warning", text=line)
            messages.append(current)
    for message in messages:
        message.ids = sorted(set(ID_PATTERN.findall(message.text)))
        for pattern, why in EXPECTED_WARNINGS:
            if message.severity == "warning" and pattern.search(message.text):
                message.expected = why
        for pattern in allowed:
            if pattern.search(message.text):
                message.expected = message.expected or f"--allow {pattern.pattern}"
    return messages


_LAYER_HEAD = re.compile(r"^Validation (Error|Warning|Performance Warning|Information): \[ ([^\]]*) \]")


def parse_layer_log(text: str, allow: list[str]) -> list[Message]:
    messages: list[Message] = []
    current: Optional[Message] = None
    for line in text.splitlines():
        m = _LAYER_HEAD.match(line)
        if m:
            kind = m.group(1)
            severity = "error" if kind == "Error" else ("info" if kind == "Information" else "warning")
            current = Message(severity=severity, text=line, ids=[m.group(2).strip()])
            messages.append(current)
        elif current is not None:
            current.text += "\n" + line
    allowed = [re.compile(a, re.S) for a in allow]
    for message in messages:
        message.text = message.text.strip()
        for pattern, why in EXPECTED_WARNINGS:
            if message.severity == "warning" and pattern.search(message.text):
                message.expected = why
        for pattern in allowed:
            if pattern.search(message.text):
                message.expected = message.expected or f"--allow {pattern.pattern}"
    return messages


def is_validation_problem(message: Message) -> bool:
    if message.expected:
        return False
    if message.severity == "error":
        return True
    return bool(message.ids) and message.severity != "info"


# ------------------------------------------------------------- the run

def run(executable: str, *, frames: int, events: dict[int, list[str]], out_dir: str, size: str = "1600x1000",
        timeout: float = 300.0, force_sync: bool = True, shader_heuristic: bool = True,
        expect: Optional[list[str]] = None, allow: Optional[list[str]] = None,
        app_args: Optional[list[str]] = None, preload: Optional[list[str]] = None,
        extra_env: Optional[dict] = None, recheck_heuristic: bool = True, log=print) -> RunResult:
    os.makedirs(out_dir, exist_ok=True)
    args = ["--frames", str(frames), *(app_args or [])]
    result = RunResult(executable=executable, args=args, out_dir=out_dir)
    hook = framehook()

    env = dict(os.environ)
    vk_env = vulkan_environment(force_sync, shader_heuristic)
    vk_env.update(extra_env or {})
    layer_log = os.path.join(out_dir, "validation.log")
    if os.path.exists(layer_log):
        os.remove(layer_log)
    vk_env.update(layer_log_environment(layer_log))
    env.update(vk_env)
    req = os.path.join(out_dir, ".hook-req")
    ack = os.path.join(out_dir, ".hook-ack")
    for fifo in (req, ack):
        if os.path.exists(fifo):
            os.remove(fifo)
        os.mkfifo(fifo)
    hooked = sorted(events)
    preload_list = ":".join([hook, *(preload or [])])
    # An ASan build must have its runtime first in the preload list.
    ldd = subprocess.run(["ldd", executable], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
    asan = re.search(r"(\S*libasan\.so\S*) => (\S+)", ldd)
    if asan:
        preload_list = f"{asan.group(2)}:{preload_list}"
        env.setdefault("ASAN_OPTIONS", "detect_leaks=0")   # drivers and the loader keep allocations to exit
        env.setdefault("UBSAN_OPTIONS", "print_stacktrace=1")
    env.update({"LD_PRELOAD": preload_list, "PF_HOOK_FRAMES": ",".join(str(f) for f in hooked),
                "PF_HOOK_REQ": req, "PF_HOOK_ACK": ack})
    result.environment = {k: v for k, v in env.items()
                          if k.startswith(("VK_", "PF_HOOK_FRAMES", "PF_SYNCVAL", "LD_PRELOAD", "VULKAN_SDK",
                                           "DISPLAY"))}
    result.sync_settings = sync_settings(env)

    # The working directory is NOT the executable's: shaders must load relative to the
    # executable (chapter 06 section 1), and a run from elsewhere proves it.
    cwd = os.path.join(out_dir, "cwd")
    os.makedirs(cwd, exist_ok=True)
    log_path = os.path.join(out_dir, "run.log")

    with Xvfb(size) as xvfb:
        env["DISPLAY"] = xvfb.display
        result.environment["DISPLAY"] = xvfb.display
        started = time.time()
        with open(log_path, "w") as log_file:
            proc = subprocess.Popen([executable, *args], cwd=cwd, env=env, stdout=log_file,
                                    stderr=subprocess.STDOUT, start_new_session=True)

            def serve():
                try:
                    with open(req) as requests, open(ack, "w") as answers:
                        for line in requests:
                            frame = int(line.split()[0])
                            window = find_window(env, proc.pid)
                            for command in events.get(frame, []):
                                try:
                                    run_command(command, frame, env, window, out_dir, result)
                                except Exception as error:   # noqa: BLE001 - reported, run continues
                                    result.failures.append(f"script at frame {frame}: {command!r}: {error}")
                            result.presents = max(result.presents, frame)
                            answers.write("go\n")
                            answers.flush()
                except OSError:
                    pass

            server = threading.Thread(target=serve, daemon=True)
            server.start()
            try:
                proc.wait(timeout)
            except subprocess.TimeoutExpired:
                result.timed_out = True
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        result.seconds = round(time.time() - started, 2)

    code = proc.returncode
    if code is not None and code < 0:
        result.signal = signal.Signals(-code).name
    else:
        result.exit_code = code
    for fifo in (req, ack):
        if os.path.exists(fifo):
            os.remove(fifo)

    with open(log_path, errors="replace") as handle:
        text = handle.read()
    result.messages = parse_log(text, allow or [])
    layer_text = ""
    if os.path.exists(layer_log):
        with open(layer_log, errors="replace") as handle:
            layer_text = handle.read()
    result.layer_messages = parse_layer_log(layer_text, allow or [])
    for pattern in expect or []:
        if not (re.search(pattern, text, re.S) or re.search(pattern, layer_text, re.S)):
            result.missing_expectations.append(pattern)

    if result.timed_out:
        result.failures.append(f"timed out after {timeout:.0f} s (hang?)")
    if result.signal:
        result.failures.append(f"crashed with {result.signal}")
    if result.exit_code not in (0, None):
        result.failures.append(f"exit code {result.exit_code}")
    sanitizer = re.findall(r"(ERROR: AddressSanitizer.*|runtime error: .*|ERROR: LeakSanitizer.*)", text)
    for line in sanitizer[:20]:
        result.failures.append(f"sanitizer: {line.strip()[:300]}")
    problems = [m for m in result.layer_messages if m.severity == "error" and not m.expected]
    program_errors = [m for m in result.messages if is_validation_problem(m)]
    if not expect:
        if problems:
            result.failures.append(f"{len(problems)} validation error(s) in validation.log")
        if program_errors:
            result.failures.append(f"{len(program_errors)} [ERROR] line(s) printed by the program")
    for pattern in result.missing_expectations:
        result.failures.append(f"expected {pattern!r} never appeared")
    for shot in result.screenshots:
        if not shot["ok"]:
            result.failures.append(f"screenshot at frame {shot['frame']} failed: {shot['error']}")
    missing_frames = [f for f in hooked if f > result.presents]
    if missing_frames and not result.failures:
        result.failures.append(f"the program presented only {result.presents} hooked frame(s); "
                               f"script frames {missing_frames} never happened")

    # The heuristic can produce false positives (the layer says so). When a run fails on
    # validation with it on, run the same thing again with it off and say which errors
    # exist only with it. The run still FAILS: such an error is a lead, not noise.
    if (recheck_heuristic and shader_heuristic and not expect
            and any("validation error" in f for f in result.failures)):
        recheck_dir = os.path.join(out_dir, "heuristic-off")
        log(f"  validation errors with syncval_shader_accesses_heuristic on; re-running without it -> {recheck_dir}")
        other = run(executable, frames=frames, events=events, out_dir=recheck_dir, size=size, timeout=timeout,
                    force_sync=force_sync, shader_heuristic=False, allow=allow, app_args=app_args,
                    preload=preload, extra_env=extra_env, recheck_heuristic=False, log=log)
        result.heuristic_recheck = recheck_dir
        without = {_message_key(m) for m in other.layer_messages if m.severity == "error"}
        for message in result.layer_messages:
            key = _message_key(message)
            if message.severity == "error" and not message.expected and key not in without \
                    and key not in result.heuristic_only:
                result.heuristic_only.append(key)
        if result.heuristic_only:
            result.failures.append(f"{len(result.heuristic_only)} distinct validation error(s) appear ONLY with "
                                   f"syncval_shader_accesses_heuristic=1 (possible false positive - investigate, "
                                   f"see {recheck_dir})")

    with open(os.path.join(out_dir, "result.json"), "w") as handle:
        json.dump(asdict(result), handle, indent=2)
    return result


def _message_key(message: Message) -> str:
    """A validation message with its handles and addresses taken out, for comparing runs."""
    lines = message.text.splitlines()
    body = lines[1] if len(lines) > 1 else message.text
    return f"{','.join(message.ids)} {re.sub(r'0x[0-9a-fA-F]+', '0x?', body)[:200]}"


def summarize(result: RunResult) -> str:
    lines = [f"run {result.executable} {' '.join(result.args)}",
             f"  output: {result.out_dir} (log: run.log)",
             f"  {'PASS' if result.ok else 'FAIL'}: exit={result.exit_code} signal={result.signal} "
             f"time={result.seconds}s"]
    lines.append("  sync validation: VK_LAYER_VALIDATE_SYNC=" + result.sync_settings.get("VK_LAYER_VALIDATE_SYNC", "?")
                 + ", VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC="
                 + result.sync_settings.get("VK_LAYER_SYNCVAL_SHADER_ACCESSES_HEURISTIC", "?")
                 + " (plus the program's own layer settings)")
    for failure in result.failures:
        lines.append(f"  FAILURE: {failure}")
    for key in result.heuristic_only:
        lines.append(f"    heuristic-only: {key}")
    layer_errors = [m for m in result.layer_messages if m.severity == "error"]
    layer_warnings = [m for m in result.layer_messages if m.severity == "warning"]
    lines.append(f"  validation.log: {len(layer_errors)} error, {len(layer_warnings)} warning "
                 f"({sum(1 for m in result.layer_messages if m.expected)} expected)")
    seen: dict[str, int] = {}
    for message in result.layer_messages:
        if message.severity == "info":
            continue
        body = message.text.splitlines()[1] if len(message.text.splitlines()) > 1 else message.text
        key = f"{message.severity}|{message.ids}|{body[:120]}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            continue
        tag = f"expected: {message.expected}" if message.expected else message.severity.upper()
        lines.append(f"    [{tag}] {message.ids} {body[:300]}")
    repeats = {k: n for k, n in seen.items() if n > 1}
    for key, n in repeats.items():
        lines.append(f"    (x{n}) {key.split('|')[1]} {key.split('|')[2][:80]}")
    program = [m for m in result.messages if m.severity in ("error", "warning")
               and not m.text.startswith("Vulkan")]
    lines.append(f"  program output: {sum(1 for m in result.messages if m.severity == 'error')} [ERROR], "
                 f"{sum(1 for m in result.messages if m.severity == 'warning')} [WARNING] lines "
                 f"(validation messages also arrive here through the program's callback)")
    for message in program:
        first = message.text.strip().splitlines()[0] if message.text.strip() else ""
        lines.append(f"    [{message.severity.upper()}{' expected' if message.expected else ''}] {first[:300]}")
    for shot in result.screenshots:
        lines.append(f"  screenshot frame {shot['frame']}: {shot['path']}")
    return "\n".join(lines)


def _default_out(name: str, label: str) -> str:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(pfbuild.BUILD_ROOT, name, "runs", f"{stamp}-{label}")


def apply_edits(copy: str, replacements: list, patches: list) -> list[str]:
    """Literal edits and diffs on a throwaway copy; each must apply exactly, or nothing runs."""
    done = []
    for rel, old, new in replacements:
        path = os.path.join(copy, rel)
        with open(path) as handle:
            text = handle.read()
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"--replace {rel}: {old!r} occurs {count} times (need exactly 1)")
        with open(path, "w") as handle:
            handle.write(text.replace(old, new))
        done.append(f"{rel}: {old!r} -> {new!r}")
    for diff in patches:
        proc = subprocess.run(["patch", "-p1", "-d", copy, "-i", os.path.abspath(diff)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"--patch {diff}:\n{proc.stdout}")
        done.append(f"applied {diff}")
    return done


def main(args) -> int:
    if args.replace or args.patch:
        copy = throwaway_copy(args.worktree, args.variant)
        for line in apply_edits(copy, args.replace, args.patch):
            print(f"variant {args.variant}: {line}")
        args.worktree = copy
        args.no_build = False
    name = args.name or pfbuild.default_name(args.worktree)
    if not args.no_build:
        built = pfbuild.build(args.worktree, configuration=args.config, compilers=tuple(args.compilers.split(",")),
                              name=name, sanitize=args.asan, msvc_approx=not args.no_msvc_approx,
                              log=lambda *_: None)
        print(pfbuild.summarize(built))
        if not built.ok:
            return 1
        executable = built.executables.get(args.compiler)
    else:
        out = os.path.join(pfbuild.BUILD_ROOT, name, args.config + ("-asan" if args.asan else ""))
        executable = next((os.path.join(dp, f) for dp, _d, fs in os.walk(os.path.join(out, args.compiler))
                           for f in fs if os.access(os.path.join(dp, f), os.X_OK) and "." not in f), None)
    if not executable:
        print(f"no {args.compiler} executable to run")
        return 1
    events = parse_script(args.script, args.shot or [])
    result = run(executable, frames=args.frames, events=events,
                 out_dir=os.path.abspath(args.out) if args.out else _default_out(name, args.config),
                 size=args.size, timeout=args.timeout, force_sync=not (args.no_force_sync or args.app_settings_only),
                 shader_heuristic=None if args.app_settings_only else not args.no_shader_heuristic,
                 expect=args.expect, allow=args.allow, app_args=shlex.split(args.app_args))
    print(summarize(result))
    return 0 if result.ok else 1


# ------------------------------------------------------------- positive control

CONTROL_EXPECT = [r"SYNC-HAZARD-WRITE-AFTER-WRITE|Hazard WRITE_AFTER_WRITE|WRITE_AFTER_WRITE"]


def chapter05_patch(root: str) -> str:
    """Chapter 05's exit check: the end-of-frame barrier's source access becomes NONE."""
    path = os.path.join(root, "Source/PillowFort/VulkanGraphics/VulkanRenderer.cpp")
    with open(path) as handle:
        text = handle.read()
    calls = [m for m in re.finditer(r"transitionImage\((?:[^;]*?)\);", text, re.S)
             if "VK_IMAGE_LAYOUT_PRESENT_SRC_KHR" in m.group(0)]
    if len(calls) != 1:
        raise RuntimeError(f"{path}: expected exactly one transitionImage(... PRESENT_SRC_KHR ...) call, "
                           f"found {len(calls)}; pass --patch")
    call = calls[0].group(0)
    if call.count("VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT") != 1:
        raise RuntimeError(f"{path}: the present barrier does not name COLOR_ATTACHMENT_WRITE once; pass --patch")
    patched = call.replace("VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT", "VK_ACCESS_2_NONE")
    with open(path, "w") as handle:
        handle.write(text.replace(call, patched))
    return f"VulkanRenderer.cpp present barrier:\n{call}\n->\n{patched}"


def throwaway_copy(root: str, label: str) -> str:
    """Source, Shaders, premake5.lua copied; Vendor symlinked. Never touches the original."""
    root = os.path.abspath(root)
    dest = os.path.join(pfbuild.BUILD_ROOT, "_throwaway", f"{pfbuild.default_name(root)}-{label}")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    for entry in os.listdir(root):
        if entry in (".git", "Build"):
            continue
        source = os.path.join(root, entry)
        if entry == "Vendor":
            os.symlink(source, os.path.join(dest, entry))
        elif os.path.isdir(source):
            shutil.copytree(source, os.path.join(dest, entry), symlinks=True)
        else:
            shutil.copy2(source, os.path.join(dest, entry))
    return dest


def syncval_compute_tools() -> tuple[str, str, str]:
    """The compute-hazard interposer and its two shaders (tools/pf_syncval_compute.cpp)."""
    lib = os.path.join(TOOLS_DIR, "pf_syncval_compute.so")
    src = os.path.join(HARNESS_DIR, "tools", "pf_syncval_compute.cpp")
    shaders = {}
    for name in ("writer", "reader"):
        glsl = os.path.join(HARNESS_DIR, "tools", f"pf_syncval_{name}.comp.glsl")
        spv = os.path.join(TOOLS_DIR, f"pf_syncval_{name}.spv")
        if not os.path.exists(spv) or os.path.getmtime(spv) < os.path.getmtime(glsl):
            os.makedirs(TOOLS_DIR, exist_ok=True)
            proc = subprocess.run([os.path.join(pfbuild.VULKAN_SDK, "Bin", "glslc"), "-fshader-stage=compute",
                                   "--target-env=vulkan1.3", glsl, "-o", spv],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if proc.returncode != 0:
                raise RuntimeError(f"glslc {glsl}: {proc.stdout}")
        shaders[name] = spv
    if not os.path.exists(lib) or os.path.getmtime(lib) < os.path.getmtime(src):
        tmp = f"{lib}.{os.getpid()}.tmp"
        proc = subprocess.run(["g++", "-std=c++20", "-O1", "-shared", "-fPIC", "-DPF_INTERPOSE",
                               f"-I{pfbuild.VULKAN_SDK}/Include", src, "-o", tmp, "-ldl"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"building pf_syncval_compute.so: {proc.stdout}")
        os.replace(tmp, lib)
    return lib, shaders["writer"], shaders["reader"]


COMPUTE_EXPECT = [r"vkCmdCopyBuffer\(\): READ_AFTER_WRITE hazard",
                  r"vkCmdDispatch\(\): READ_AFTER_WRITE hazard"]


def control_compute(args) -> int:
    """Descriptor-access tracking is live: the program's own device, two compute hazards injected."""
    name = pfbuild.default_name(args.worktree)
    built = pfbuild.build(args.worktree, compilers=("gcc",), name=name, log=lambda *_: None)
    if not built.ok:
        print(pfbuild.summarize(built))
        return 1
    lib, writer, reader = syncval_compute_tools()
    extra = {"PF_SYNCVAL_WRITER": writer, "PF_SYNCVAL_READER": reader}
    out_root = os.path.abspath(args.out) if args.out else _default_out(name, "control-compute")
    print(f"compute positive control on {args.worktree} (unmodified; hazards injected by LD_PRELOAD "
          f"right after the program's vkCreateDevice):\n"
          f"  1. dispatch writes a storage buffer, vkCmdCopyBuffer reads it, no barrier\n"
          f"  2. dispatch writes a storage buffer, a second dispatch reads it, no barrier\n")
    ok = True
    result = run(built.executables["gcc"], frames=3, events={}, out_dir=os.path.join(out_root, "heuristic-on"),
                 shader_heuristic=True, expect=args.expect or COMPUTE_EXPECT, preload=[lib], extra_env=extra)
    fired = not result.missing_expectations
    ok &= fired and result.exit_code == 0
    print(summarize(result))
    print(f"  => compute positive control [heuristic on]: {'FIRED (both hazards)' if fired else 'DID NOT FIRE'}\n")
    # The same with the layer default, to show what a run without the heuristic misses.
    quiet = run(built.executables["gcc"], frames=3, events={}, out_dir=os.path.join(out_root, "heuristic-off"),
                shader_heuristic=False, expect=args.expect or COMPUTE_EXPECT, preload=[lib], extra_env=extra)
    missed = len(quiet.missing_expectations)
    print(summarize(quiet))
    print(f"  => with the layer default (heuristic off): {missed} of {len(COMPUTE_EXPECT)} hazards went "
          f"UNREPORTED{' (expected for VVL 1.4.363)' if missed == len(COMPUTE_EXPECT) else ' - the layer default changed; update the README'}\n")
    return 0 if ok else 1


def control(args) -> int:
    if getattr(args, "compute", False):
        return control_compute(args)
    copy = throwaway_copy(args.worktree, "control")
    if args.patch:
        proc = subprocess.run(["patch", "-p1", "-d", copy, "-i", os.path.abspath(args.patch)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(proc.stdout)
        if proc.returncode != 0:
            return 1
        description = f"applied {args.patch}"
    else:
        description = chapter05_patch(copy)
    print(f"positive control in {copy}:\n{description}\n")
    built = pfbuild.build(copy, compilers=("gcc",), name=os.path.basename(copy), log=lambda *_: None)
    print(f"build: {built.out_dir}")
    if not built.ok:
        print(pfbuild.summarize(built))
        return 1
    expect = args.expect or CONTROL_EXPECT
    out_root = os.path.abspath(args.out) if args.out else _default_out(os.path.basename(copy), "control")
    heuristic = not getattr(args, "no_shader_heuristic", False)
    verdicts = []
    # First with only what the application asks for (VK_EXT_layer_settings "enables"):
    # this is the run that proves the app's own request turns sync validation on.
    for label, force in (("app-settings-only", False), ("forced-VK_LAYER_VALIDATE_SYNC", True)):
        result = run(built.executables["gcc"], frames=3, events={}, out_dir=os.path.join(out_root, label),
                     force_sync=force, shader_heuristic=heuristic, expect=expect)
        fired = not result.missing_expectations
        verdicts.append((label, fired))
        print(summarize(result))
        print(f"  => positive control [{label}]: {'FIRED' if fired else 'DID NOT FIRE'}\n")
    return 0 if all(fired for _label, fired in verdicts) else 1
