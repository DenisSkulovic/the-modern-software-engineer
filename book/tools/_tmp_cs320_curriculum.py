from pathlib import Path

path = Path(__file__).resolve().parents[1] / "curriculum.yaml"
text = path.read_text(encoding="utf-8")

old_cs220_notes = """  notes: Eight revised lectures. Language promises and JS/TS semantics first; then types/ownership, memory/GC,
    compilers/JITs, managed runtimes, native runtimes, and a language-choice workshop. Former CS320-L03
    (JS/TS under the microscope) now lives here as CS220-L02.
"""
new_cs220_notes = """  notes: Eight revised lectures. Language promises and JS/TS semantics first; then types/ownership, memory/GC,
    compilers/JITs, managed runtimes, native runtimes, and a language-choice workshop. JS/TS runtime
    semantics live here as CS220-L02 (legacy CS101-S11), not in CS320.
"""
if old_cs220_notes not in text:
    raise SystemExit("CS220 notes block not found")
text = text.replace(old_cs220_notes, new_cs220_notes, 1)

start = text.index("- code: CS320\n")
end = text.index("- code: CS330\n")
new_cs320 = """- code: CS320
  title: Operating Systems, Concurrency, and Runtimes
  discipline: CS
  level: 300
  type: core
  status: complete
  slug: operating-systems-and-concurrency
  dir: CS/CS320-operating-systems-and-concurrency
  notes: Eight revised OS/concurrency lectures. Kernel/containers first, then CPU, virtual memory,
    memory pressure, syscalls/async I/O, event-loop concurrency, threads/atomics, and forensics.
    Former JS/TS lecture remains in CS220-L02. Legacy CS101-S10 maps to L01; CS101-S09 maps to L06.
  lectures:
  - id: CS320-L01
    title: The Kernel, Processes, and Containers
    slug: the-kernel-processes-and-containers
    legacy_ids:
    - CS101-S10
    source: CS/CS320-operating-systems-and-concurrency/CS320-L01-the-kernel-processes-and-containers.md
    manuscript: revised
    edition: 2.1.0
  - id: CS320-L02
    title: CPU Scheduling, Quotas, and Contention
    slug: cpu-scheduling-quotas-and-contention
    legacy_ids: []
    source: CS/CS320-operating-systems-and-concurrency/CS320-L02-cpu-scheduling-quotas-and-contention.md
    manuscript: revised
    edition: 2.1.0
  - id: CS320-L03
    title: Virtual Memory, Pages, and Address Translation
    slug: virtual-memory-pages-and-address-translation
    legacy_ids: []
    source: CS/CS320-operating-systems-and-concurrency/CS320-L03-virtual-memory-pages-and-address-translation.md
    manuscript: revised
    edition: 2.1.0
  - id: CS320-L04
    title: Memory Pressure, Cgroups, and OOM
    slug: memory-pressure-cgroups-and-oom
    legacy_ids: []
    source: CS/CS320-operating-systems-and-concurrency/CS320-L04-memory-pressure-cgroups-and-oom.md
    manuscript: revised
    edition: 2.1.0
  - id: CS320-L05
    title: System Calls, File Descriptors, and Asynchronous I/O
    slug: system-calls-file-descriptors-and-asynchronous-io
    legacy_ids: []
    source: CS/CS320-operating-systems-and-concurrency/CS320-L05-system-calls-file-descriptors-and-asynchronous-io.md
    manuscript: revised
    edition: 2.1.0
  - id: CS320-L06
    title: Concurrency, Event Loops, and Cancellation
    slug: concurrency-event-loops-and-cancellation
    legacy_ids:
    - CS101-S09
    source: CS/CS320-operating-systems-and-concurrency/CS320-L06-concurrency-event-loops-and-cancellation.md
    manuscript: revised
    edition: 2.1.0
  - id: CS320-L07
    title: Threads, Atomics, and Memory Ordering
    slug: threads-atomics-and-memory-ordering
    legacy_ids: []
    source: CS/CS320-operating-systems-and-concurrency/CS320-L07-threads-atomics-and-memory-ordering.md
    manuscript: revised
    edition: 2.1.0
  - id: CS320-L08
    title: Operating-System and Runtime Forensics
    slug: operating-system-and-runtime-forensics
    legacy_ids: []
    source: CS/CS320-operating-systems-and-concurrency/CS320-L08-operating-system-and-runtime-forensics.md
    manuscript: revised
    edition: 2.1.0
"""
text = text[:start] + new_cs320 + text[end:]
path.write_text(text, encoding="utf-8")
print("curriculum.yaml updated")
