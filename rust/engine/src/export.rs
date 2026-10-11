//! A film's video, natively: each frame drawn, converted to NV12 on the GPU where it changed,
//! read back and handed to x264 on a thread of its own (see `encode`), muxed into an MP4.

use std::collections::VecDeque;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Instant;

use crate::{encode, mp4};
use wgpu::util::DeviceExt;

use crate::render::{COUNT_BYTES, Camera, Frame, Gpu, Player, count};

impl Player {
    /// The macroblocks whose pixels can differ from the previous frame of the same view: the old
    /// and new footprints of every record that changed. Anything else — a new camera, objects
    /// added or removed, what cannot be bounded — is the whole frame.
    fn damage(&self, previous: Option<&Frame>, frame: &Frame, columns: usize, rows: usize) -> Vec<u8> {
        let everything = vec![1u8; columns * rows];
        let Some(previous) = previous else { return everything };
        if previous.view != frame.view || previous.records.len() != frame.records.len() {
            return everything;
        }
        let camera = Camera::new(&frame.view);
        let mut dirty = vec![0u8; columns * rows];
        for (old, new) in previous.records.iter().zip(&frame.records) {
            if bytemuck::bytes_of(old) == bytemuck::bytes_of(new) {
                continue;
            }
            for r in [old, new] {
                let Some([x0, y0, x1, y1]) = self.store.footprint(&camera, r) else { return everything };
                if x1 < 0.0 || y1 < 0.0 || x0 >= camera.size[0] || y0 >= camera.size[1] {
                    continue; // off screen
                }
                let (c0, c1) = ((x0.max(0.0) / 16.0) as usize, ((x1 / 16.0) as usize).min(columns - 1));
                let (r0, r1) = ((y0.max(0.0) / 16.0) as usize, ((y1 / 16.0) as usize).min(rows - 1));
                for row in r0..=r1 {
                    dirty[row * columns + c0..=row * columns + c1].fill(1);
                }
            }
        }
        dirty
    }

    pub(crate) fn push_frames(&mut self, gpu: &mut Gpu, frames: Vec<Frame>, repeat: u32, key: bool, capture: bool) -> Result<(), String> {
        let mut export = self.export.take().ok_or("no export is open")?;
        let result = (|| {
            // A pixel consumer waits for this frame. Settle older draws before making it,
            // so their overflow retries cannot replace its captured pixels.
            if capture {
                while !export.pending.is_empty() { self.retire(gpu, &mut export)?; }
            }
            self.push_into(gpu, &mut export, frames, repeat, key, capture)?;
            if capture {
                self.retire(gpu, &mut export)?;
                self.map_pixels(gpu)?;
            }
            Ok(())
        })();
        self.export = Some(export);
        result
    }

    /// Draw a frame into the export and convert only the macroblocks a change can touch — every
    /// one when camera views are drawn too (their pictures change with no record changing).
    fn push_into(&mut self, gpu: &mut Gpu, export: &mut Export, frames: Vec<Frame>, repeat: u32, key: bool, capture: bool) -> Result<(), String> {
        let (columns, rows) = (export.width.div_ceil(16), export.height.div_ceil(16));
        let total = columns * rows;
        if export.pending.len() == RING {
            self.retire(gpu, export)?;
        }
        let slot = export.drawn % RING;
        let frame = frames.last().ok_or("no frame")?;
        let (mut command, grouped, composited) = self.encode(gpu, &frames)?;
        // a frame composited in groups settles the pixels two groups share at the seam between
        // them, which a change anywhere can move
        let whole = frames.len() > 1 || grouped || export.grouped;
        export.grouped = grouped;
        let dirty = if whole { vec![1u8; total] } else { self.damage(export.previous.as_ref(), frame, columns, rows) };
        export.converted += dirty.iter().filter(|&&d| d != 0).count();
        let listed: Vec<u32> = (0..total as u32).filter(|&k| dirty[k as usize] != 0).collect();
        // a frame whose see-through fragments may overflow the lists is kept until its count is
        // read (see `retire`)
        let lists = self.lists.as_ref().filter(|_| composited && !listed.is_empty()).map(|l| l.capacity);
        self.convert(gpu, export, &mut command, &listed, slot, lists.is_some());
        if capture { self.copy_pixels(&mut command); }
        gpu.queue.submit(Some(command.finish()));
        export.map(slot, listed.len());
        gpu.device.poll(wgpu::PollType::Poll).map_err(|e| e.to_string())?;
        let first = export.previous.is_none();
        let kept = lists.map(|capacity| (frames.clone(), capacity));
        export.pending.push_back(Pending { slot, listed, repeat, first, key, kept, capture });
        export.previous = frames.into_iter().last();
        export.drawn += 1;
        Ok(())
    }

    /// Convert the listed macroblocks of the drawn frame into the export's `slot`, followed by
    /// the lists' count when `counted`.
    fn convert(&self, gpu: &Gpu, export: &Export, command: &mut wgpu::CommandEncoder, listed: &[u32], slot: usize, counted: bool) {
        if listed.is_empty() {
            return;
        }
        let columns = export.width.div_ceil(16);
        let list = gpu.device.create_buffer_init(&wgpu::util::BufferInitDescriptor { label: Some("listed"), contents: bytemuck::cast_slice(listed), usage: wgpu::BufferUsages::STORAGE });
        gpu.queue.write_buffer(&export.grid, 0, bytemuck::cast_slice(&[columns as u32, listed.len() as u32, 0, 0]));
        let color = &self.targets.as_ref().expect("targets").frame.color;
        let group = gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("nv12"),
            layout: &export.convert.get_bind_group_layout(0),
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(color) },
                wgpu::BindGroupEntry { binding: 1, resource: list.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 2, resource: export.packed.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 3, resource: export.grid.as_entire_binding() },
            ],
        });
        {
            let mut pass = command.begin_compute_pass(&Default::default());
            pass.set_pipeline(&export.convert);
            pass.set_bind_group(0, &group, &[]);
            pass.dispatch_workgroups(listed.len() as u32, 1, 1);
        }
        let bytes = listed.len() as u64 * 384;
        command.copy_buffer_to_buffer(&export.packed, 0, &export.ring[slot], 0, Some(bytes));
        if let Some(lists) = self.lists.as_ref().filter(|_| counted) {
            command.copy_buffer_to_buffer(&lists.appended, 0, &export.ring[slot], bytes, Some(COUNT_BYTES));
        }
    }

    /// The oldest frame in flight: its changed macroblocks, read back, to the encoder — drawn
    /// and converted again first if its see-through fragments overflowed the lists.
    pub(crate) fn retire(&mut self, gpu: &mut Gpu, export: &mut Export) -> Result<(), String> {
        let Some(p) = export.pending.pop_front() else { return Ok(()) };
        let mut packets = Vec::new();
        if !p.listed.is_empty() {
            let bytes = p.listed.len() as u64 * 384;
            export.wait(&gpu.device, p.slot)?;
            if let Some((frames, capacity)) = &p.kept {
                let mut capacity = *capacity;
                loop {
                    let appended = count(&export.ring[p.slot].slice(bytes..bytes + COUNT_BYTES).get_mapped_range().map_err(|e| e.to_string())?);
                    if !self.overflowed(gpu, appended, capacity) {
                        break;
                    }
                    export.ring[p.slot].unmap();
                    let (mut command, ..) = self.encode(gpu, frames)?;
                    capacity = self.lists.as_ref().map_or(0, |l| l.capacity);
                    self.convert(gpu, export, &mut command, &p.listed, p.slot, true);
                    if p.capture { self.copy_pixels(&mut command); }
                    gpu.queue.submit(Some(command.finish()));
                    export.map(p.slot, p.listed.len());
                    export.wait(&gpu.device, p.slot)?;
                }
            }
            packets = export.ring[p.slot].slice(..bytes).get_mapped_range().map_err(|e| e.to_string())?.to_vec();
            export.ring[p.slot].unmap();
        }
        let change = encode::Change { listed: p.listed, packets, first: p.first, repeat: p.repeat, key: p.key };
        export.worker.as_ref().ok_or("the video is finished")?.send(change)
    }
}

/// Frames an export has in flight: drawn and converted, their pixels on the way back (deep
/// enough that the drawing thread rarely waits for the GPU's completion).
const RING: usize = 6;

pub(crate) struct Pending {
    slot: usize,
    listed: Vec<u32>,
    repeat: u32,
    first: bool,
    key: bool,
    kept: Option<(Vec<Frame>, u64)>, // a frame composited through the lists, and their capacity
    capture: bool, // copy its final successful draw for a simultaneous pixel consumer
}

/// A video being written: each frame drawn, converted to NV12 where it changed, read back and
/// handed — the changed macroblocks only — to the encoder's thread, which keeps the picture;
/// `RING` frames in flight: the GPU draws the next frames while x264 encodes this one.
pub(crate) struct Export {
    worker: Option<encode::Worker>,
    convert: wgpu::ComputePipeline, // RGBA → NV12, the listed macroblocks (`nv12.wgsl`)
    packed: wgpu::Buffer,
    ring: Vec<wgpu::Buffer>,
    mapped: Vec<Arc<AtomicBool>>,
    grid: wgpu::Buffer,
    pub(crate) pending: VecDeque<Pending>,
    previous: Option<Frame>,
    grouped: bool, // the previous frame was composited in groups (see `push_into`)
    width: usize,
    height: usize,
    drawn: usize,
    converted: usize,
    start: Instant,
}

impl Export {
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn new(gpu: &Gpu, width: u32, height: u32, fps: u32, preset: &str, crf: f32, options: &[(String, String)], path: &str) -> Result<Self, String> {
        let worker = encode::Worker::new(encode::Encoder::new(width, height, fps, preset, crf, options, path)?, width as usize, height as usize);
        let size = (width.div_ceil(16) * height.div_ceil(16) * 384) as u64;
        let buffer = |label, usage| gpu.device.create_buffer(&wgpu::BufferDescriptor { label: Some(label), size: size + COUNT_BYTES, usage, mapped_at_creation: false });
        let convert = gpu.device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("nv12"),
            layout: None, // derived from the shader
            module: &gpu.device.create_shader_module(wgpu::include_wgsl!("nv12.wgsl")),
            entry_point: Some("cs_macroblocks"),
            compilation_options: Default::default(),
            cache: None,
        });
        Ok(Self {
            worker: Some(worker),
            convert,
            packed: buffer("nv12", wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC),
            ring: (0..RING).map(|_| buffer("nv12 readback", wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST)).collect(),
            mapped: (0..RING).map(|_| Default::default()).collect(),
            grid: gpu.device.create_buffer(&wgpu::BufferDescriptor { label: Some("grid"), size: 16, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false }),
            pending: VecDeque::with_capacity(RING),
            previous: None,
            grouped: false,
            width: width as usize,
            height: height as usize,
            drawn: 0,
            converted: 0,
            start: Instant::now(),
        })
    }

    /// Read `slot` back once its frame is converted: its `listed` macroblocks, and the lists'
    /// count after them.
    fn map(&self, slot: usize, listed: usize) {
        if listed > 0 {
            let flag = self.mapped[slot].clone();
            self.ring[slot].slice(..listed as u64 * 384 + COUNT_BYTES).map_async(wgpu::MapMode::Read, move |_| flag.store(true, Ordering::Release));
        }
    }

    /// Wait until `slot` is read back.
    fn wait(&self, device: &wgpu::Device, slot: usize) -> Result<(), String> {
        while !self.mapped[slot].load(Ordering::Acquire) {
            device.poll(wgpu::PollType::Wait { submission_index: None, timeout: None }).map_err(|e| e.to_string())?;
        }
        self.mapped[slot].store(false, Ordering::Release);
        Ok(())
    }

    pub(crate) fn finish(mut self, audio: Option<mp4::Audio>) -> Result<(f64, f64, f64, u64), String> {
        let total = self.width.div_ceil(16) * self.height.div_ceil(16);
        let converted = self.converted as f64 / (self.drawn.max(1) * total) as f64;
        let (bytes, x264) = self.worker.take().ok_or("the video is finished")?.join(audio)?;
        Ok((self.start.elapsed().as_secs_f64(), x264, converted, bytes))
    }
}

impl Drop for Export {
    /// An export dropped before it finished (the scene failed) leaves no file.
    fn drop(&mut self) {
        if let Some(worker) = self.worker.take() {
            worker.abort();
        }
    }
}
