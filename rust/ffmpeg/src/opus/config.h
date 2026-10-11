// Opus's portable float build. C17's compiler feature test chooses the temporary allocation
// mode, as Opus's configure does: standard variable-length arrays first, alloca otherwise.
#define OPUS_BUILD
#define HAVE_LRINT
#define HAVE_LRINTF
#define ENABLE_HARDENING

#ifndef __STDC_NO_VLA__
#define VAR_ARRAYS
#else
#define USE_ALLOCA
#if __has_include(<alloca.h>)
#define HAVE_ALLOCA_H
#endif
#endif
