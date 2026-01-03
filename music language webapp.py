import streamlit as st
import time
import re
import threading
from supercollider import Server, Synth

# -------------------------
# SuperCollider Setup
# -------------------------
server = Server()

freqs = {
    "C": 261.63, "C#": 277.18, "D": 293.66, "D#": 311.13, "E": 329.63,
    "F": 349.23, "F#": 369.99, "G": 392.00, "G#": 415.30, "A": 440.00,
    "A#": 466.16, "B": 493.88
}

PREMADE_BEATS = {
    "basic": {
        "kick": [1,0,0,0,1,0,0,0],
        "snare": [0,0,1,0,0,0,1,0],
        "hihat": [1,0,1,0,1,0,1,0]
    },
    "fast": {
        "kick": [1,0,1,0,1,0,1,0],
        "snare": [0,1,0,1,0,1,0,1],
        "hihat": [1,1,1,1,1,1,1,1]
    },
    "chill": {
        "kick": [1,0,0,0,0,0,0,0],
        "snare": [0,0,0,0,1,0,0,0],
        "hihat": [1,0,0,0,1,0,0,0]
    },
    "disco": {
        "kick": [1,0,0,0,1,0,0,0],
        "snare": [0,0,1,0,0,0,1,0],
        "hihat": [0,1,0,1,0,1,0,1]
    },
}

# Global function storage
user_functions = {}

# -------------------------
# Parsing Function
# -------------------------
def parse_line(line):
    # Remove anything after a '#' (comment)
    line = line.split("#", 1)[0].strip()
    if not line:
        return None

    # --- User-defined function ---
    if line.startswith("def "):
        m = re.match(r"def\s+(\w+)\s*{(.+)}", line)
        if not m:
            return ("error", "def syntax must be: def name { commands }")
        name = m.group(1)
        body = [cmd.strip() for cmd in m.group(2).split(";") if cmd.strip()]
        user_functions[name] = body
        return ("define", name)

    # --- Function call ---
    if line in user_functions:
        return ("function_call", line)

    # --- Parallel ---
    if line.startswith("parallel"):
        m = re.match(r"parallel\s*{(.+)}", line)
        if not m:
            return ("error", "parallel syntax must be: parallel { cmd1; cmd2; ... }")
        cmds = [cmd.strip() for cmd in m.group(1).split(";") if cmd.strip()]
        return ("parallel", cmds)

    # --- Loop ---
    if line.startswith("loop"):
        m = re.match(r"loop\s+(\d+)\s*{(.+)}", line)
        if not m:
            return ("error", "loop syntax must be: loop <count> { commands }")
        count = int(m.group(1))
        inner = [cmd.strip() for cmd in m.group(2).split(";") if cmd.strip()]
        return ("loop", count, inner)

    # --- Note ---
    if line.startswith("note"):
        parts = line.split()
        if len(parts) != 3:
            return ("error", "note command must be in format: note <note> <duration>")
        note_name = parts[1].upper()
        if note_name not in freqs:
            return ("error", f"unknown note {note_name}")
        try:
            duration = float(parts[2])
        except ValueError:
            return ("error", "duration must be a number")
        return ("note", note_name, duration)

    # --- Sequence ---
    if line.startswith("seq"):
        seq = [n.upper() for n in line.split()[1:]]
        if not seq:
            return ("error", "sequence must have at least one note")
        for n in seq:
            if n not in freqs:
                return ("error", f"unknown note {n}")
        return ("sequence", seq)

    # --- Chord ---
    if line.startswith("chord"):
        parts = line.split()[1:]
        if len(parts) < 2:
            return ("error", "chord must be in format: chord <note1> <note2> ... <duration>")
        try:
            duration = float(parts[-1])
            note_names = [n.upper() for n in parts[:-1]]
        except ValueError:
            return ("error", "last argument must be duration (e.g., chord C E G 1)")
        for n in note_names:
            if n not in freqs:
                return ("error", f"unknown note {n}")
        return ("chord", note_names, duration)

    # --- Drum ---
    if line.startswith("drum"):
        parts = line.split()[1:]
        if not parts:
            return ("error", "drum command must include at least one drum name")
        return ("drum", parts)

    # --- Beat ---
    if line.startswith("beat"):
        parts = line.split()
        patter_name = parts[1] if len(parts) > 1 else "basic"
        return ("beat", patter_name)

    return ("error", f"Unknown command: {line}")


# -------------------------
# Sound Functions
# -------------------------
def play_note(note_name, duration, waveform="piano"):
    freq = freqs[note_name]
    synth = Synth(server, waveform, {"freq": freq})
    time.sleep(duration)
    synth.free()

def play_sequence(sequence, duration=0.4):
    for n in sequence:
        play_note(n, duration)

def play_chord(notes, duration):
    synths = [Synth(server, "piano", {"freq": freqs[n]}) for n in notes]
    time.sleep(duration)
    for s in synths:
        s.free()

def play_drum(name):
    Synth(server, name)

def play_beat(pattern="basic", tempo=120):
    if pattern not in PREMADE_BEATS:
        pattern = "basic"

    beat = PREMADE_BEATS[pattern]
    kick_pattern = beat["kick"]
    snare_pattern = beat["snare"]
    hihat_pattern = beat["hihat"]

    beat_interval = 60 / tempo / 2
    for i in range(8):
        if kick_pattern[i]: play_drum("kick")
        if snare_pattern[i]: play_drum("snare")
        if hihat_pattern[i]: play_drum("hihat")
        time.sleep(beat_interval)


# -------------------------
# Command Execution
# -------------------------
def run_command(cmd):
    if cmd is None:
        return ""
    if cmd[0] == "error":
        return f"⚠️ {cmd[1]}"
    if cmd[0] == "define":
        return f"✅ Defined function '{cmd[1]}'"
    if cmd[0] == "function_call":
        func_name = cmd[1]
        for c in user_functions[func_name]:
            result = run_command(parse_line(c))
        return f"🧩 Ran function '{func_name}'"
    if cmd[0] == "note":
        _, note_name, dur = cmd
        play_note(note_name, dur)
        return f"🎵 Played note {note_name} for {dur}s"
    if cmd[0] == "sequence":
        _, seq = cmd
        play_sequence(seq)
        return f"🎶 Played sequence {' '.join(seq)}"
    if cmd[0] == "chord":
        _, notes, dur = cmd
        play_chord(notes, dur)
        return f"🎹 Played chord {' '.join(notes)} for {dur}s"
    if cmd[0] == "drum":
        _, names = cmd
        for n in names:
            play_drum(n)
        return f"🥁 Played drum(s): {' '.join(names)}"
    if cmd[0] == "beat":
        _, pattern = cmd
        play_beat(pattern)
        return f"🪘 Played beat pattern: {pattern}"
    if cmd[0] == "loop":
        _, count, commands = cmd
        for _ in range(count):
            for c in commands:
                result = run_command(parse_line(c))
        return f"🔁 Loop executed {count} times"
    if cmd[0] == "parallel":
        _, commands = cmd
        threads = []
        for c in commands:
            t = threading.Thread(target=lambda: run_command(parse_line(c)))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        return f"🎼 Parallel block executed"

    return "⚠️ Command not recognized."


# -------------------------
# Streamlit Interface
# -------------------------
st.title("Cadence: Code Editor")

col1, col2 = st.columns(2)

with col1:
    user_input = st.text_area("Enter your code:", height=550)
with col2:
    if st.button("Run"):
        st.write("### Output:")
        lines = user_input.strip().split("\n")
        for line in lines:
            cmd = parse_line(line)
            result = run_command(cmd)
            st.write(result)

