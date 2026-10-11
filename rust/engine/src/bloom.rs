//! A 3D view's bloom (`Camera.bloom`): the glow a lens and a sensor spread around the light they take in, which keeps
//! the light (`bloom.wgsl`): a share of the light the view shows is spread over levels of half the size each and added
//! back up, the rest stays where it is, and each pixel is shown with the glow over it. The view's composite leaves its
//! pixels' paint and light for it (`vector::Out::Color`'s `light_out`) instead of showing them; a view without lit
//! content, or without bloom, shows its pixels as it did.

/// The levels: the view halved, then halved again while a level keeps this many texels across its narrower side (a
/// 1920x1080 view's: 960x540 down to 15x9, seven, the coarsest level's texel an eighth of the view's height; half the
/// glow lies within a twentieth of the height of its light, nine tenths within an eighth, nearly all within a quarter:
/// experiments/bloom), at most `LEVELS` of them.
const NARROWEST: u32 = 8;
const LEVELS: usize = 8;

/// The passes: the first level (`spread`), each level after it (`down`), each added up (`up`), the view shown (`show`).
pub(crate) struct Bloom {
    layouts: [wgpu::BindGroupLayout; 3],
    passes: [wgpu::ComputePipeline; 4],
}

/// Where a view's glow is made (for its canvas, at its size): the paint and light its composite leaves (`paint`,
/// `light`), its levels, and what the passes are bound to, the last of them writing the canvas's color.
pub(crate) struct Bloomed {
    pub(crate) paint: wgpu::TextureView,
    pub(crate) light: wgpu::TextureView,
    params: wgpu::Buffer,
    groups: Vec<wgpu::BindGroup>, // the first level, each level after it, each added up (coarsest first), the view shown
    sizes: Vec<[u32; 2]>,         // the levels', and last the view's
}

impl Bloom {
    pub(crate) fn new(device: &wgpu::Device) -> Self {
        let source = [include_str!("tone.wgsl"), include_str!("bloom.wgsl")].concat();
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor { label: Some("bloom"), source: wgpu::ShaderSource::Wgsl(source.into()) });
        let entry = |binding, ty| wgpu::BindGroupLayoutEntry { binding, visibility: wgpu::ShaderStages::COMPUTE, ty, count: None };
        let params = entry(0, wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: false, min_binding_size: None });
        let texture = |binding| entry(binding, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: true }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false });
        let smooth = entry(2, wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering));
        let out = |binding, format| entry(binding, wgpu::BindingType::StorageTexture { access: wgpu::StorageTextureAccess::WriteOnly, format, view_dimension: wgpu::TextureViewDimension::D2 });
        let level = out(3, super::RADIANCE);
        let layout = |label, entries: &[wgpu::BindGroupLayoutEntry]| device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some(label), entries });
        let layouts = [
            layout("bloom down", &[params, texture(1), smooth, level]),
            layout("bloom up", &[texture(1), smooth, level, texture(4)]),
            layout("bloom show", &[params, smooth, texture(5), texture(6), texture(7), out(8, super::COLOR)]),
        ];
        let pass = |entry: &str, k: usize| {
            let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&layouts[k])], immediate_size: 0 });
            let options = wgpu::PipelineCompilationOptions { zero_initialize_workgroup_memory: false, ..Default::default() }; // (none used)
            device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor { label: Some(entry), layout: Some(&pipeline_layout), module: &shader, entry_point: Some(entry), compilation_options: options, cache: None })
        };
        let passes = [pass("spread", 0), pass("down", 0), pass("up", 1), pass("show", 2)];
        Self { layouts, passes }
    }

    /// Where a view of `size` drawn in `target` makes its glow (`smooth`: a bilinear sampler, clamped to the edges).
    pub(crate) fn bloomed(&self, device: &wgpu::Device, smooth: &wgpu::Sampler, target: &wgpu::TextureView, [width, height]: [u32; 2]) -> Bloomed {
        let mut sizes = vec![[width.div_ceil(2), height.div_ceil(2)]];
        while sizes.len() < LEVELS {
            let [w, h] = sizes[sizes.len() - 1].map(|v| v.div_ceil(2));
            if w.min(h) < NARROWEST {
                break;
            }
            sizes.push([w, h]);
        }
        let image = |label: &str, [w, h]: [u32; 2], format| {
            let size = wgpu::Extent3d { width: w, height: h, depth_or_array_layers: 1 };
            let usage = wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::TEXTURE_BINDING;
            device.create_texture(&wgpu::TextureDescriptor { label: Some(label), size, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format, usage, view_formats: &[] }).create_view(&Default::default())
        };
        let (paint, light) = (image("bloom paint", [width, height], super::COLOR), image("bloom light", [width, height], super::RADIANCE));
        // each level's share, and (but the coarsest's) the coarser levels added to it
        let down: Vec<wgpu::TextureView> = sizes.iter().map(|&s| image("bloom level", s, super::RADIANCE)).collect();
        let up: Vec<wgpu::TextureView> = sizes[..sizes.len() - 1].iter().map(|&s| image("bloom level added up", s, super::RADIANCE)).collect();
        let params = device.create_buffer(&wgpu::BufferDescriptor { label: Some("bloom"), size: 16, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let bind = |k: usize, entries: &[(u32, wgpu::BindingResource)]| {
            let entries: Vec<wgpu::BindGroupEntry> = entries.iter().map(|(binding, resource)| wgpu::BindGroupEntry { binding: *binding, resource: resource.clone() }).collect();
            device.create_bind_group(&wgpu::BindGroupDescriptor { label: None, layout: &self.layouts[k], entries: &entries })
        };
        let (view, sampler) = (wgpu::BindingResource::TextureView, wgpu::BindingResource::Sampler(smooth));
        let added = |l: usize| if l + 1 == sizes.len() { &down[l] } else { &up[l] }; // (the coarsest is all there is of it)
        let mut groups = Vec::with_capacity(2 * sizes.len());
        for l in 0..sizes.len() {
            let source = if l == 0 { &light } else { &down[l - 1] };
            groups.push(bind(0, &[(0, params.as_entire_binding()), (1, view(source)), (2, sampler.clone()), (3, view(&down[l]))]));
        }
        for l in (0..sizes.len() - 1).rev() {
            groups.push(bind(1, &[(1, view(added(l + 1))), (2, sampler.clone()), (3, view(&up[l])), (4, view(&down[l]))]));
        }
        groups.push(bind(2, &[(0, params.as_entire_binding()), (2, sampler.clone()), (5, view(&paint)), (6, view(&light)), (7, view(added(0))), (8, view(target))]));
        sizes.push([width, height]);
        Bloomed { paint, light, params, groups, sizes }
    }

    /// A view's glow, once its composite has left its paint and light in `b`: `strength` the share of its light spread
    /// (0 to 1), `tone` its tone mapping (1: AgX).
    pub(crate) fn encode(&self, queue: &wgpu::Queue, encoder: &mut wgpu::CommandEncoder, b: &Bloomed, strength: f32, tone: u32) {
        let levels = b.sizes.len() - 1;
        let params: [u32; 4] = [strength.to_bits(), (strength / levels as f32).to_bits(), tone, 0];
        queue.write_buffer(&b.params, 0, bytemuck::cast_slice(&params));
        let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("bloom"), timestamp_writes: None });
        let mut dispatch = |k: usize, group: &wgpu::BindGroup, [w, h]: [u32; 2], tile: u32| {
            pass.set_pipeline(&self.passes[k]);
            pass.set_bind_group(0, group, &[]);
            pass.dispatch_workgroups(w.div_ceil(tile), h.div_ceil(tile), 1);
        };
        for l in 0..levels {
            dispatch(if l == 0 { 0 } else { 1 }, &b.groups[l], b.sizes[l], 8);
        }
        for (k, l) in (0..levels - 1).rev().enumerate() {
            dispatch(2, &b.groups[levels + k], b.sizes[l], 8);
        }
        dispatch(3, &b.groups[2 * levels - 1], b.sizes[levels], 16);
    }
}
