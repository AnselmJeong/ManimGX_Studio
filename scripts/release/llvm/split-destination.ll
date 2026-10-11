; SPDX-FileCopyrightText: 2026 Academa, Inc.
; SPDX-License-Identifier: MIT
;
; Compiler-only regression: a split interval's VR256X destination must not be
; rematerialized using AVX2_SETALLONES, whose destination permits only VR256.
; Generated from manimgx's square scene by Mesa 26.2.3 / LLVM 21.1.8, then reduced
; with llvm-reduce 21.1.8. The full optimized shader's SHA256 is
; 211aed8343ed48be225fde8f01b577f23dd593217eb75ed0c914fa2305034ec7.
; This reduced program is well-formed IR but is not a runtime program: do not execute it.
;
; ModuleID = '<bc file>'
source_filename = "cs5_variant0"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"

declare ptr @coro_malloc(i32)

declare void @coro_free(ptr)

define void @cs_variant(ptr noalias %0, ptr noalias %1, i32 %2, i32 %3, i32 %4, i32 %ssa_126, i32 %ssa_126128, i32 %ssa_126129, i32 %5, i32 %6, i32 %7, i32 %8, i32 %9, ptr noalias %10, ptr noalias %11) {
entry:
  br label %loop_begin

loop_begin:                                       ; preds = %endif-block142, %entry
  %12 = and i1 false, false
  br i1 %12, label %loop_begin1, label %endif-block

loop_begin1:                                      ; preds = %loop_begin1, %loop_begin
  %13 = icmp samesign ugt i32 0, 6
  br i1 %13, label %endif-block, label %loop_begin1

endif-block:                                      ; preds = %loop_begin1, %loop_begin
  %mask.0 = phi <8 x i32> [ splat (i32 -1), %loop_begin ], [ zeroinitializer, %loop_begin1 ]
  br i1 false, label %endif-block.cont3266, label %endif-block.then3267

endif-block.then3267:                             ; preds = %endif-block
  br label %endif-block.cont3266

endif-block.cont3266:                             ; preds = %endif-block.then3267, %endif-block
  %14 = call <4 x float> @llvm.x86.sse.min.ss(<4 x float> zeroinitializer, <4 x float> <float 0x41EFFFFFE0000000, float poison, float poison, float poison>) #4
  %ssa_142 = extractelement <4 x float> %14, i64 0
  %ssa_143 = call i32 @llvm.fptoui.sat.i32.f32(float %ssa_142) #4
  %15 = insertelement <8 x i32> poison, i32 %ssa_143, i64 0
  %16 = shufflevector <8 x i32> %15, <8 x i32> poison, <8 x i32> zeroinitializer
  %ssa_144 = icmp ult <8 x i32> zeroinitializer, %16
  br i1 false, label %endif-block.then, label %endif-block.cont

endif-block.then:                                 ; preds = %endif-block.cont3266
  br label %endif-block.cont

endif-block.cont:                                 ; preds = %endif-block.then, %endif-block.cont3266
  %ssa_148 = call i32 @llvm.fptoui.sat.i32.f32(float 0.000000e+00) #4
  %17 = insertelement <8 x i32> poison, i32 %ssa_148, i64 0
  %18 = shufflevector <8 x i32> %17, <8 x i32> poison, <8 x i32> zeroinitializer
  %ssa_149 = icmp ult <8 x i32> zeroinitializer, %18
  %.not4901 = and <8 x i1> %ssa_149, %ssa_144
  br i1 false, label %endif-block132, label %if-true-block133

if-true-block133:                                 ; preds = %endif-block.cont
  br i1 false, label %if-true-block133.then, label %if-true-block133.cont

if-true-block133.then:                            ; preds = %if-true-block133
  br label %if-true-block133.cont

if-true-block133.cont:                            ; preds = %if-true-block133.then, %if-true-block133
  br label %endif-block132

endif-block132:                                   ; preds = %if-true-block133.cont, %endif-block.cont
  %19 = xor <8 x i1> %.not4901, splat (i1 true)
  %20 = zext <8 x i1> %19 to <8 x i8>
  %21 = or <8 x i8> zeroinitializer, %20
  %ssa_167.not = icmp eq <8 x i8> %21, zeroinitializer
  %22 = sext <8 x i1> %ssa_167.not to <8 x i32>
  %23 = icmp ne <8 x i32> %mask.0, zeroinitializer
  %24 = select <8 x i1> %ssa_167.not, <8 x i1> %23, <8 x i1> zeroinitializer
  %25 = bitcast <8 x i1> %24 to i8
  %any_active141.not = icmp eq i8 %25, 0
  br i1 %any_active141.not, label %endif-block142, label %if-true-block143

if-true-block143:                                 ; preds = %endif-block132
  br i1 false, label %if-true-block143.then3265, label %if-true-block143.cont3264

if-true-block143.then3265:                        ; preds = %if-true-block143
  br label %if-true-block143.cont3264

if-true-block143.cont3264:                        ; preds = %if-true-block143.then3265, %if-true-block143
  br i1 false, label %if-true-block143.then3263, label %if-true-block143.cont3262

if-true-block143.then3263:                        ; preds = %if-true-block143.cont3264
  br label %if-true-block143.cont3262

if-true-block143.cont3262:                        ; preds = %if-true-block143.then3263, %if-true-block143.cont3264
  br i1 false, label %if-true-block143.then3261, label %if-true-block143.cont3260

if-true-block143.then3261:                        ; preds = %if-true-block143.cont3262
  br label %if-true-block143.cont3260

if-true-block143.cont3260:                        ; preds = %if-true-block143.then3261, %if-true-block143.cont3262
  br i1 false, label %if-true-block143.then3259, label %if-true-block143.cont3258

if-true-block143.then3259:                        ; preds = %if-true-block143.cont3260
  br label %if-true-block143.cont3258

if-true-block143.cont3258:                        ; preds = %if-true-block143.then3259, %if-true-block143.cont3260
  br i1 false, label %if-true-block143.then3257, label %if-true-block143.cont3256

if-true-block143.then3257:                        ; preds = %if-true-block143.cont3258
  br label %if-true-block143.cont3256

if-true-block143.cont3256:                        ; preds = %if-true-block143.then3257, %if-true-block143.cont3258
  br i1 false, label %if-true-block143.then3255, label %if-true-block143.cont3254

if-true-block143.then3255:                        ; preds = %if-true-block143.cont3256
  br label %if-true-block143.cont3254

if-true-block143.cont3254:                        ; preds = %if-true-block143.then3255, %if-true-block143.cont3256
  br i1 false, label %if-true-block143.then, label %if-true-block143.cont

if-true-block143.then:                            ; preds = %if-true-block143.cont3254
  br label %if-true-block143.cont

if-true-block143.cont:                            ; preds = %if-true-block143.then, %if-true-block143.cont3254
  br i1 false, label %endif-block149, label %if-true-block150

if-true-block150:                                 ; preds = %if-true-block143.cont
  br i1 true, label %if-true-block153, label %endif-block152

if-true-block153:                                 ; preds = %if-true-block150
  %26 = call { <8 x float>, <8 x float>, <8 x float>, <8 x float>, <8 x i1> } null(i64 0, i64 undef, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer)
  br label %endif-block152

endif-block152:                                   ; preds = %if-true-block153, %if-true-block150
  br i1 false, label %endif-block152.then, label %endif-block152.cont

endif-block152.then:                              ; preds = %endif-block152
  br label %endif-block152.cont

endif-block152.cont:                              ; preds = %endif-block152.then, %endif-block152
  br i1 false, label %endif-block158, label %if-true-block159

if-true-block159:                                 ; preds = %endif-block152.cont
  br label %endif-block158

endif-block158:                                   ; preds = %if-true-block159, %endif-block152.cont
  %any_active160.not = icmp eq i8 0, 0
  br i1 %any_active160.not, label %endif-block149, label %if-true-block162

if-true-block162:                                 ; preds = %endif-block158
  br i1 true, label %if-true-block167, label %endif-block166

if-true-block167:                                 ; preds = %if-true-block162
  br label %endif-block166

endif-block166:                                   ; preds = %if-true-block167, %if-true-block162
  %27 = select <8 x i1> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer
  %28 = select <8 x i1> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer
  %29 = select <8 x i1> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer
  %30 = select <8 x i1> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer
  br label %endif-block149

endif-block149:                                   ; preds = %endif-block166, %endif-block158, %if-true-block143.cont
  %reg122.0 = phi <8 x i32> [ zeroinitializer, %if-true-block143.cont ], [ %27, %endif-block166 ], [ zeroinitializer, %endif-block158 ]
  %reg121.0 = phi <8 x i32> [ zeroinitializer, %if-true-block143.cont ], [ %30, %endif-block166 ], [ zeroinitializer, %endif-block158 ]
  %reg120.0 = phi <8 x i32> [ zeroinitializer, %if-true-block143.cont ], [ %29, %endif-block166 ], [ zeroinitializer, %endif-block158 ]
  %reg119.0 = phi <8 x i32> [ zeroinitializer, %if-true-block143.cont ], [ %28, %endif-block166 ], [ zeroinitializer, %endif-block158 ]
  %31 = xor <8 x i1> zeroinitializer, %ssa_167.not
  %any_active171.not = icmp eq i8 0, 0
  br i1 %any_active171.not, label %endif-block172, label %if-true-block173

if-true-block173:                                 ; preds = %endif-block149
  %32 = select <8 x i1> %31, <8 x i32> zeroinitializer, <8 x i32> %reg122.0
  br label %endif-block172

endif-block172:                                   ; preds = %if-true-block173, %endif-block149
  %reg122.3 = phi <8 x i32> [ %32, %if-true-block173 ], [ %reg122.0, %endif-block149 ]
  %reg121.3 = phi <8 x i32> [ zeroinitializer, %if-true-block173 ], [ %reg121.0, %endif-block149 ]
  %reg120.3 = phi <8 x i32> [ zeroinitializer, %if-true-block173 ], [ %reg120.0, %endif-block149 ]
  %reg119.3 = phi <8 x i32> [ zeroinitializer, %if-true-block173 ], [ %reg119.0, %endif-block149 ]
  br i1 true, label %if-true-block178, label %endif-block177

if-true-block178:                                 ; preds = %endif-block172
  br label %endif-block177

endif-block177:                                   ; preds = %if-true-block178, %endif-block172
  br i1 true, label %if-true-block200, label %endif-block199

if-true-block200:                                 ; preds = %endif-block177
  br label %endif-block199

endif-block199:                                   ; preds = %if-true-block200, %endif-block177
  br i1 false, label %endif-block199.then3253, label %endif-block199.cont3252

endif-block199.then3253:                          ; preds = %endif-block199
  br label %endif-block199.cont3252

endif-block199.cont3252:                          ; preds = %endif-block199.then3253, %endif-block199
  br i1 false, label %endif-block199.then, label %endif-block199.cont

endif-block199.then:                              ; preds = %endif-block199.cont3252
  br label %endif-block199.cont

endif-block199.cont:                              ; preds = %endif-block199.then, %endif-block199.cont3252
  br i1 false, label %endif-block205, label %if-true-block206

if-true-block206:                                 ; preds = %endif-block199.cont
  br i1 true, label %if-true-block211, label %endif-block210

if-true-block211:                                 ; preds = %if-true-block206
  br label %endif-block210

endif-block210:                                   ; preds = %if-true-block211, %if-true-block206
  br i1 false, label %endif-block210.then, label %endif-block210.cont

endif-block210.then:                              ; preds = %endif-block210
  br label %endif-block210.cont

endif-block210.cont:                              ; preds = %endif-block210.then, %endif-block210
  br i1 false, label %endif-block218, label %if-true-block219

if-true-block219:                                 ; preds = %endif-block210.cont
  br label %endif-block218

endif-block218:                                   ; preds = %if-true-block219, %endif-block210.cont
  br label %endif-block205

endif-block205:                                   ; preds = %endif-block218, %endif-block199.cont
  %33 = load i32, ptr null, align 4
  %34 = ashr i32 %33, 2
  %35 = insertelement <8 x i32> poison, i32 %34, i64 0
  %36 = shufflevector <8 x i32> %35, <8 x i32> poison, <8 x i32> zeroinitializer
  %oob_cmp231 = icmp ult <8 x i32> zeroinitializer, %36
  %mask232 = and <8 x i1> %24, %oob_cmp231
  %ssa_278 = call <8 x i32> @llvm.masked.gather.v8i32.v8p0(<8 x ptr> zeroinitializer, i32 4, <8 x i1> %mask232, <8 x i32> zeroinitializer) #4
  %37 = load i32, ptr null, align 4
  %38 = icmp ugt i32 %37, 5
  br i1 %38, label %endif-block205.then, label %endif-block205.cont

endif-block205.then:                              ; preds = %endif-block205
  %39 = load ptr, ptr null, align 8
  br label %endif-block205.cont

endif-block205.cont:                              ; preds = %endif-block205.then, %endif-block205
  %40 = select <8 x i1> %ssa_167.not, <8 x i32> splat (i32 2137108966), <8 x i32> zeroinitializer
  br label %bgnloop

bgnloop:                                          ; preds = %endif-block281, %endif-block205.cont
  %.04828 = phi <8 x i32> [ splat (i32 -1), %endif-block205.cont ], [ %break_full, %endif-block281 ]
  %reg127.0 = phi <8 x i32> [ zeroinitializer, %endif-block205.cont ], [ %reg127.1, %endif-block281 ]
  %reg126.0 = phi <8 x i32> [ zeroinitializer, %endif-block205.cont ], [ %reg126.1, %endif-block281 ]
  %reg125.0 = phi <8 x i32> [ zeroinitializer, %endif-block205.cont ], [ %reg125.1, %endif-block281 ]
  %reg124.0 = phi <8 x i32> [ zeroinitializer, %endif-block205.cont ], [ %reg124.1, %endif-block281 ]
  %reg123.0 = phi <8 x i32> [ zeroinitializer, %endif-block205.cont ], [ %reg123.1, %endif-block281 ]
  %reg122.4 = phi <8 x i32> [ %reg122.3, %endif-block205.cont ], [ zeroinitializer, %endif-block281 ]
  %reg121.4 = phi <8 x i32> [ %reg121.3, %endif-block205.cont ], [ zeroinitializer, %endif-block281 ]
  %reg120.4 = phi <8 x i32> [ %reg120.3, %endif-block205.cont ], [ zeroinitializer, %endif-block281 ]
  %reg119.4 = phi <8 x i32> [ %reg119.3, %endif-block205.cont ], [ zeroinitializer, %endif-block281 ]
  %reg118.0 = phi <8 x i8> [ zeroinitializer, %endif-block205.cont ], [ %251, %endif-block281 ]
  %reg115.0 = phi <8 x i32> [ %22, %endif-block205.cont ], [ zeroinitializer, %endif-block281 ]
  %reg114.0 = phi <8 x i32> [ zeroinitializer, %endif-block205.cont ], [ %reg114.1, %endif-block281 ]
  %reg113.0 = phi <8 x i32> [ %40, %endif-block205.cont ], [ %reg113.1, %endif-block281 ]
  %41 = extractelement <8 x i32> %reg115.0, i32 0
  %ssa_288 = icmp eq i32 %41, 0
  %42 = insertelement <8 x i1> poison, i1 %ssa_288, i64 0
  %43 = shufflevector <8 x i1> %42, <8 x i1> poison, <8 x i32> zeroinitializer
  %ssa_296 = icmp uge <8 x i32> zeroinitializer, %ssa_278
  %ssa_298.not = or <8 x i1> zeroinitializer, %ssa_296
  %ssa_300 = or <8 x i1> %43, %ssa_298.not
  %44 = and <8 x i1> %ssa_300, %ssa_167.not
  %break_full = select <8 x i1> %44, <8 x i32> zeroinitializer, <8 x i32> %.04828
  %maskfull252 = select <8 x i1> %ssa_167.not, <8 x i32> %break_full, <8 x i32> zeroinitializer
  %any_active253.not = icmp eq i8 0, 0
  %ssa_327 = call <8 x float> @llvm.x86.avx.min.ps.256(<8 x float> zeroinitializer, <8 x float> splat (float 0x41DFFFFFE0000000)) #4
  %ssa_329 = call <8 x i32> @llvm.fptosi.sat.v8i32.v8f32(<8 x float> %ssa_327) #4
  %45 = bitcast <8 x i32> %maskfull252 to <8 x float>
  %46 = bitcast <8 x i32> %ssa_329 to <8 x float>
  %47 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %46, <8 x float> %45) #4
  %48 = bitcast <8 x float> %47 to <8 x i32>
  %ssa_339 = call <8 x i32> @llvm.smin.v8i32(<8 x i32> %48, <8 x i32> zeroinitializer)
  %ssa_340 = icmp slt <8 x i32> %ssa_339, zeroinitializer
  %49 = or <8 x i1> %ssa_340, zeroinitializer
  %ssa_348 = or <8 x i1> %49, zeroinitializer
  %ssa_349 = xor <8 x i1> %ssa_348, splat (i1 true)
  %50 = and <8 x i1> %ssa_167.not, %ssa_349
  %51 = sext <8 x i1> %50 to <8 x i32>
  %maskfull279 = select <8 x i1> %50, <8 x i32> %break_full, <8 x i32> zeroinitializer
  %52 = and <8 x i32> %maskfull279, %mask.0
  %53 = icmp ne <8 x i32> %52, zeroinitializer
  %any_active280.not = icmp eq i8 0, 0
  br i1 %any_active280.not, label %endif-block281, label %if-true-block282

if-true-block282:                                 ; preds = %bgnloop
  %54 = load i32, ptr null, align 4
  %55 = ashr i32 %54, 2
  %56 = insertelement <8 x i32> poison, i32 %55, i64 0
  %57 = shufflevector <8 x i32> %56, <8 x i32> poison, <8 x i32> zeroinitializer
  %oob_cmp338 = icmp ult <8 x i32> zeroinitializer, %57
  %mask339 = and <8 x i1> %53, %oob_cmp338
  %ssa_370342 = call <8 x i32> @llvm.masked.gather.v8i32.v8p0(<8 x ptr> zeroinitializer, i32 4, <8 x i1> %mask339, <8 x i32> zeroinitializer) #4
  %58 = bitcast <8 x i32> %reg113.0 to <8 x float>
  br label %bgnloop343

bgnloop343:                                       ; preds = %endif-block1331, %if-true-block282
  %.04830 = phi <8 x i32> [ %break_full, %if-true-block282 ], [ %.04829, %endif-block1331 ]
  %reg127.2 = phi <8 x i32> [ %reg127.0, %if-true-block282 ], [ %reg127.3, %endif-block1331 ]
  %reg126.2 = phi <8 x i32> [ %reg126.0, %if-true-block282 ], [ %reg126.3, %endif-block1331 ]
  %reg125.2 = phi <8 x i32> [ %reg125.0, %if-true-block282 ], [ %reg125.3, %endif-block1331 ]
  %reg124.2 = phi <8 x i32> [ %reg124.0, %if-true-block282 ], [ %reg124.3, %endif-block1331 ]
  %reg123.2 = phi <8 x i32> [ %reg123.0, %if-true-block282 ], [ %reg123.3, %endif-block1331 ]
  %reg122.6 = phi <8 x i32> [ %reg122.4, %if-true-block282 ], [ %reg122.7, %endif-block1331 ]
  %reg121.6 = phi <8 x i32> [ %reg121.4, %if-true-block282 ], [ %reg121.7, %endif-block1331 ]
  %reg120.6 = phi <8 x i32> [ %reg120.4, %if-true-block282 ], [ %reg120.7, %endif-block1331 ]
  %reg119.6 = phi <8 x i32> [ %reg119.4, %if-true-block282 ], [ %reg119.7, %endif-block1331 ]
  %reg118.2 = phi <8 x i8> [ %reg118.0, %if-true-block282 ], [ %reg118.3, %endif-block1331 ]
  %reg114.2 = phi <8 x i32> [ %reg114.0, %if-true-block282 ], [ %247, %endif-block1331 ]
  %reg113.2 = phi <8 x float> [ %58, %if-true-block282 ], [ %248, %endif-block1331 ]
  %reg108.2 = phi <8 x i32> [ zeroinitializer, %if-true-block282 ], [ %reg108.3, %endif-block1331 ]
  %reg99.2 = phi <8 x i32> [ zeroinitializer, %if-true-block282 ], [ %70, %endif-block1331 ]
  %reg98.2 = phi <8 x i32> [ zeroinitializer, %if-true-block282 ], [ %66, %endif-block1331 ]
  %59 = xor <8 x i8> zeroinitializer, splat (i8 -1)
  %60 = and <8 x i8> %reg118.2, %59
  %61 = or <8 x i8> zeroinitializer, %60
  %break_full349 = xor <8 x i32> zeroinitializer, %.04830
  %maskfull355 = select <8 x i1> %50, <8 x i32> %break_full349, <8 x i32> zeroinitializer
  %ssa_376 = icmp eq <8 x i32> %reg99.2, zeroinitializer
  %ssa_377.neg = sext <8 x i1> %ssa_376 to <8 x i32>
  %ssa_380 = add <8 x i32> %reg98.2, %ssa_377.neg
  %62 = bitcast <8 x i32> %maskfull355 to <8 x float>
  %63 = bitcast <8 x i32> %ssa_380 to <8 x float>
  %64 = bitcast <8 x i32> %reg98.2 to <8 x float>
  %65 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %64, <8 x float> %63, <8 x float> %62) #4
  %66 = bitcast <8 x float> %65 to <8 x i32>
  %ssa_382 = add <8 x i32> %reg99.2, splat (i32 -1)
  %67 = bitcast <8 x i32> %ssa_382 to <8 x float>
  %68 = bitcast <8 x i32> %reg99.2 to <8 x float>
  %69 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %68, <8 x float> %67, <8 x float> %62) #4
  %70 = bitcast <8 x float> %69 to <8 x i32>
  %71 = and <8 x i32> %maskfull355, %mask.0
  %exec_bitvec356 = icmp ne <8 x i32> %71, zeroinitializer
  %exec_bitmask357 = bitcast <8 x i1> %exec_bitvec356 to i8
  %72 = zext i8 %exec_bitmask357 to i32
  %73 = call range(i32 0, 33) i32 @llvm.cttz.i32(i32 %72, i1 false) #4
  %first_active_or_0359 = select i1 false, i32 0, i32 %73
  %74 = extractelement <8 x i32> zeroinitializer, i32 %first_active_or_0359
  %ssa_384 = icmp ugt i32 %74, 2
  %75 = insertelement <8 x i1> poison, i1 %ssa_384, i64 0
  %76 = shufflevector <8 x i1> %75, <8 x i1> poison, <8 x i32> zeroinitializer
  %77 = and <8 x i1> %76, %50
  %maskfull361 = select <8 x i1> %77, <8 x i32> %break_full349, <8 x i32> zeroinitializer
  %78 = trunc <8 x i32> %maskfull361 to <8 x i8>
  %79 = xor <8 x i8> %78, splat (i8 -1)
  %80 = and <8 x i8> %61, %79
  %81 = or <8 x i8> zeroinitializer, %80
  %break_full363 = xor <8 x i32> %maskfull361, %break_full349
  %82 = bitcast <8 x i32> %break_full363 to <8 x float>
  %83 = select <8 x i1> %50, <8 x float> %82, <8 x float> zeroinitializer
  %84 = bitcast <8 x i32> zeroinitializer to <8 x float>
  %85 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %84, <8 x float> %83) #4
  %ssa_391 = icmp eq <8 x i32> %ssa_370342, splat (i32 -1)
  %86 = select <8 x i1> %ssa_391, <8 x i32> %51, <8 x i32> zeroinitializer
  %maskfull371 = and <8 x i32> %break_full363, %86
  %87 = and <8 x i32> %maskfull371, %mask.0
  %88 = icmp ne <8 x i32> %87, zeroinitializer
  %89 = bitcast <8 x i1> %88 to i8
  %any_active372.not = icmp eq i8 %89, 0
  br i1 %any_active372.not, label %endif-block373, label %if-true-block374

if-true-block374:                                 ; preds = %bgnloop343
  %ssa_394 = call <8 x i32> @llvm.x86.avx2.gather.d.d.256(<8 x i32> undef, ptr nonnull null, <8 x i32> zeroinitializer, <8 x i32> splat (i32 -1), i8 1) #4
  %ssa_396.not = icmp ugt <8 x i32> %ssa_394, splat (i32 2)
  %ssa_397 = select <8 x i1> %ssa_396.not, <8 x i32> splat (i32 -1), <8 x i32> zeroinitializer
  %ssa_401 = select <8 x i1> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> %ssa_397
  %ssa_402.not = icmp eq <8 x i32> %ssa_401, splat (i32 -1)
  %90 = select <8 x i1> %ssa_402.not, <8 x i32> zeroinitializer, <8 x i32> %86
  %maskfull380 = and <8 x i32> %90, %break_full363
  %91 = and <8 x i32> %maskfull380, %mask.0
  %92 = icmp ne <8 x i32> %91, zeroinitializer
  %93 = bitcast <8 x i1> %92 to i8
  %any_active381.not = icmp eq i8 %93, 0
  br i1 %any_active381.not, label %endif-block382, label %if-true-block383

if-true-block383:                                 ; preds = %if-true-block374
  br i1 false, label %endif-block388, label %if-true-block389

if-true-block389:                                 ; preds = %if-true-block383
  br i1 true, label %if-true-block395, label %endif-block394

if-true-block395:                                 ; preds = %if-true-block389
  %94 = call { <8 x float>, <8 x float>, <8 x float>, <8 x float>, <8 x i1> } null(i64 0, i64 undef, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer)
  br label %endif-block394

endif-block394:                                   ; preds = %if-true-block395, %if-true-block389
  br label %endif-block388

endif-block388:                                   ; preds = %endif-block394, %if-true-block383
  br i1 false, label %endif-block406, label %if-true-block407

if-true-block407:                                 ; preds = %endif-block388
  br label %endif-block419

endif-block419:                                   ; preds = %if-true-block407
  br i1 false, label %endif-block433, label %if-true-block434

if-true-block434:                                 ; preds = %endif-block419
  br i1 false, label %endif-block458, label %if-true-block459

if-true-block459:                                 ; preds = %if-true-block434
  br label %endif-block458

endif-block458:                                   ; preds = %if-true-block459, %if-true-block434
  br label %endif-block433

endif-block433:                                   ; preds = %endif-block458, %endif-block419
  br i1 false, label %endif-block406, label %if-true-block667

if-true-block667:                                 ; preds = %endif-block433
  br label %endif-block671

endif-block671:                                   ; preds = %if-true-block667
  br i1 false, label %endif-block406, label %if-true-block991

if-true-block991:                                 ; preds = %endif-block671
  br i1 false, label %endif-block1055, label %if-true-block1056

if-true-block1056:                                ; preds = %if-true-block991
  br label %endif-block1055

endif-block1055:                                  ; preds = %if-true-block1056, %if-true-block991
  br label %endif-block406

endif-block406:                                   ; preds = %endif-block1055, %endif-block671, %endif-block433, %endif-block388
  br label %endif-block382

endif-block382:                                   ; preds = %endif-block406, %if-true-block374
  br i1 false, label %endif-block373, label %if-true-block1318

if-true-block1318:                                ; preds = %endif-block382
  br label %endif-block373

endif-block373:                                   ; preds = %if-true-block1318, %endif-block382, %bgnloop343
  %95 = xor <8 x i32> %86, %51
  %maskfull1322 = and <8 x i32> %95, %break_full363
  %96 = and <8 x i32> %maskfull1322, %mask.0
  %97 = icmp ne <8 x i32> %96, zeroinitializer
  %98 = bitcast <8 x i1> %97 to i8
  %any_active1323.not = icmp eq i8 %98, 0
  br i1 %any_active1323.not, label %endif-block1324, label %if-true-block1325

if-true-block1325:                                ; preds = %endif-block373
  %99 = and <8 x i32> zeroinitializer, zeroinitializer
  %100 = and <8 x i32> zeroinitializer, zeroinitializer
  %101 = and <8 x i32> zeroinitializer, zeroinitializer
  %102 = and <8 x i32> zeroinitializer, zeroinitializer
  %103 = bitcast <8 x i32> %maskfull1322 to <8 x float>
  %104 = bitcast <8 x i32> zeroinitializer to <8 x float>
  %105 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %104, <8 x float> zeroinitializer, <8 x float> %103) #4
  %106 = bitcast <8 x float> %105 to <8 x i32>
  %107 = or <8 x i32> zeroinitializer, zeroinitializer
  br label %endif-block1324

endif-block1324:                                  ; preds = %if-true-block1325, %endif-block373
  %reg96.8 = phi <8 x i32> [ %106, %if-true-block1325 ], [ zeroinitializer, %endif-block373 ]
  %reg94.7 = phi <8 x i32> [ %107, %if-true-block1325 ], [ zeroinitializer, %endif-block373 ]
  %reg88.17 = phi <8 x i32> [ %102, %if-true-block1325 ], [ zeroinitializer, %endif-block373 ]
  %reg87.17 = phi <8 x i32> [ %99, %if-true-block1325 ], [ zeroinitializer, %endif-block373 ]
  %reg86.17 = phi <8 x i32> [ %100, %if-true-block1325 ], [ zeroinitializer, %endif-block373 ]
  %reg85.17 = phi <8 x i32> [ %101, %if-true-block1325 ], [ zeroinitializer, %endif-block373 ]
  %108 = select <8 x i1> zeroinitializer, <8 x float> zeroinitializer, <8 x float> splat (float 3.000000e+00)
  %109 = bitcast <8 x i32> %reg96.8 to <8 x float>
  %ssa_2977 = fcmp uge <8 x float> %108, %109
  %ssa_2978 = icmp eq <8 x i8> zeroinitializer, zeroinitializer
  %ssa_2979.not = and <8 x i1> %ssa_2977, %ssa_2978
  %110 = and <8 x i1> %ssa_2979.not, %50
  %maskfull1329 = and <8 x i32> %break_full363, %mask.0
  %111 = icmp ne <8 x i32> %maskfull1329, zeroinitializer
  %112 = select <8 x i1> %110, <8 x i1> %111, <8 x i1> zeroinitializer
  %113 = bitcast <8 x i1> %112 to i8
  %any_active1330.not = icmp eq i8 %113, 0
  br i1 %any_active1330.not, label %endif-block1331, label %if-true-block1332

if-true-block1332:                                ; preds = %endif-block1324
  br label %endif-block1336

endif-block1336:                                  ; preds = %if-true-block1332
  %114 = xor <8 x i1> zeroinitializer, %110
  %115 = trunc <8 x i32> %break_full363 to <8 x i8>
  %116 = select <8 x i1> %114, <8 x i8> %115, <8 x i8> zeroinitializer
  %117 = and <8 x i8> %116, splat (i8 1)
  %118 = or <8 x i8> zeroinitializer, %117
  %ssa_3068 = icmp ne <8 x i8> %118, zeroinitializer
  %119 = and <8 x i1> %ssa_3068, %110
  %maskfull1459 = select <8 x i1> %119, <8 x i32> %break_full363, <8 x i32> zeroinitializer
  %120 = trunc <8 x i32> %maskfull1459 to <8 x i8>
  %121 = xor <8 x i8> %120, splat (i8 -1)
  %122 = and <8 x i8> %81, %121
  %break_full1461 = xor <8 x i32> %maskfull1459, %break_full363
  %123 = and <8 x i1> %110, %ssa_391
  %any_active1470.not = icmp eq i8 0, 0
  br i1 %any_active1470.not, label %endif-block1471, label %if-true-block1472

if-true-block1472:                                ; preds = %endif-block1336
  %124 = bitcast <8 x i32> %reg94.7 to <8 x float>
  %ssa_3072 = fcmp oge <8 x float> %124, splat (float 0x3FEFFFEB00000000)
  %125 = and <8 x i1> %123, %ssa_3072
  %maskfull1474 = select <8 x i1> %125, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %any_active1475.not = icmp eq i8 0, 0
  br i1 %any_active1475.not, label %endif-block1476, label %if-true-block1477

if-true-block1477:                                ; preds = %if-true-block1472
  %126 = bitcast <8 x i32> %reg85.17 to <8 x float>
  %ssa_3075 = fmul <8 x float> %124, %126
  %127 = bitcast <8 x i32> %reg86.17 to <8 x float>
  %ssa_3078 = fmul <8 x float> %124, %127
  %128 = bitcast <8 x i32> %reg87.17 to <8 x float>
  %ssa_3081 = fmul <8 x float> %124, %128
  %129 = bitcast <8 x i32> %reg88.17 to <8 x float>
  %ssa_3084 = fmul <8 x float> %124, %129
  %ssa_3086 = fsub <8 x float> splat (float 1.000000e+00), %ssa_3084
  %130 = bitcast <8 x i32> %reg119.6 to <8 x float>
  %ssa_3088 = fmul <8 x float> %ssa_3086, %130
  %131 = bitcast <8 x i32> %reg120.6 to <8 x float>
  %ssa_3090 = fmul <8 x float> %ssa_3086, %131
  %132 = bitcast <8 x i32> %reg121.6 to <8 x float>
  %ssa_3092 = fmul <8 x float> %ssa_3086, %132
  %133 = bitcast <8 x i32> %reg122.6 to <8 x float>
  %ssa_3094 = fmul <8 x float> %ssa_3086, %133
  %ssa_3095 = fadd <8 x float> %ssa_3088, %ssa_3075
  %134 = bitcast <8 x i32> %maskfull1474 to <8 x float>
  %135 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %130, <8 x float> %ssa_3095, <8 x float> %134) #4
  %136 = bitcast <8 x float> %135 to <8 x i32>
  %ssa_3096 = fadd <8 x float> %ssa_3078, %ssa_3090
  %137 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %131, <8 x float> %ssa_3096, <8 x float> %134) #4
  %138 = bitcast <8 x float> %137 to <8 x i32>
  %ssa_3097 = fadd <8 x float> %ssa_3081, %ssa_3092
  %139 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %132, <8 x float> %ssa_3097, <8 x float> %134) #4
  %140 = bitcast <8 x float> %139 to <8 x i32>
  %ssa_3098 = fadd <8 x float> %ssa_3084, %ssa_3094
  %141 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %133, <8 x float> %ssa_3098, <8 x float> %134) #4
  %142 = bitcast <8 x float> %141 to <8 x i32>
  %143 = bitcast <8 x i32> %reg124.2 to <8 x float>
  %ssa_3100 = fmul <8 x float> %ssa_3086, %143
  %144 = bitcast <8 x i32> %reg125.2 to <8 x float>
  %ssa_3102 = fmul <8 x float> %ssa_3086, %144
  %145 = bitcast <8 x i32> %reg126.2 to <8 x float>
  %ssa_3104 = fmul <8 x float> %ssa_3086, %145
  %146 = bitcast <8 x i32> %reg127.2 to <8 x float>
  %ssa_3106 = fmul <8 x float> %ssa_3086, %146
  %ssa_3107 = fadd <8 x float> %ssa_3100, %ssa_3075
  %147 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %143, <8 x float> %ssa_3107, <8 x float> %134) #4
  %148 = bitcast <8 x float> %147 to <8 x i32>
  %ssa_3108 = fadd <8 x float> %ssa_3078, %ssa_3102
  %149 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %144, <8 x float> %ssa_3108, <8 x float> %134) #4
  %150 = bitcast <8 x float> %149 to <8 x i32>
  %ssa_3109 = fadd <8 x float> %ssa_3081, %ssa_3104
  %151 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %145, <8 x float> %ssa_3109, <8 x float> %134) #4
  %152 = bitcast <8 x float> %151 to <8 x i32>
  %ssa_3110 = fadd <8 x float> %ssa_3084, %ssa_3106
  %153 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %146, <8 x float> %ssa_3110, <8 x float> %134) #4
  %154 = bitcast <8 x float> %153 to <8 x i32>
  br label %endif-block1476

endif-block1476:                                  ; preds = %if-true-block1477, %if-true-block1472
  %reg127.5 = phi <8 x i32> [ %154, %if-true-block1477 ], [ %reg127.2, %if-true-block1472 ]
  %reg126.5 = phi <8 x i32> [ %152, %if-true-block1477 ], [ %reg126.2, %if-true-block1472 ]
  %reg125.5 = phi <8 x i32> [ %150, %if-true-block1477 ], [ %reg125.2, %if-true-block1472 ]
  %reg124.5 = phi <8 x i32> [ %148, %if-true-block1477 ], [ %reg124.2, %if-true-block1472 ]
  %reg122.9 = phi <8 x i32> [ %142, %if-true-block1477 ], [ %reg122.6, %if-true-block1472 ]
  %reg121.9 = phi <8 x i32> [ %140, %if-true-block1477 ], [ %reg121.6, %if-true-block1472 ]
  %reg120.9 = phi <8 x i32> [ %138, %if-true-block1477 ], [ %reg120.6, %if-true-block1472 ]
  %reg119.9 = phi <8 x i32> [ %136, %if-true-block1477 ], [ %reg119.6, %if-true-block1472 ]
  %155 = xor <8 x i1> %125, %123
  %maskfull1479 = select <8 x i1> %155, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %156 = and <8 x i32> %maskfull1479, %mask.0
  %157 = icmp ne <8 x i32> %156, zeroinitializer
  %158 = bitcast <8 x i1> %157 to i8
  %any_active1480.not = icmp eq i8 %158, 0
  br i1 %any_active1480.not, label %endif-block1471, label %if-true-block1482

if-true-block1482:                                ; preds = %endif-block1476
  %ssa_3112 = icmp eq <8 x i32> %reg108.2, zeroinitializer
  %159 = and <8 x i1> %155, %ssa_3112
  %maskfull1484 = select <8 x i1> %159, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %160 = and <8 x i32> %maskfull1484, %mask.0
  %161 = icmp ne <8 x i32> %160, zeroinitializer
  %162 = bitcast <8 x i1> %161 to i8
  %any_active1485.not = icmp eq i8 %162, 0
  br i1 %any_active1485.not, label %endif-block1486, label %if-true-block1487

if-true-block1487:                                ; preds = %if-true-block1482
  %163 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> zeroinitializer, <8 x float> zeroinitializer) #4
  %164 = bitcast <8 x float> %163 to <8 x i32>
  br label %endif-block1486

endif-block1486:                                  ; preds = %if-true-block1487, %if-true-block1482
  %reg122.11 = phi <8 x i32> [ zeroinitializer, %if-true-block1487 ], [ %reg122.9, %if-true-block1482 ]
  %reg121.11 = phi <8 x i32> [ zeroinitializer, %if-true-block1487 ], [ %reg121.9, %if-true-block1482 ]
  %reg108.6 = phi <8 x i32> [ zeroinitializer, %if-true-block1487 ], [ %reg108.2, %if-true-block1482 ]
  %reg103.6 = phi <8 x i32> [ %164, %if-true-block1487 ], [ zeroinitializer, %if-true-block1482 ]
  %165 = xor <8 x i1> %159, %155
  %any_active1490.not = icmp eq i8 0, 0
  br i1 %any_active1490.not, label %endif-block1491, label %if-true-block1492

if-true-block1492:                                ; preds = %endif-block1486
  %ssa_3137 = icmp eq <8 x i32> %reg108.6, splat (i32 1)
  %166 = and <8 x i1> %ssa_3137, %165
  %maskfull1494 = select <8 x i1> %166, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %167 = and <8 x i32> %maskfull1494, %mask.0
  %168 = icmp ne <8 x i32> %167, zeroinitializer
  %169 = bitcast <8 x i1> %168 to i8
  %any_active1495.not = icmp eq i8 %169, 0
  br i1 %any_active1495.not, label %endif-block1496, label %if-true-block1497

if-true-block1497:                                ; preds = %if-true-block1492
  %ssa_3149 = icmp sge <8 x i32> zeroinitializer, %reg103.6
  %ssa_3150 = or <8 x i1> %ssa_3149, zeroinitializer
  %ssa_3151 = xor <8 x i1> %ssa_3150, splat (i1 true)
  %170 = and <8 x i1> %166, %ssa_3151
  %maskfull1499 = select <8 x i1> %170, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %171 = and <8 x i32> %maskfull1499, %mask.0
  %172 = icmp ne <8 x i32> %171, zeroinitializer
  %173 = bitcast <8 x i1> %172 to i8
  %any_active1500.not = icmp eq i8 %173, 0
  br i1 %any_active1500.not, label %endif-block1501, label %if-true-block1502

if-true-block1502:                                ; preds = %if-true-block1497
  br i1 true, label %if-true-block1508, label %endif-block1507

if-true-block1508:                                ; preds = %if-true-block1502
  br label %endif-block1507

endif-block1507:                                  ; preds = %if-true-block1508, %if-true-block1502
  br label %endif-block1501

endif-block1501:                                  ; preds = %endif-block1507, %if-true-block1497
  br label %endif-block1519

endif-block1519:                                  ; preds = %endif-block1501
  br label %endif-block1537

endif-block1537:                                  ; preds = %endif-block1519
  br i1 false, label %endif-block1555, label %if-true-block1556

if-true-block1556:                                ; preds = %endif-block1537
  br i1 true, label %if-true-block1562, label %endif-block1561

if-true-block1562:                                ; preds = %if-true-block1556
  %174 = call { <8 x float>, <8 x float>, <8 x float>, <8 x float>, <8 x i1> } null(i64 0, i64 undef, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer, <8 x i32> zeroinitializer)
  br label %endif-block1561

endif-block1561:                                  ; preds = %if-true-block1562, %if-true-block1556
  br label %endif-block1555

endif-block1555:                                  ; preds = %endif-block1561, %endif-block1537
  br i1 false, label %endif-block1573, label %if-true-block1574

if-true-block1574:                                ; preds = %endif-block1555
  br i1 false, label %endif-block1580, label %if-true-block1581

if-true-block1581:                                ; preds = %if-true-block1574
  br i1 false, label %endif-block1585, label %if-true-block1586

if-true-block1586:                                ; preds = %if-true-block1581
  br label %endif-block1585

endif-block1585:                                  ; preds = %if-true-block1586, %if-true-block1581
  br label %endif-block1580

endif-block1580:                                  ; preds = %endif-block1585, %if-true-block1574
  br label %endif-block1573

endif-block1573:                                  ; preds = %endif-block1580, %endif-block1555
  br label %endif-block1496

endif-block1496:                                  ; preds = %endif-block1573, %if-true-block1492
  br label %endif-block1619

endif-block1619:                                  ; preds = %endif-block1496
  br i1 false, label %endif-block1637, label %if-true-block1638

if-true-block1638:                                ; preds = %endif-block1619
  br i1 true, label %if-true-block1644, label %endif-block1643

if-true-block1644:                                ; preds = %if-true-block1638
  br label %endif-block1643

endif-block1643:                                  ; preds = %if-true-block1644, %if-true-block1638
  br label %endif-block1637

endif-block1637:                                  ; preds = %endif-block1643, %endif-block1619
  br i1 false, label %endif-block1655, label %if-true-block1656

if-true-block1656:                                ; preds = %endif-block1637
  br i1 true, label %if-true-block1662, label %endif-block1661

if-true-block1662:                                ; preds = %if-true-block1656
  br label %endif-block1661

endif-block1661:                                  ; preds = %if-true-block1662, %if-true-block1656
  br label %endif-block1655

endif-block1655:                                  ; preds = %endif-block1661, %endif-block1637
  br label %endif-block1673

endif-block1673:                                  ; preds = %endif-block1655
  br i1 false, label %endif-block1691, label %if-true-block1692

if-true-block1692:                                ; preds = %endif-block1673
  br label %endif-block1698

endif-block1698:                                  ; preds = %if-true-block1692
  br label %endif-block1691

endif-block1691:                                  ; preds = %endif-block1698, %endif-block1673
  br i1 false, label %endif-block1733, label %if-true-block1734

if-true-block1734:                                ; preds = %endif-block1691
  br label %endif-block1733

endif-block1733:                                  ; preds = %if-true-block1734, %endif-block1691
  %175 = xor <8 x i1> zeroinitializer, %165
  %any_active1737.not = icmp eq i8 0, 0
  br i1 %any_active1737.not, label %endif-block1738, label %if-true-block1739

if-true-block1739:                                ; preds = %endif-block1733
  %ssa_3530 = icmp eq <8 x i32> zeroinitializer, zeroinitializer
  %176 = and <8 x i1> %175, %ssa_3530
  %maskfull1741 = select <8 x i1> %176, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %177 = and <8 x i32> %maskfull1741, %mask.0
  %178 = icmp ne <8 x i32> %177, zeroinitializer
  %179 = bitcast <8 x i1> %178 to i8
  %any_active1742.not = icmp eq i8 %179, 0
  br i1 %any_active1742.not, label %endif-block1743, label %if-true-block1744

if-true-block1744:                                ; preds = %if-true-block1739
  %180 = bitcast <8 x i32> %reg88.17 to <8 x float>
  %ssa_3533 = fsub <8 x float> splat (float 1.000000e+00), %180
  %ssa_3541 = fmul <8 x float> %ssa_3533, zeroinitializer
  %181 = bitcast <8 x i32> %maskfull1741 to <8 x float>
  %182 = bitcast <8 x i32> %reg87.17 to <8 x float>
  %ssa_3547 = fadd <8 x float> zeroinitializer, %182
  %183 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %ssa_3547, <8 x float> %181) #4
  %184 = bitcast <8 x float> %183 to <8 x i32>
  %ssa_3549 = fadd <8 x float> %ssa_3541, %180
  %185 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %ssa_3549, <8 x float> %181) #4
  %186 = bitcast <8 x float> %185 to <8 x i32>
  %187 = and <8 x i32> %maskfull1741, splat (i32 2)
  %188 = or <8 x i32> %187, zeroinitializer
  br label %endif-block1743

endif-block1743:                                  ; preds = %if-true-block1744, %if-true-block1739
  %reg122.16 = phi <8 x i32> [ %186, %if-true-block1744 ], [ zeroinitializer, %if-true-block1739 ]
  %reg121.16 = phi <8 x i32> [ %184, %if-true-block1744 ], [ zeroinitializer, %if-true-block1739 ]
  %reg108.10 = phi <8 x i32> [ %188, %if-true-block1744 ], [ zeroinitializer, %if-true-block1739 ]
  %189 = xor <8 x i1> %176, %175
  %any_active1747.not = icmp eq i8 0, 0
  br i1 %any_active1747.not, label %endif-block1748, label %if-true-block1749

if-true-block1749:                                ; preds = %endif-block1743
  %ssa_3551 = icmp eq <8 x i32> %reg108.10, splat (i32 1)
  %190 = and <8 x i1> %ssa_3551, %189
  %maskfull1751 = select <8 x i1> %190, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %191 = and <8 x i32> %maskfull1751, %mask.0
  %192 = icmp ne <8 x i32> %191, zeroinitializer
  %193 = bitcast <8 x i1> %192 to i8
  %any_active1752.not = icmp eq i8 %193, 0
  br i1 %any_active1752.not, label %endif-block1753, label %if-true-block1754

if-true-block1754:                                ; preds = %if-true-block1749
  br i1 false, label %endif-block1758, label %if-true-block1759

if-true-block1759:                                ; preds = %if-true-block1754
  br i1 true, label %if-true-block1765, label %endif-block1764

if-true-block1765:                                ; preds = %if-true-block1759
  br label %endif-block1764

endif-block1764:                                  ; preds = %if-true-block1765, %if-true-block1759
  br label %endif-block1758

endif-block1758:                                  ; preds = %endif-block1764, %if-true-block1754
  br i1 false, label %endif-block1776, label %if-true-block1777

if-true-block1777:                                ; preds = %endif-block1758
  br i1 true, label %if-true-block1783, label %endif-block1782

if-true-block1783:                                ; preds = %if-true-block1777
  br label %endif-block1782

endif-block1782:                                  ; preds = %if-true-block1783, %if-true-block1777
  br label %endif-block1776

endif-block1776:                                  ; preds = %endif-block1782, %endif-block1758
  br i1 false, label %endif-block1794, label %if-true-block1795

if-true-block1795:                                ; preds = %endif-block1776
  br i1 true, label %if-true-block1801, label %endif-block1800

if-true-block1801:                                ; preds = %if-true-block1795
  br label %endif-block1800

endif-block1800:                                  ; preds = %if-true-block1801, %if-true-block1795
  br label %endif-block1794

endif-block1794:                                  ; preds = %endif-block1800, %endif-block1776
  br label %endif-block1812

endif-block1812:                                  ; preds = %endif-block1794
  %194 = bitcast <8 x i32> zeroinitializer to <8 x float>
  %ssa_3641 = fsub <8 x float> %194, zeroinitializer
  %ssa_3642 = fmul <8 x float> %ssa_3641, %ssa_3641
  %ssa_3644 = fadd <8 x float> zeroinitializer, %ssa_3642
  %ssa_3645 = fcmp uge <8 x float> %ssa_3644, splat (float 0x3E45798EE0000000)
  %195 = and <8 x i1> %ssa_3645, %190
  %maskfull1828 = select <8 x i1> %195, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %any_active1829.not = icmp eq i8 0, 0
  br i1 %any_active1829.not, label %endif-block1830, label %if-true-block1831

if-true-block1831:                                ; preds = %endif-block1812
  %ssa_3648 = fdiv <8 x float> zeroinitializer, zeroinitializer
  %196 = bitcast <8 x i32> %maskfull1828 to <8 x float>
  %197 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %ssa_3648, <8 x float> %196) #4
  %ssa_3649 = fdiv <8 x float> %ssa_3641, zeroinitializer
  %198 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %ssa_3649, <8 x float> %196) #4
  %199 = bitcast <8 x float> %198 to <8 x i32>
  %ssa_3651 = call <8 x float> @llvm.fabs.v8f32(<8 x float> %197) #4
  %ssa_3653 = call <8 x float> @llvm.fabs.v8f32(<8 x float> %198) #4
  %ssa_3654 = call <8 x float> @llvm.x86.avx.max.ps.256(<8 x float> %ssa_3651, <8 x float> %ssa_3653) #4
  %ssa_3655 = call <8 x float> @llvm.x86.avx.min.ps.256(<8 x float> %ssa_3651, <8 x float> %ssa_3653) #4
  %ssa_3657 = fcmp olt <8 x float> %ssa_3655, splat (float 0x3EB0C6F7A0000000)
  %200 = and <8 x i1> %ssa_3657, %195
  %ssa_3660 = fmul <8 x float> zeroinitializer, %ssa_3654
  %201 = bitcast <8 x i32> %break_full1461 to <8 x float>
  %202 = select <8 x i1> %200, <8 x float> %201, <8 x float> zeroinitializer
  %203 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %ssa_3660, <8 x float> %202) #4
  %204 = xor <8 x i1> %200, %195
  %any_active1836.not = icmp eq i8 0, 0
  br i1 %any_active1836.not, label %endif-block1837, label %if-true-block1838

if-true-block1838:                                ; preds = %if-true-block1831
  %ssa_3662 = fmul <8 x float> %ssa_3654, splat (float 2.000000e+00)
  %ssa_3663 = fdiv <8 x float> %ssa_3655, %ssa_3662
  %ssa_3665 = fcmp oge <8 x float> %ssa_3663, zeroinitializer
  %205 = and <8 x i1> %204, %ssa_3665
  %maskfull1840 = select <8 x i1> %205, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %206 = and <8 x i32> %maskfull1840, %mask.0
  %207 = icmp ne <8 x i32> %206, zeroinitializer
  %208 = bitcast <8 x i1> %207 to i8
  %any_active1841.not = icmp eq i8 %208, 0
  br i1 %any_active1841.not, label %endif-block1842, label %if-true-block1843

if-true-block1843:                                ; preds = %if-true-block1838
  %ssa_3666 = fadd <8 x float> %ssa_3654, %ssa_3655
  %ssa_3667 = fmul <8 x float> %ssa_3666, splat (float 5.000000e-01)
  %ssa_3668 = fmul <8 x float> %ssa_3662, %ssa_3655
  %ssa_3670 = fmul <8 x float> %ssa_3668, zeroinitializer
  %ssa_3671 = call <8 x float> @llvm.sqrt.v8f32(<8 x float> %ssa_3670) #4
  %209 = fsub <8 x float> %ssa_3671, %ssa_3667
  %210 = bitcast <8 x i32> %maskfull1840 to <8 x float>
  %211 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %203, <8 x float> %209, <8 x float> %210) #4
  br label %endif-block1842

endif-block1842:                                  ; preds = %if-true-block1843, %if-true-block1838
  %212 = phi <8 x float> [ %211, %if-true-block1843 ], [ %203, %if-true-block1838 ]
  %213 = xor <8 x i1> %205, %204
  %any_active1846.not = icmp eq i8 0, 0
  br i1 %any_active1846.not, label %endif-block1837, label %if-true-block1848

if-true-block1848:                                ; preds = %endif-block1842
  %ssa_3674 = fsub <8 x float> splat (float 1.000000e+00), %ssa_3663
  %ssa_3676 = fcmp oge <8 x float> %ssa_3674, zeroinitializer
  %214 = and <8 x i1> %213, %ssa_3676
  %maskfull1850 = select <8 x i1> %214, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %215 = and <8 x i32> %maskfull1850, %mask.0
  %216 = icmp ne <8 x i32> %215, zeroinitializer
  %217 = bitcast <8 x i1> %216 to i8
  %any_active1851.not = icmp eq i8 %217, 0
  br i1 %any_active1851.not, label %endif-block1852, label %if-true-block1853

if-true-block1853:                                ; preds = %if-true-block1848
  %ssa_3678 = fsub <8 x float> %ssa_3654, %ssa_3655
  br label %endif-block1852

endif-block1852:                                  ; preds = %if-true-block1853, %if-true-block1848
  br i1 false, label %endif-block1837, label %if-true-block1858

if-true-block1858:                                ; preds = %endif-block1852
  br label %endif-block1837

endif-block1837:                                  ; preds = %if-true-block1858, %endif-block1852, %endif-block1842, %if-true-block1831
  %218 = phi <8 x float> [ %203, %if-true-block1831 ], [ %212, %endif-block1842 ], [ zeroinitializer, %if-true-block1858 ], [ zeroinitializer, %endif-block1852 ]
  %ssa_3695 = fneg <8 x float> %218
  %219 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %ssa_3695, <8 x float> %196) #4
  %220 = bitcast <8 x float> %219 to <8 x i32>
  br label %endif-block1830

endif-block1830:                                  ; preds = %endif-block1837, %endif-block1812
  %reg67.10 = phi <8 x i32> [ %199, %endif-block1837 ], [ zeroinitializer, %endif-block1812 ]
  %reg65.10 = phi <8 x i32> [ %220, %endif-block1837 ], [ zeroinitializer, %endif-block1812 ]
  %221 = xor <8 x i32> zeroinitializer, splat (i32 -1)
  %222 = and <8 x i32> %reg65.10, %221
  %223 = or <8 x i32> %222, zeroinitializer
  %224 = and <8 x i32> %reg67.10, %221
  %225 = bitcast <8 x i32> %223 to <8 x float>
  %ssa_3697 = fcmp ogt <8 x float> %225, splat (float 1.500000e+00)
  %226 = bitcast <8 x i32> %maskfull1751 to <8 x float>
  %227 = bitcast <8 x float> zeroinitializer to <8 x i32>
  %228 = bitcast <8 x i32> %224 to <8 x float>
  %229 = select <8 x i1> %ssa_3697, <8 x float> zeroinitializer, <8 x float> %228
  %230 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> zeroinitializer, <8 x float> %229, <8 x float> %226) #4
  br label %endif-block1753

endif-block1753:                                  ; preds = %endif-block1830, %if-true-block1749
  %231 = phi <8 x float> [ %230, %endif-block1830 ], [ zeroinitializer, %if-true-block1749 ]
  %reg110.10 = phi <8 x i32> [ %227, %endif-block1830 ], [ zeroinitializer, %if-true-block1749 ]
  %ssa_3751 = fmul <8 x float> %231, zeroinitializer
  %232 = bitcast <8 x i32> %reg110.10 to <8 x float>
  %ssa_3754 = fmul <8 x float> zeroinitializer, %232
  %ssa_3755 = fadd <8 x float> %ssa_3751, %ssa_3754
  %ssa_3757 = fcmp ogt <8 x float> %ssa_3755, splat (float 0x3FEFD70A40000000)
  %233 = and <8 x i1> %ssa_3757, %189
  %maskfull1874 = select <8 x i1> %233, <8 x i32> %break_full1461, <8 x i32> zeroinitializer
  %234 = and <8 x i32> %maskfull1874, %mask.0
  %235 = icmp ne <8 x i32> %234, zeroinitializer
  %236 = bitcast <8 x i1> %235 to i8
  %any_active1875.not = icmp eq i8 %236, 0
  br i1 %any_active1875.not, label %endif-block1876, label %if-true-block1877

if-true-block1877:                                ; preds = %endif-block1753
  br i1 false, label %endif-block1881, label %if-true-block1882

if-true-block1882:                                ; preds = %if-true-block1877
  br label %endif-block1886

endif-block1886:                                  ; preds = %if-true-block1882
  br label %endif-block1881

endif-block1881:                                  ; preds = %endif-block1886, %if-true-block1877
  br i1 false, label %endif-block1926, label %if-true-block1927

if-true-block1927:                                ; preds = %endif-block1881
  br label %endif-block1931

endif-block1931:                                  ; preds = %if-true-block1927
  br label %endif-block1926

endif-block1926:                                  ; preds = %endif-block1931, %endif-block1881
  br label %endif-block1876

endif-block1876:                                  ; preds = %endif-block1926, %endif-block1753
  %any_active1970.not = icmp eq i8 0, 0
  br i1 %any_active1970.not, label %endif-block1971, label %if-true-block1972

if-true-block1972:                                ; preds = %endif-block1876
  br label %if-true-block1977

if-true-block1977:                                ; preds = %if-true-block1972
  ret void

endif-block1971:                                  ; preds = %endif-block1876
  br label %endif-block1748

endif-block1748:                                  ; preds = %endif-block1971, %endif-block1743
  %reg122.17 = phi <8 x i32> [ zeroinitializer, %endif-block1971 ], [ %reg122.16, %endif-block1743 ]
  %reg121.17 = phi <8 x i32> [ zeroinitializer, %endif-block1971 ], [ %reg121.16, %endif-block1743 ]
  br label %endif-block1738

endif-block1738:                                  ; preds = %endif-block1748, %endif-block1733
  %reg122.15 = phi <8 x i32> [ %reg122.17, %endif-block1748 ], [ zeroinitializer, %endif-block1733 ]
  %reg121.15 = phi <8 x i32> [ %reg121.17, %endif-block1748 ], [ zeroinitializer, %endif-block1733 ]
  br label %endif-block1491

endif-block1491:                                  ; preds = %endif-block1738, %endif-block1486
  %reg126.7 = phi <8 x i32> [ zeroinitializer, %endif-block1738 ], [ %reg126.5, %endif-block1486 ]
  %reg124.7 = phi <8 x i32> [ zeroinitializer, %endif-block1738 ], [ %reg124.5, %endif-block1486 ]
  %reg123.6 = phi <8 x i32> [ zeroinitializer, %endif-block1738 ], [ %reg123.2, %endif-block1486 ]
  %reg122.12 = phi <8 x i32> [ %reg122.15, %endif-block1738 ], [ %reg122.11, %endif-block1486 ]
  %reg121.12 = phi <8 x i32> [ %reg121.15, %endif-block1738 ], [ %reg121.11, %endif-block1486 ]
  %reg94.11 = phi <8 x i32> [ zeroinitializer, %endif-block1738 ], [ %reg94.7, %endif-block1486 ]
  %237 = bitcast <8 x i32> %maskfull1479 to <8 x float>
  %238 = bitcast <8 x i32> %reg94.11 to <8 x float>
  %239 = bitcast <8 x i32> %reg123.6 to <8 x float>
  %240 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %239, <8 x float> %238, <8 x float> %237) #4
  %241 = bitcast <8 x float> %240 to <8 x i32>
  br label %endif-block1471

endif-block1471:                                  ; preds = %endif-block1491, %endif-block1476, %endif-block1336
  %reg127.4 = phi <8 x i32> [ %reg127.2, %endif-block1336 ], [ zeroinitializer, %endif-block1491 ], [ %reg127.5, %endif-block1476 ]
  %reg126.4 = phi <8 x i32> [ %reg126.2, %endif-block1336 ], [ %reg126.7, %endif-block1491 ], [ %reg126.5, %endif-block1476 ]
  %reg125.4 = phi <8 x i32> [ %reg125.2, %endif-block1336 ], [ zeroinitializer, %endif-block1491 ], [ %reg125.5, %endif-block1476 ]
  %reg124.4 = phi <8 x i32> [ %reg124.2, %endif-block1336 ], [ %reg124.7, %endif-block1491 ], [ %reg124.5, %endif-block1476 ]
  %reg123.4 = phi <8 x i32> [ %reg123.2, %endif-block1336 ], [ %241, %endif-block1491 ], [ %reg123.2, %endif-block1476 ]
  %reg122.8 = phi <8 x i32> [ %reg122.6, %endif-block1336 ], [ %reg122.12, %endif-block1491 ], [ %reg122.9, %endif-block1476 ]
  %reg121.8 = phi <8 x i32> [ %reg121.6, %endif-block1336 ], [ %reg121.12, %endif-block1491 ], [ %reg121.9, %endif-block1476 ]
  %reg120.8 = phi <8 x i32> [ %reg120.6, %endif-block1336 ], [ zeroinitializer, %endif-block1491 ], [ %reg120.9, %endif-block1476 ]
  %reg119.8 = phi <8 x i32> [ %reg119.6, %endif-block1336 ], [ zeroinitializer, %endif-block1491 ], [ %reg119.9, %endif-block1476 ]
  br label %endif-block1331

endif-block1331:                                  ; preds = %endif-block1471, %endif-block1324
  %.04829 = phi <8 x i32> [ %break_full1461, %endif-block1471 ], [ %break_full363, %endif-block1324 ]
  %reg127.3 = phi <8 x i32> [ %reg127.4, %endif-block1471 ], [ %reg127.2, %endif-block1324 ]
  %reg126.3 = phi <8 x i32> [ %reg126.4, %endif-block1471 ], [ %reg126.2, %endif-block1324 ]
  %reg125.3 = phi <8 x i32> [ %reg125.4, %endif-block1471 ], [ %reg125.2, %endif-block1324 ]
  %reg124.3 = phi <8 x i32> [ %reg124.4, %endif-block1471 ], [ %reg124.2, %endif-block1324 ]
  %reg123.3 = phi <8 x i32> [ %reg123.4, %endif-block1471 ], [ %reg123.2, %endif-block1324 ]
  %reg122.7 = phi <8 x i32> [ %reg122.8, %endif-block1471 ], [ %reg122.6, %endif-block1324 ]
  %reg121.7 = phi <8 x i32> [ %reg121.8, %endif-block1471 ], [ %reg121.6, %endif-block1324 ]
  %reg120.7 = phi <8 x i32> [ %reg120.8, %endif-block1471 ], [ %reg120.6, %endif-block1324 ]
  %reg119.7 = phi <8 x i32> [ %reg119.8, %endif-block1471 ], [ %reg119.6, %endif-block1324 ]
  %reg118.3 = phi <8 x i8> [ %122, %endif-block1471 ], [ %81, %endif-block1324 ]
  %reg108.3 = phi <8 x i32> [ zeroinitializer, %endif-block1471 ], [ %reg108.2, %endif-block1324 ]
  %242 = bitcast <8 x i32> %reg114.2 to <8 x float>
  %243 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %85, <8 x float> %242, <8 x float> zeroinitializer) #4
  %244 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %109, <8 x float> %reg113.2, <8 x float> zeroinitializer) #4
  %maskfull2641 = select <8 x i1> %50, <8 x i32> %.04829, <8 x i32> zeroinitializer
  %245 = bitcast <8 x i32> %maskfull2641 to <8 x float>
  %246 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %242, <8 x float> %243, <8 x float> %245) #4
  %247 = bitcast <8 x float> %246 to <8 x i32>
  %248 = call <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float> %reg113.2, <8 x float> %244, <8 x float> %245) #4
  %i1cond2648.not = icmp eq i8 0, 0
  br i1 %i1cond2648.not, label %endif-block281, label %bgnloop343

endif-block281:                                   ; preds = %endif-block1331, %bgnloop
  %reg127.1 = phi <8 x i32> [ %reg127.0, %bgnloop ], [ %reg127.3, %endif-block1331 ]
  %reg126.1 = phi <8 x i32> [ %reg126.0, %bgnloop ], [ %reg126.3, %endif-block1331 ]
  %reg125.1 = phi <8 x i32> [ %reg125.0, %bgnloop ], [ %reg125.3, %endif-block1331 ]
  %reg124.1 = phi <8 x i32> [ %reg124.0, %bgnloop ], [ %reg124.3, %endif-block1331 ]
  %reg123.1 = phi <8 x i32> [ %reg123.0, %bgnloop ], [ %reg123.3, %endif-block1331 ]
  %reg118.1 = phi <8 x i8> [ %reg118.0, %bgnloop ], [ %reg118.3, %endif-block1331 ]
  %reg114.1 = phi <8 x i32> [ %reg114.0, %bgnloop ], [ %247, %endif-block1331 ]
  %reg113.1 = phi <8 x i32> [ %reg113.0, %bgnloop ], [ zeroinitializer, %endif-block1331 ]
  %249 = xor <8 x i8> zeroinitializer, splat (i8 -1)
  %250 = and <8 x i8> %reg118.1, %249
  %251 = or <8 x i8> %250, zeroinitializer
  br i1 %any_active253.not, label %endloop2671, label %bgnloop

endloop2671:                                      ; preds = %endif-block281
  br i1 false, label %endif-block2673, label %if-true-block2674

if-true-block2674:                                ; preds = %endloop2671
  br i1 true, label %if-true-block2683, label %endif-block2673

if-true-block2683:                                ; preds = %if-true-block2674
  br label %endif-block2673

endif-block2673:                                  ; preds = %if-true-block2683, %if-true-block2674, %endloop2671
  br label %endif-block142

endif-block142:                                   ; preds = %endif-block2673, %endif-block132
  %.not4952 = icmp ult i32 0, 0
  br i1 %.not4952, label %loop_begin, label %skip

skip:                                             ; preds = %endif-block142
  ret void
}

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(none)
declare <4 x float> @llvm.x86.sse.max.ss(<4 x float>, <4 x float>) #0

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(none)
declare <4 x float> @llvm.x86.sse.min.ss(<4 x float>, <4 x float>) #0

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare i32 @llvm.fptoui.sat.i32.f32(float) #1

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(read)
declare <8 x i32> @llvm.masked.gather.v8i32.v8p0(<8 x ptr>, i32 immarg, <8 x i1>, <8 x i32>) #2

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(none)
declare <8 x float> @llvm.x86.avx.blendv.ps.256(<8 x float>, <8 x float>, <8 x float>) #0

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare i32 @llvm.cttz.i32(i32, i1 immarg) #1

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(none)
declare <8 x float> @llvm.x86.avx.max.ps.256(<8 x float>, <8 x float>) #0

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(none)
declare <8 x float> @llvm.x86.avx.min.ps.256(<8 x float>, <8 x float>) #0

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x i32> @llvm.fptosi.sat.v8i32.v8f32(<8 x float>) #1

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(read)
declare <8 x i32> @llvm.x86.avx2.gather.d.d.256(<8 x i32>, ptr, <8 x i32>, <8 x i32>, i8 immarg) #2

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x float> @llvm.fabs.v8f32(<8 x float>) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x float> @llvm.floor.v8f32(<8 x float>) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x i32> @llvm.fptoui.sat.v8i32.v8f32(<8 x float>) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x float> @llvm.fmuladd.v8f32(<8 x float>, <8 x float>, <8 x float>) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x float> @llvm.sqrt.v8f32(<8 x float>) #1

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(write)
declare void @llvm.masked.scatter.v8i32.v8p0(<8 x i32>, <8 x ptr>, i32 immarg, <8 x i1>) #3

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare i8 @llvm.cttz.i8(i8, i1 immarg) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x i32> @llvm.umin.v8i32(<8 x i32>, <8 x i32>) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x i32> @llvm.smin.v8i32(<8 x i32>, <8 x i32>) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x i32> @llvm.umax.v8i32(<8 x i32>, <8 x i32>) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare i32 @llvm.umin.i32(i32, i32) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare <8 x float> @llvm.copysign.v8f32(<8 x float>, <8 x float>) #1

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare i32 @llvm.umax.i32(i32, i32) #1

attributes #0 = { nocallback nofree nosync nounwind willreturn memory(none) }
attributes #1 = { nocallback nofree nosync nounwind speculatable willreturn memory(none) }
attributes #2 = { nocallback nofree nosync nounwind willreturn memory(read) }
attributes #3 = { nocallback nofree nosync nounwind willreturn memory(write) }
attributes #4 = { nounwind }
