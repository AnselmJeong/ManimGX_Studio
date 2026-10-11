// SPDX-FileCopyrightText: 2026 Academa, Inc.
// SPDX-FileCopyrightText: 2016 The Android Open Source Project
// SPDX-License-Identifier: Apache-2.0
// Modified by Academa, Inc.

//! A 3D view's ambient occlusion (`Camera.ambient_occlusion`): how much of the light from all around reaches the
//! surface each pixel shows, as the surfaces near it shut it out — scalable ambient obscurance (McGuire, Mara and
//! Luebke 2012; `occlusion.wgsl`). The view's opaque depth comes first, its opaque meshes' (`vs_depth`) and then its
//! opaque paths' where nearer (`vector::Out::Opaque`); from it come distances along the view, a pyramid of them, the
//! occlusion and its low-pass, which the view's lit passes read (`light.wgsl`: what an ambient or environment light
//! gives a surface, times it).

use std::f32::consts::TAU;

/// The taps a pixel's occlusion is sought with, and the turns of their spiral (its start interleaved 4 x 4:
/// `occlusion.wgsl`'s `start`).
const SAMPLES: f32 = 16.0;
const TURNS: f32 = 7.0;
/// How far a surface's depth is taken nearer than it is, as a share of its distance: no surface shuts out its own
/// light.
const BIAS: f32 = 0.0005;
/// The depth within which the low-pass takes a neighbour as the surface's own, as a share of the radius (5 cm of 30).
const SAME_SURFACE: f32 = 1.0 / 6.0;

/// The passes: a mesh's depth as its view sees it (the raster pipeline's `vs_depth`), and the occlusion's: distances,
/// a level of the pyramid, the occlusion, its low-pass.
pub(crate) struct Occlusion {
    pub(crate) depth: wgpu::RenderPipeline,
    layouts: [wgpu::BindGroupLayout; 4],
    passes: [wgpu::ComputePipeline; 4],
}

/// Where a view's occlusion is found (made for its canvas, at its size): its opaque depth, drawn by the view's passes,
/// then (`Occlusion::encode`) what the occlusion makes of it, last of all `out`, which the lit passes read.
pub(crate) struct Occluded {
    pub(crate) depth: wgpu::TextureView,
    pub(crate) out: wgpu::TextureView,
    params: wgpu::Buffer,
    groups: Vec<wgpu::BindGroup>, // the distances, each level of the pyramid, the occlusion, its low-pass
    sizes: Vec<[u32; 2]>,         // the pyramid's levels, from the whole view's
}

impl Occlusion {
    /// Its passes: the depth's with the raster pipeline's shader (`blend`) and scene layout.
    pub(crate) fn new(device: &wgpu::Device, blend: &wgpu::ShaderModule, scene: &wgpu::BindGroupLayout) -> Self {
        let depth = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("occlusion depth"),
            layout: Some(&device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(scene)], immediate_size: 0 })),
            vertex: wgpu::VertexState { module: blend, entry_point: Some("vs_depth"), compilation_options: Default::default(), buffers: &[] },
            fragment: None,
            primitive: wgpu::PrimitiveState::default(),
            depth_stencil: Some(wgpu::DepthStencilState {
                format: wgpu::TextureFormat::Depth32Float,
                depth_write_enabled: Some(true),
                depth_compare: Some(wgpu::CompareFunction::GreaterEqual), // (reversed Z, as the view's raster passes)
                stencil: Default::default(),
                bias: Default::default(),
            }),
            multisample: wgpu::MultisampleState::default(),
            multiview_mask: None,
            cache: None,
        });
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor { label: Some("occlusion"), source: wgpu::ShaderSource::Wgsl(include_str!("occlusion.wgsl").into()) });
        let entry = |binding, ty| wgpu::BindGroupLayoutEntry { binding, visibility: wgpu::ShaderStages::COMPUTE, ty, count: None };
        let params = entry(0, wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: false, min_binding_size: None });
        let texture = |binding| entry(binding, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false });
        let out = entry(6, wgpu::BindingType::StorageTexture { access: wgpu::StorageTextureAccess::WriteOnly, format: wgpu::TextureFormat::R32Float, view_dimension: wgpu::TextureViewDimension::D2 });
        let depth_in = entry(1, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Depth, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false });
        let make = |label: &str, entries: &[wgpu::BindGroupLayoutEntry]| {
            let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some(label), entries });
            let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&layout)], immediate_size: 0 });
            let options = wgpu::PipelineCompilationOptions { zero_initialize_workgroup_memory: false, ..Default::default() }; // (written before read)
            let pass = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor { label: Some(label), layout: Some(&pipeline_layout), module: &shader, entry_point: Some(label), compilation_options: options, cache: None });
            (layout, pass)
        };
        let [(l0, p0), (l1, p1), (l2, p2), (l3, p3)] = [
            make("linearize", &[params, depth_in, out]),
            make("depth_mip", &[texture(7), out]),
            make("sao", &[params, texture(3), texture(4), out]),
            make("blur", &[params, texture(3), texture(5), out]),
        ];
        Self { depth, layouts: [l0, l1, l2, l3], passes: [p0, p1, p2, p3] }
    }

    /// Where a view of `size` finds its occlusion.
    pub(crate) fn occluded(&self, device: &wgpu::Device, [width, height]: [u32; 2]) -> Occluded {
        // the pyramid's levels: down to about 32 pixels across the view's longer side, 2 to 8 of them
        let levels = (32 - width.max(height).leading_zeros()).saturating_sub(5).clamp(2, 8);
        let sizes: Vec<[u32; 2]> = (0..levels).map(|l| [(width >> l).max(1), (height >> l).max(1)]).collect();
        let texture = |label: &str, [w, h]: [u32; 2], levels: u32, format, usage| {
            let size = wgpu::Extent3d { width: w, height: h, depth_or_array_layers: 1 };
            device.create_texture(&wgpu::TextureDescriptor { label: Some(label), size, mip_level_count: levels, sample_count: 1, dimension: wgpu::TextureDimension::D2, format, usage, view_formats: &[] })
        };
        let written = wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::TEXTURE_BINDING;
        let r32 = |label| texture(label, sizes[0], 1, wgpu::TextureFormat::R32Float, written).create_view(&Default::default());
        let depth = texture("occlusion depth", sizes[0], 1, wgpu::TextureFormat::Depth32Float, wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING).create_view(&Default::default());
        let (distances, raw, out) = (r32("distances"), r32("occlusion"), r32("occlusion low-passed"));
        let pyramid = texture("distances' pyramid", sizes[1], levels - 1, wgpu::TextureFormat::R32Float, written);
        let level: Vec<wgpu::TextureView> = (0..levels - 1).map(|l| pyramid.create_view(&wgpu::TextureViewDescriptor { base_mip_level: l, mip_level_count: Some(1), ..Default::default() })).collect();
        let mips = pyramid.create_view(&Default::default());
        let params = device.create_buffer(&wgpu::BufferDescriptor { label: Some("occlusion"), size: 64, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let bind = |k: usize, entries: &[(u32, wgpu::BindingResource)]| {
            let entries: Vec<wgpu::BindGroupEntry> = entries.iter().map(|(binding, resource)| wgpu::BindGroupEntry { binding: *binding, resource: resource.clone() }).collect();
            device.create_bind_group(&wgpu::BindGroupDescriptor { label: None, layout: &self.layouts[k], entries: &entries })
        };
        let view = wgpu::BindingResource::TextureView;
        let mut groups = vec![bind(0, &[(0, params.as_entire_binding()), (1, view(&depth)), (6, view(&distances))])];
        // level l from level l - 1 (the distances themselves for the first)
        for l in 1..levels as usize {
            let finer = if l == 1 { &distances } else { &level[l - 2] };
            groups.push(bind(1, &[(7, view(finer)), (6, view(&level[l - 1]))]));
        }
        groups.push(bind(2, &[(0, params.as_entire_binding()), (3, view(&distances)), (4, view(&mips)), (6, view(&raw))]));
        groups.push(bind(3, &[(0, params.as_entire_binding()), (3, view(&distances)), (5, view(&raw)), (6, view(&out))]));
        Occluded { depth, out, params, groups, sizes }
    }

    /// A view's occlusion, once its opaque depth is drawn: `projection` the view's (rows; a 3D view's: depth z / w =
    /// near / distance, see `feed.view`), how much (`amount`) and how far around (`radius`, in the world's units).
    pub(crate) fn encode(&self, queue: &wgpu::Queue, encoder: &mut wgpu::CommandEncoder, o: &Occluded, projection: &[[f32; 4]; 4], amount: f32, radius: f32) {
        let length = |r: [f32; 4]| (r[0] * r[0] + r[1] * r[1] + r[2] * r[2]).sqrt();
        let unit = length(projection[3]); // w a unit along the view: one over the focal distance
        let (tan_x, tan_y, near) = (unit / length(projection[0]), unit / length(projection[1]), projection[2][3] / unit);
        let peak = 0.1 * radius;
        let [width, height] = o.sizes[0];
        let params: [f32; 16] = [
            tan_x, tan_y, near, (o.sizes.len() - 1) as f32,
            radius, 2.0, TAU * peak * amount / SAMPLES, BIAS, // (twice a power of 1)
            peak * peak, 1.0 / (radius * radius), 0.5 * height as f32 / tan_y, 0.0,
            0.0, TURNS * TAU / (SAMPLES - 0.5), SAMPLES, 1.0 / (SAME_SURFACE * radius),
        ];
        queue.write_buffer(&o.params, 0, bytemuck::cast_slice(&params));
        let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("occlusion"), timestamp_writes: None });
        let mut dispatch = |k: usize, group: &wgpu::BindGroup, [w, h]: [u32; 2], tile: u32| {
            pass.set_pipeline(&self.passes[k]);
            pass.set_bind_group(0, group, &[]);
            pass.dispatch_workgroups(w.div_ceil(tile), h.div_ceil(tile), 1);
        };
        let n = o.groups.len();
        dispatch(0, &o.groups[0], [width, height], 8);
        for (l, size) in o.sizes.iter().enumerate().skip(1) {
            dispatch(1, &o.groups[l], *size, 8);
        }
        dispatch(2, &o.groups[n - 2], [width, height], 8);
        dispatch(3, &o.groups[n - 1], [width, height], 16);
    }
}
