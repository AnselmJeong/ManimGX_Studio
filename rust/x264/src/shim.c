/* x264 behind four calls, so that Rust never mirrors its structs: NV12 pictures in, samples
 * for an MP4 out (each picture's NAL units prefixed by their sizes, the parameter sets apart). */

#include <stdint.h>
#include <stdlib.h>

#include "x264.h"

typedef struct {
    x264_t *x264;
    int width, height, macroblocks;
} encoder;

/* An encoder of width × height pictures at fps, in BT.601 limited range over sRGB bytes:
 * x264's preset and constant rate factor, then `count` of its own options, names[k] =
 * values[k]. `*sps` and `*pps` are its parameter sets, without size prefixes, until the next
 * call. Returns 0, or what failed: 1 the preset, 2 + k option k, -1 x264. */
int manimgx_x264_open(encoder **out, int width, int height, int fps, const char *preset,
                      float crf, int count, const char *const *names,
                      const char *const *values, const uint8_t **sps, int *sps_size,
                      const uint8_t **pps, int *pps_size) {
    x264_param_t param;
    if (x264_param_default_preset(&param, preset, NULL) < 0)
        return 1;
    param.i_width = width;
    param.i_height = height;
    param.i_csp = X264_CSP_NV12;
    param.i_fps_num = param.i_timebase_den = fps;
    param.i_fps_den = param.i_timebase_num = 1;
    param.b_repeat_headers = 0;
    param.b_annexb = 0;
    param.rc.f_rf_constant = crf;
    param.i_log_level = X264_LOG_NONE;
    param.analyse.b_mb_info = 1;
    for (int k = 0; k < count; k++)
        if (x264_param_parse(&param, names[k], values[k]) < 0)
            return 2 + k;
    param.vui.b_fullrange = 0;
    param.vui.i_colmatrix = 6; /* smpte170m */
    param.vui.i_colorprim = 1; /* bt709 */
    param.vui.i_transfer = 13; /* iec61966-2-1 */
    if (x264_param_apply_profile(&param, "high") < 0)
        return -1;
    encoder *e = malloc(sizeof *e);
    if (!e || !(e->x264 = x264_encoder_open(&param))) {
        free(e);
        return -1;
    }
    e->width = width;
    e->height = height;
    e->macroblocks = ((width + 15) / 16) * ((height + 15) / 16);
    x264_nal_t *nals;
    int n;
    *sps = *pps = NULL;
    if (x264_encoder_headers(e->x264, &nals, &n) < 0)
        n = 0;
    for (int k = 0; k < n; k++) {
        if (nals[k].i_type == NAL_SPS) {
            *sps = nals[k].p_payload + 4;
            *sps_size = nals[k].i_payload - 4;
        } else if (nals[k].i_type == NAL_PPS) {
            *pps = nals[k].p_payload + 4;
            *pps_size = nals[k].i_payload - 4;
        }
    }
    if (!*sps || !*pps) {
        x264_encoder_close(e->x264);
        free(e);
        return -1;
    }
    *out = e;
    return 0;
}

/* Encode an NV12 picture shown from `pts` (NULL: one that x264 held back); `constant`, if
 * given, has a byte per macroblock, nonzero where the picture is the previous one's, and x264
 * skips those; `force_key` makes the picture a keyframe (IDR). The sample written is at `*sample` until the next call: `*size` bytes, 0 when
 * x264 holds the picture back. Returns < 0 on failure. */
int manimgx_x264_encode(encoder *e, const uint8_t *nv12, int64_t pts, const uint8_t *constant,
                        int force_key, const uint8_t **sample, int *size, int64_t *sample_pts,
                        int *key) {
    x264_picture_t in, out, *picture = NULL;
    if (nv12) {
        x264_picture_init(&in);
        in.img.i_csp = X264_CSP_NV12;
        in.img.i_plane = 2;
        in.img.i_stride[0] = in.img.i_stride[1] = e->width;
        in.img.plane[0] = (uint8_t *)nv12;
        in.img.plane[1] = (uint8_t *)nv12 + (size_t)e->width * e->height;
        in.i_pts = pts;
        in.i_type = force_key ? X264_TYPE_IDR : X264_TYPE_AUTO;
        if (constant) {
            /* x264 may encode the picture later (frame threads): it frees the array */
            uint8_t *info = malloc(e->macroblocks);
            if (!info)
                return -1;
            for (int k = 0; k < e->macroblocks; k++)
                info[k] = constant[k] ? X264_MBINFO_CONSTANT : 0;
            in.prop.mb_info = info;
            in.prop.mb_info_free = free;
        }
        picture = &in;
    }
    x264_nal_t *nals;
    int n;
    *size = x264_encoder_encode(e->x264, &nals, &n, picture, &out);
    if (*size < 0)
        return -1;
    *sample = NULL;
    if (*size) {
        /* the NAL units of a picture are contiguous: together, one sample */
        *sample = nals[0].p_payload;
        *sample_pts = out.i_pts;
        *key = out.b_keyframe;
    }
    return 0;
}

/* How many pictures x264 holds back. */
int manimgx_x264_delayed(encoder *e) {
    return x264_encoder_delayed_frames(e->x264);
}

void manimgx_x264_close(encoder *e) {
    x264_encoder_close(e->x264);
    free(e);
}
