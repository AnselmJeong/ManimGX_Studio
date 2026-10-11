// A file's sound through FFmpeg: decoded from memory into interleaved float samples at the
// stream's rate, at most two channels (wider sound downmixed to stereo by swresample, scaled so
// it can't clip). libavformat and libavcodec trim what the file declares: an MP4's edit list,
// the encoder's delay and padding.

#include <stdio.h>

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/mem.h>
#include <libavutil/opt.h>
#include <libswresample/swresample.h>

struct memory {
    const uint8_t *data;
    int64_t size, at;
};

static int read_memory(void *opaque, uint8_t *buffer, int size) {
    struct memory *m = opaque;
    int64_t n = FFMIN(size, m->size - m->at);
    if (n <= 0)
        return AVERROR_EOF;
    memcpy(buffer, m->data + m->at, n);
    m->at += n;
    return (int)n;
}

static int64_t seek_memory(void *opaque, int64_t offset, int whence) {
    struct memory *m = opaque;
    if (whence & AVSEEK_SIZE)
        return m->size;
    whence &= ~AVSEEK_FORCE;
    int64_t at = whence == SEEK_CUR ? m->at + offset : whence == SEEK_END ? m->size + offset : offset;
    if (at < 0 || at > m->size)
        return AVERROR(EINVAL);
    return m->at = at;
}

// Appends a frame's samples (NULL: what the converter still holds), as interleaved float of
// `channels` channels at `rate`, to *samples (*frames so far, room for *capacity floats).
static int append(SwrContext *swr, AVFrame *in, int channels, int rate, float **samples, size_t *frames, size_t *capacity) {
    if (in && in->ch_layout.order == AV_CHANNEL_ORDER_UNSPEC) { // PCM without a channel mask
        int n = in->ch_layout.nb_channels;
        av_channel_layout_uninit(&in->ch_layout);
        av_channel_layout_default(&in->ch_layout, n);
    }
    AVFrame *out = av_frame_alloc();
    if (!out)
        return AVERROR(ENOMEM);
    av_channel_layout_default(&out->ch_layout, channels);
    out->format = AV_SAMPLE_FMT_FLT;
    out->sample_rate = rate;
    int ret = swr_convert_frame(swr, out, in);
    if (ret == AVERROR_INPUT_CHANGED && (ret = swr_config_frame(swr, out, in)) >= 0 && (ret = swr_init(swr)) >= 0)
        ret = swr_convert_frame(swr, out, in); // the stream changed its layout or rate
    size_t need = (*frames + out->nb_samples) * channels;
    if (ret >= 0 && need > *capacity) {
        float *grown = av_realloc(*samples, FFMAX(need, *capacity * 2) * sizeof(float));
        if (grown)
            *samples = grown, *capacity = FFMAX(need, *capacity * 2);
        else
            ret = AVERROR(ENOMEM);
    }
    if (ret >= 0 && out->nb_samples) {
        memcpy(*samples + *frames * channels, out->data[0], out->nb_samples * channels * sizeof(float));
        *frames += out->nb_samples;
    }
    av_frame_free(&out);
    return ret;
}

// The sound of the file in data[0..size): *samples (av_malloc'd: manimgx_free), *frames of
// *channels at *rate. 0, or a negative AVERROR, with what went wrong in error[].
int manimgx_decode(const uint8_t *data, size_t size, float **samples, size_t *frames, int *rate, int *channels, char *error, size_t error_size) {
    struct memory m = {data, (int64_t)size, 0};
    AVFormatContext *format = avformat_alloc_context();
    AVIOContext *io = NULL;
    AVCodecContext *decoder = NULL;
    SwrContext *swr = swr_alloc();
    AVPacket *packet = av_packet_alloc();
    AVFrame *frame = av_frame_alloc();
    uint8_t *buffer = av_malloc(1 << 16);
    size_t capacity = 0;
    int ret, stream;
    *samples = NULL, *frames = 0, *error = 0;
    av_log_set_level(AV_LOG_QUIET);
    if (!format || !swr || !packet || !frame || !buffer || !(io = avio_alloc_context(buffer, 1 << 16, 0, &m, read_memory, NULL, seek_memory))) {
        ret = AVERROR(ENOMEM);
        goto end;
    }
    buffer = NULL; // the context's now
    format->pb = io;
    if ((ret = avformat_open_input(&format, NULL, NULL, NULL)) < 0 || (ret = avformat_find_stream_info(format, NULL)) < 0)
        goto end;
    if ((ret = stream = av_find_best_stream(format, AVMEDIA_TYPE_AUDIO, -1, -1, NULL, 0)) < 0)
        goto end;
    const AVCodecParameters *parameters = format->streams[stream]->codecpar;
    const AVCodec *codec = avcodec_find_decoder(parameters->codec_id);
    if (!codec) {
        snprintf(error, error_size, "its sound is %s, which ManimGX doesn't decode", avcodec_get_name(parameters->codec_id));
        ret = AVERROR_DECODER_NOT_FOUND;
        goto end;
    }
    if (!(decoder = avcodec_alloc_context3(codec))) {
        ret = AVERROR(ENOMEM);
        goto end;
    }
    if ((ret = avcodec_parameters_to_context(decoder, parameters)) < 0)
        goto end;
    decoder->pkt_timebase = format->streams[stream]->time_base;
    if ((ret = avcodec_open2(decoder, codec, NULL)) < 0)
        goto end;
    *rate = decoder->sample_rate;
    *channels = FFMIN(decoder->ch_layout.nb_channels, 2);
    if (*channels < 1 || *rate < 1) {
        ret = AVERROR_INVALIDDATA;
        goto end;
    }
    av_opt_set_double(swr, "rematrix_maxval", 1.0, 0); // a downmix that can't clip
    for (int done = 0; !done;) {
        if (av_read_frame(format, packet) < 0) {
            done = 1; // the end (or a file cut short): flush what the decoder holds
            avcodec_send_packet(decoder, NULL);
        } else if (packet->stream_index == stream) {
            avcodec_send_packet(decoder, packet); // a damaged packet is skipped
            av_packet_unref(packet);
        } else {
            av_packet_unref(packet);
            continue;
        }
        while (avcodec_receive_frame(decoder, frame) >= 0) {
            ret = append(swr, frame, *channels, *rate, samples, frames, &capacity);
            av_frame_unref(frame);
            if (ret < 0)
                goto end;
        }
    }
    ret = *frames ? append(swr, NULL, *channels, *rate, samples, frames, &capacity) : AVERROR_INVALIDDATA;
end:
    if (ret < 0) {
        if (!*error)
            av_strerror(ret, error, error_size);
        av_freep(samples);
        *frames = 0;
    }
    av_free(buffer);
    swr_free(&swr);
    av_frame_free(&frame);
    av_packet_free(&packet);
    avcodec_free_context(&decoder);
    avformat_close_input(&format);
    if (io)
        av_freep(&io->buffer);
    avio_context_free(&io);
    return ret < 0 ? ret : 0;
}

void manimgx_free(void *pointer) {
    av_free(pointer);
}
