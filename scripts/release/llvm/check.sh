#!/bin/sh
# Verify the repaired compiler's register constraints before linking it into lavapipe.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source=$1
features=+64bit,+sse,+sse2,+sse3,+ssse3,+sse4.1,+sse4.2,+avx,+f16c,+fma,+avx2,+avx512f,+avx512cd,+avx512bw,+avx512dq,+avx512vl,+avx512vbmi
opt -passes=verify -disable-output "$root/split-destination.ll"
for level in 1 2; do
  llc -mtriple=x86_64-redhat-linux-gnu -mcpu=znver5 -mattr="$features" \
    -code-model=large -relocation-model=static -O"$level" -verify-machineinstrs \
    "$root/split-destination.ll" -o /dev/null
done
# Declining an illegal rematerialization must still allow this existing legal
# subregister use; getRegClassConstraintEffect accounts for the subregister.
llc -mtriple=x86_64-- -run-pass=greedy -verify-machineinstrs -verify-regalloc \
  -stress-regalloc=2 "$source/llvm/test/CodeGen/X86/splitkit-remat-broken-subreg-constraint.mir" \
  -o /dev/null
