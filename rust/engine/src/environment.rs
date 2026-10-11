//! Environments: light from all around a 3D view, a picture of its surroundings (an equirectangular Radiance image,
//! RGBE: a byte of red, green, blue and a shared exponent a pixel), lighting its mobjects with a material from every
//! direction, metals reflecting it. Image-based light: its diffuse light nine spherical harmonics (computed here, from
//! the picture), its specular light a cube of the picture prefiltered by the GGX lobe a roughness a level (on the GPU,
//! when a view first shows it: `environment.wgsl`), read by the split sum (`light.wgsl`).

#[cfg(feature = "render")]
/// A cube's side, in texels (about a fifth of a degree a texel).
pub(crate) const SIDE: u32 = 512;
#[cfg(feature = "render")]
/// Its roughness levels, 512 to 16 texels a side: level l is the GGX lobe of perceptual roughness r with
/// l = (LEVELS - 1) r (2 - r).
pub(crate) const LEVELS: u32 = 6;
#[cfg(feature = "render")]
/// The samples a level's texel averages: fewer blur the glossy levels (each sample then reads a coarser mip),
/// measured in experiments/b4-ibl.
const SAMPLES: u32 = 1024;
#[cfg(feature = "render")]
/// The coarsest source a sample reads, in texels a side: a sample of the lobe's tail stands for a wide solid angle,
/// and a coarser mip than this mixes light from beyond the lobe's reach into its average (a bright sky leaking into
/// a dark floor's reflection); finer ones leave the tails noisy (experiments/b4-ibl).
const COARSEST: u32 = 16;

#[cfg(any(feature = "python", test))]
/// A Radiance (.hdr) file's pixels: its width, height, and RGBE bytes row by row from the top (a run-length encoded
/// file's runs undone).
pub(crate) fn read_hdr(data: &[u8]) -> Result<(u32, u32, Vec<u8>), String> {
    // the header: lines up to an empty one, then the resolution: "-Y height +X width"
    let mut at = 0;
    let line = |at: &mut usize| -> Result<&[u8], String> {
        let start = *at;
        let end = data[start..].iter().position(|&b| b == b'\n').ok_or("a Radiance file ends in its header")? + start;
        *at = end + 1;
        Ok(&data[start..end])
    };
    let first = line(&mut at)?;
    if !first.starts_with(b"#?") {
        return Err("not a Radiance (.hdr) file".into());
    }
    while !line(&mut at)?.is_empty() {}
    let size = String::from_utf8_lossy(line(&mut at)?).to_string();
    let words: Vec<&str> = size.split_whitespace().collect();
    let (height, width) = match words.as_slice() {
        ["-Y", h, "+X", w] => (h.parse::<u32>().map_err(|e| e.to_string())?, w.parse::<u32>().map_err(|e| e.to_string())?),
        _ => return Err(format!("a Radiance file's orientation that is not \"-Y height +X width\": {size}")),
    };
    if width == 0 || height == 0 {
        return Err("a Radiance picture's dimensions must be positive".into());
    }
    let length = (width as usize).checked_mul(height as usize).and_then(|n| n.checked_mul(4))
        .filter(|&n| n <= isize::MAX as usize).ok_or("a Radiance picture is too large to address")?;
    let row_bytes = length / height as usize;
    // A header is not evidence that its pixels exist. A flat picture needs all its
    // bytes; an RLE row needs its four-byte header and, for each of four components,
    // at least two encoded bytes per 127 decoded bytes (the longest repeated run).
    let minimum = if (8..0x8000).contains(&width) { (4 + 8 * width.div_ceil(127)) as usize * height as usize } else { length };
    if data.len() - at < minimum {
        return Err("a Radiance file ends early".into());
    }
    let mut out = vec![0u8; length];
    let byte = |at: &mut usize| -> Result<u8, String> {
        let b = *data.get(*at).ok_or("a Radiance file ends early")?;
        *at += 1;
        Ok(b)
    };
    for y in 0..height as usize {
        let row = &mut out[y * row_bytes..(y + 1) * row_bytes];
        let head = [data.get(at).copied(), data.get(at + 1).copied(), data.get(at + 2).copied()];
        if (8..0x8000).contains(&width) && head[0] == Some(2) && head[1] == Some(2) && head[2].is_some_and(|b| b & 0x80 == 0) {
            // run-length encoded: four header bytes, then each component's runs across the row
            let scanline = data.get(at..).and_then(|rest| rest.get(..4)).ok_or("a Radiance file ends early")?;
            if u16::from_be_bytes([scanline[2], scanline[3]]) as u32 != width {
                return Err("a Radiance scanline's width does not match its picture".into());
            }
            at += 4;
            for c in 0..4 {
                let mut x = 0;
                while x < width as usize {
                    let count = byte(&mut at)? as usize;
                    if count > 128 {
                        let value = byte(&mut at)?;
                        for _ in 0..count - 128 {
                            *row.get_mut(4 * x + c).ok_or("a Radiance run past its row")? = value;
                            x += 1;
                        }
                    } else {
                        for _ in 0..count {
                            *row.get_mut(4 * x + c).ok_or("a Radiance run past its row")? = byte(&mut at)?;
                            x += 1;
                        }
                    }
                }
            }
        } else {
            // flat: four bytes a pixel
            let bytes = data.get(at..).and_then(|rest| rest.get(..row_bytes)).ok_or("a Radiance file ends early")?;
            row.copy_from_slice(bytes);
            at += row_bytes;
        }
    }
    Ok((width, height, out))
}

/// An RGBE pixel's light (stb's decoding: the mantissas times 2^(exponent - 136)).
fn light(p: &[u8]) -> [f64; 3] {
    if p[3] == 0 {
        return [0.0; 3];
    }
    let scale = 2f64.powi(p[3] as i32 - 136);
    [p[0] as f64 * scale, p[1] as f64 * scale, p[2] as f64 * scale]
}

/// Light as an RGBE pixel: each channel's mantissa against the brightest's exponent, truncated (as Radiance writes it).
fn rgbe(c: [f64; 3]) -> [u8; 4] {
    let top = c[0].max(c[1]).max(c[2]);
    if top < 1e-32 {
        return [0; 4];
    }
    let exponent = top.log2().floor() as i32 + 1; // top = m 2^exponent, m in [0.5, 1)
    let scale = 256.0 / 2f64.powi(exponent);
    [(c[0] * scale) as u8, (c[1] * scale) as u8, (c[2] * scale) as u8, (exponent + 128) as u8]
}

#[cfg(any(feature = "python", test))]
/// The widest picture an environment keeps: a wider one is halved until it is not (a 4096-wide picture's pixel spans a
/// tenth of a degree, its cube's texel a fifth).
pub(crate) const WIDEST: u32 = 4096;

#[cfg(any(feature = "python", test))]
/// A picture no wider than `WIDEST`: each halving averages the available pixels' light
/// in each 2x2 block, including an odd edge or a picture only one pixel high.
pub(crate) fn narrowed(mut width: u32, mut height: u32, mut pixels: Vec<u8>) -> (u32, u32, Vec<u8>) {
    while width > WIDEST {
        let (w, h) = (width.div_ceil(2), height.div_ceil(2));
        let mut out = Vec::with_capacity(w as usize * h as usize * 4);
        for y in 0..h {
            for x in 0..w {
                let mut sum = [0.0; 3];
                let (columns, rows) = ((width - 2 * x).min(2), (height - 2 * y).min(2));
                let weight = 1.0 / (columns * rows) as f64;
                for (dx, dy) in [(0, 0), (1, 0), (0, 1), (1, 1)] {
                    if dx >= columns || dy >= rows { continue; }
                    let at = ((2 * y + dy) as usize * width as usize + (2 * x + dx) as usize) * 4;
                    let l = light(&pixels[at..at + 4]);
                    (0..3).for_each(|c| sum[c] += l[c] * weight);
                }
                out.extend(rgbe(sum));
            }
        }
        (width, height, pixels) = (w, h, out);
    }
    (width, height, pixels)
}

#[cfg(feature = "render")]
/// The direction of an equirectangular picture's point (u, v in [0, 1], v from the top): the picture's up is the
/// scene's +z (a 3D view's floor is its xy plane), its centre looking along +x, its edges along -x, and across it to
/// the right is turning right (clockwise from above: as it shows to someone inside it; Blender's convention).
pub(crate) fn direction(u: f64, v: f64) -> [f64; 3] {
    let (phi, theta) = ((0.5 - u) * std::f64::consts::TAU, v * std::f64::consts::PI);
    [theta.sin() * phi.cos(), theta.sin() * phi.sin(), theta.cos()]
}

#[cfg(feature = "render")]
/// The diffuse light of a picture: nine spherical harmonics of its light, each weighted by its pixel's solid angle,
/// convolved with the cosine lobe (Ramamoorthi and Hanrahan's 1, 2/3, 1/4 a band) and divided by pi, each with its
/// basis function's constant, so that a matte white surface facing n shows c0 + c1 y + c2 z + c3 x + c4 xy + c5 yz
/// + c6 (3 z^2 - 1) + c7 zx + c8 (x^2 - y^2) (`light.wgsl`'s `irradiance`).
pub(crate) fn harmonics(width: u32, height: u32, rgbe: &[u8]) -> [[f32; 4]; 9] {
    let mut sum = [[0f64; 3]; 9];
    // every pixel of a picture up to 1024 wide, else every k-th (a smooth function needs no more)
    let step = (width / 1024).max(1);
    for y in (0..height).step_by(step as usize) {
        let v = (y as f64 + 0.5) / height as f64;
        let solid = (std::f64::consts::TAU / width as f64 * step as f64) * (std::f64::consts::PI / height as f64 * step as f64) * (v * std::f64::consts::PI).sin();
        for x in (0..width).step_by(step as usize) {
            let at = ((y * width + x) * 4) as usize;
            let l = light(&rgbe[at..at + 4]);
            let [dx, dy, dz] = direction((x as f64 + 0.5) / width as f64, v);
            let basis = [0.282095, 0.488603 * dy, 0.488603 * dz, 0.488603 * dx, 1.092548 * dx * dy, 1.092548 * dy * dz, 0.315392 * (3.0 * dz * dz - 1.0), 1.092548 * dx * dz, 0.546274 * (dx * dx - dy * dy)];
            for (k, b) in basis.iter().enumerate() {
                for c in 0..3 {
                    sum[k][c] += l[c] * b * solid;
                }
            }
        }
    }
    // the convolution with the cosine lobe over pi, and each basis function's constant (applied to its monomial)
    let scale = [0.282095 * 1.0, 0.488603 * 2.0 / 3.0, 0.488603 * 2.0 / 3.0, 0.488603 * 2.0 / 3.0, 1.092548 * 0.25, 1.092548 * 0.25, 0.315392 * 0.25, 1.092548 * 0.25, 0.546274 * 0.25];
    std::array::from_fn(|k| [(sum[k][0] * scale[k]) as f32, (sum[k][1] * scale[k]) as f32, (sum[k][2] * scale[k]) as f32, 0.0])
}

#[cfg(feature = "render")]
/// The built-in studio's id (an `EnvironmentLight` without a picture): the player makes it (`studio`), nothing
/// uploads it.
pub(crate) const STUDIO: u32 = 0;

#[cfg(feature = "render")]
/// A studio's softboxes: azimuth and elevation of their centres (degrees; azimuth 0 is the picture's +x, 90 its +y),
/// their angular width and height, their radiance and color.
const SOFTBOXES: [(f64, f64, f64, f64, f64, [f64; 3]); 4] = [
    (-128.0, 41.0, 50.0, 34.0, 5.0, [1.0, 0.96, 0.9]), // the key: Manim's light source's way
    (-35.0, 8.0, 60.0, 34.0, 0.7, [0.9, 0.95, 1.0]),   // the fill, low beside the camera
    (90.0, 22.0, 10.0, 50.0, 3.5, [1.0, 1.0, 1.0]),    // a strip behind: rims
    (0.0, 80.0, 70.0, 20.0, 0.8, [1.0, 1.0, 1.0]),     // overhead
];

#[cfg(feature = "render")]
/// A photo studio's light all around, 1024 x 512: a dim room, its floor a little lighter than its walls, which darken
/// upward, and softboxes (`SOFTBOXES`), their edges soft over a degree and a half.
pub(crate) fn studio() -> (u32, u32, Vec<u8>) {
    use std::f64::consts::{PI, TAU};
    let (w, h) = (1024u32, 512u32);
    let smooth = |e0: f64, e1: f64, x: f64| {
        let t = ((x - e0) / (e1 - e0)).clamp(0.0, 1.0);
        t * t * (3.0 - 2.0 * t)
    };
    let soft = 1.5f64.to_radians();
    let mut out = Vec::with_capacity((w * h * 4) as usize);
    for y in 0..h {
        let el = PI / 2.0 - (y as f64 + 0.5) / h as f64 * PI;
        for x in 0..w {
            let az = (0.5 - (x as f64 + 0.5) / w as f64) * TAU;
            let room = if el < 0.0 { 0.12 } else { 0.1 - 0.07 * el.sin() };
            let mut c = [room; 3];
            for (at, up, wide, tall, radiance, color) in SOFTBOXES {
                let d = az - at.to_radians();
                let across = (d - TAU * (d / TAU).round()).abs() * el.cos();
                let above = (el - up.to_radians()).abs();
                let (half_w, half_h) = (wide.to_radians() / 2.0, tall.to_radians() / 2.0);
                let shown = smooth(half_w + soft, half_w - soft, across) * smooth(half_h + soft, half_h - soft, above);
                (0..3).for_each(|k| c[k] += shown * radiance * color[k]);
            }
            out.extend(rgbe(c));
        }
    }
    (w, h, out)
}

#[cfg(feature = "render")]
/// A picture's sun, lifted out of it into a light (a view lights by it as by a sun: `Player::views`): toward it (a
/// unit vector in the picture's frame) and the light it sends (what a white matte surface facing it shows: its
/// irradiance over pi). A point: a sun's disc (half a degree) gives a highlight its light alike, only spread on a
/// mirror's, where it is a pixel or less (experiments/b4-ibl/disc.py).
#[derive(Clone, Copy, Debug)]
pub(crate) struct Sun {
    pub(crate) toward: [f32; 3],
    pub(crate) light: [f32; 3],
}

#[cfg(feature = "render")]
/// How far from its brightest pixel a sun's light may reach (radians: farther, it is a window or a lamp's glow, and
/// stays in the picture); the ring of sky around it its light is measured against; how far above that sky its light
/// must stand (a fraction of the peak's); and the least share of the picture's light it holds.
const SUN_REACH: f64 = 8.0 * std::f64::consts::PI / 180.0;
#[cfg(feature = "render")]
const SUN_SKY: (f64, f64) = (8.0 * std::f64::consts::PI / 180.0, 12.0 * std::f64::consts::PI / 180.0);
#[cfg(feature = "render")]
const SUN_EDGE: f64 = 0.02;
#[cfg(feature = "render")]
const SUN_SHARE: f64 = 0.01;

#[cfg(feature = "render")]
/// Lift a picture's sun out of it: the region of light connected to its brightest pixel that stands above the sky
/// around it (by `SUN_EDGE` of the peak's excess), if the region lies within `SUN_REACH` of the peak and holds at
/// least `SUN_SHARE` of the picture's light. Its light above that sky becomes the sun; the region shows the sky. A
/// sun is a light a picture holds badly: nine harmonics cannot draw its shadow's edge, and the prefilter's samples
/// find a sun's disc rarely (experiments/b4-ibl).
fn lift_sun(width: u32, height: u32, pixels: &mut [u8]) -> Option<Sun> {
    use std::f64::consts::{PI, TAU};
    let (w, h) = (width as usize, height as usize);
    let luma = |c: [f64; 3]| 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    let solid = |y: usize| TAU / w as f64 * PI / h as f64 * ((y as f64 + 0.5) / h as f64 * PI).sin();
    let toward_of = |x: usize, y: usize| direction((x as f64 + 0.5) / w as f64, (y as f64 + 0.5) / h as f64);
    let lit = |x: usize, y: usize| light(&pixels[(y * w + x) * 4..][..4]);
    let (mut peak, mut brightest, mut total) = ((0, 0), 0.0, 0.0);
    for y in 0..h {
        for x in 0..w {
            let l = luma(lit(x, y));
            total += l * solid(y);
            if l > brightest {
                (peak, brightest) = ((x, y), l);
            }
        }
    }
    if brightest <= 0.0 {
        return None;
    }
    let toward = toward_of(peak.0, peak.1);
    let angle = |x: usize, y: usize| {
        let d = toward_of(x, y);
        (d[0] * toward[0] + d[1] * toward[1] + d[2] * toward[2]).clamp(-1.0, 1.0).acos()
    };
    // the sky around it: each channel's median over the ring (the rows it can reach, every column)
    let span = (SUN_SKY.1 / PI * h as f64).ceil() as usize + 1;
    let rows = peak.1.saturating_sub(span)..(peak.1 + span + 1).min(h);
    let mut ring: [Vec<f64>; 3] = Default::default();
    for y in rows.clone() {
        for x in 0..w {
            if (SUN_SKY.0..SUN_SKY.1).contains(&angle(x, y)) {
                let l = lit(x, y);
                (0..3).for_each(|c| ring[c].push(l[c]));
            }
        }
    }
    if ring[0].is_empty() {
        return None;
    }
    let sky: [f64; 3] = std::array::from_fn(|c| {
        let mid = ring[c].len() / 2;
        *ring[c].select_nth_unstable_by(mid, f64::total_cmp).1
    });
    let edge = luma(sky) + SUN_EDGE * (brightest - luma(sky));
    // the region: connected to the peak above the edge (across the picture's seam and over its poles), within reach
    let mut region = std::collections::HashSet::from([peak]);
    let mut stack = vec![peak];
    while let Some((x, y)) = stack.pop() {
        let mut next = vec![((x + 1) % w, y), ((x + w - 1) % w, y)];
        next.push(if y == 0 { ((x + w / 2) % w, 0) } else { (x, y - 1) });
        next.push(if y == h - 1 { ((x + w / 2) % w, h - 1) } else { (x, y + 1) });
        for n in next {
            if region.contains(&n) || luma(lit(n.0, n.1)) <= edge {
                continue;
            }
            if angle(n.0, n.1) >= SUN_REACH {
                return None; // it reaches too far: a window, a lamp's glow, a bright sky
            }
            region.insert(n);
            stack.push(n);
        }
    }
    // its light above the sky, and where it comes from
    let (mut excess, mut centroid) = ([0.0; 3], [0.0; 3]);
    for &(x, y) in &region {
        let l = lit(x, y);
        let above: [f64; 3] = std::array::from_fn(|c| (l[c] - sky[c]).max(0.0) * solid(y));
        let d = toward_of(x, y);
        (0..3).for_each(|c| {
            excess[c] += above[c];
            centroid[c] += luma(above) * d[c];
        });
    }
    if luma(excess) < SUN_SHARE * total {
        return None;
    }
    let length = (centroid[0] * centroid[0] + centroid[1] * centroid[1] + centroid[2] * centroid[2]).sqrt().max(1e-12);
    let shown = rgbe(sky);
    for &(x, y) in &region {
        pixels[(y * w + x) * 4..][..4].copy_from_slice(&shown);
    }
    Some(Sun { toward: centroid.map(|c| (c / length) as f32), light: excess.map(|c| (c / PI) as f32) })
}

#[cfg(feature = "render")]
/// An environment as the player keeps it: its picture (RGBE, its sun lifted out: until its cube is made), its diffuse
/// light, its prefiltered cube once made, the light a 1 in the cube stands for (its unit: 1 unless its brightest
/// light would pass a half float's range, 65504), and its sun.
pub(crate) struct Environment {
    pub(crate) width: u32,
    pub(crate) height: u32,
    pub(crate) rgbe: Vec<u8>,
    pub(crate) harmonics: [[f32; 4]; 9],
    pub(crate) cube: Option<wgpu::TextureView>,
    pub(crate) unit: f32,
    pub(crate) sun: Option<Sun>,
}

#[cfg(feature = "render")]
impl Environment {
    /// The environment of a picture, its sun lifted out of it (`lift_sun`).
    pub(crate) fn new(width: u32, height: u32, mut rgbe: Vec<u8>) -> Self {
        let sun = lift_sun(width, height, &mut rgbe);
        Self::of(width, height, rgbe, sun)
    }

    /// The environment of a picture as it is, with a sun.
    fn of(width: u32, height: u32, rgbe: Vec<u8>, sun: Option<Sun>) -> Self {
        let harmonics = harmonics(width, height, &rgbe);
        // the brightest channel of any pixel (a texel, a mip and a level average them: none is brighter), at half the
        // range's top
        let brightest = rgbe.chunks_exact(4).map(|p| light(p).into_iter().fold(0.0, f64::max)).fold(0.0, f64::max);
        let unit = (brightest / 32768.0).max(1.0) as f32;
        Self { width, height, rgbe, harmonics, cube: None, unit, sun }
    }
}

#[cfg(feature = "render")]
/// The prefilter's pipelines: the picture into a cube (`to_cube`), its mips (`halve`), and each roughness level of the
/// cube it lights with (`prefilter`).
pub(crate) struct Prefilter {
    to_cube: (wgpu::BindGroupLayout, wgpu::ComputePipeline),
    halve: (wgpu::BindGroupLayout, wgpu::ComputePipeline),
    prefilter: (wgpu::BindGroupLayout, wgpu::ComputePipeline),
    sampler: wgpu::Sampler,
}

#[cfg(feature = "render")]
impl Prefilter {
    pub(crate) fn new(device: &wgpu::Device) -> Self {
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor { label: Some("environment"), source: wgpu::ShaderSource::Wgsl(include_str!("environment.wgsl").into()) });
        let compute = wgpu::ShaderStages::COMPUTE;
        let entry = |binding, ty| wgpu::BindGroupLayoutEntry { binding, visibility: compute, ty, count: None };
        let out = |binding| entry(binding, wgpu::BindingType::StorageTexture { access: wgpu::StorageTextureAccess::WriteOnly, format: wgpu::TextureFormat::Rgba16Float, view_dimension: wgpu::TextureViewDimension::D2Array });
        let make = |label: &str, entries: &[wgpu::BindGroupLayoutEntry]| {
            let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some(label), entries });
            let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&layout)], immediate_size: 0 });
            let pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor { label: Some(label), layout: Some(&pipeline_layout), module: &shader, entry_point: Some(label), compilation_options: Default::default(), cache: None });
            (layout, pipeline)
        };
        let picture = entry(0, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Uint, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false });
        let level = entry(4, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2Array, multisampled: false });
        let cube = entry(5, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: true }, view_dimension: wgpu::TextureViewDimension::Cube, multisampled: false });
        let sampler = entry(2, wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering));
        let params = entry(3, wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: false, min_binding_size: None });
        Self {
            to_cube: make("to_cube", &[picture, out(1), params]),
            halve: make("halve", &[level, out(1)]),
            prefilter: make("prefilter", &[cube, out(1), sampler, params]),
            sampler: device.create_sampler(&wgpu::SamplerDescriptor { label: Some("environment"), mag_filter: wgpu::FilterMode::Linear, min_filter: wgpu::FilterMode::Linear, mipmap_filter: wgpu::MipmapFilterMode::Linear, ..Default::default() }),
        }
    }

    /// The cube an environment lights with: its picture into a cube of `SIDE`² with every mip (the source), then each
    /// level of the result the source's light averaged over the GGX lobe of its roughness (`SAMPLES` importance samples,
    /// each read from the source's mip whose texels match the sample's solid angle, Krivanek and Colbert's filtered
    /// importance sampling, but none coarser than `COARSEST`), level 0 the source's own.
    pub(crate) fn run(&self, device: &wgpu::Device, queue: &wgpu::Queue, encoder: &mut wgpu::CommandEncoder, env: &Environment) -> wgpu::TextureView {
        let size = wgpu::Extent3d { width: env.width, height: env.height, depth_or_array_layers: 1 };
        let picture = device.create_texture(&wgpu::TextureDescriptor { label: Some("environment picture"), size, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format: wgpu::TextureFormat::Rgba8Uint, usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST, view_formats: &[] });
        queue.write_texture(picture.as_image_copy(), &env.rgbe, wgpu::TexelCopyBufferLayout { offset: 0, bytes_per_row: Some(4 * env.width), rows_per_image: Some(env.height) }, size);
        let cube = |label, mips| {
            device.create_texture(&wgpu::TextureDescriptor {
                label: Some(label),
                size: wgpu::Extent3d { width: SIDE, height: SIDE, depth_or_array_layers: 6 },
                mip_level_count: mips,
                sample_count: 1,
                dimension: wgpu::TextureDimension::D2,
                format: wgpu::TextureFormat::Rgba16Float,
                usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::COPY_SRC,
                view_formats: &[],
            })
        };
        let mips = SIDE.ilog2() + 1;
        let (source, out) = (cube("environment source", mips), cube("environment", LEVELS));
        let level = |t: &wgpu::Texture, mip: u32| t.create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::D2Array), base_mip_level: mip, mip_level_count: Some(1), ..Default::default() });
        let bind = |layout: &wgpu::BindGroupLayout, entries: &[(u32, wgpu::BindingResource)]| {
            let entries: Vec<wgpu::BindGroupEntry> = entries.iter().map(|(binding, resource)| wgpu::BindGroupEntry { binding: *binding, resource: resource.clone() }).collect();
            device.create_bind_group(&wgpu::BindGroupDescriptor { label: None, layout, entries: &entries })
        };
        let view = wgpu::BindingResource::TextureView;
        let picture_view = picture.create_view(&Default::default());
        let sources: Vec<wgpu::TextureView> = (0..mips).map(|mip| level(&source, mip)).collect();
        let outs: Vec<wgpu::TextureView> = (0..LEVELS).map(|l| level(&out, l)).collect();
        let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("environment"), timestamp_writes: None });
        let groups = |side: u32| side.div_ceil(8);
        // the source: level 0 from the picture, then each mip the average of the one before
        let uniform = |params: [f32; 8]| {
            let buffer = device.create_buffer(&wgpu::BufferDescriptor { label: Some("prefilter"), size: 32, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
            queue.write_buffer(&buffer, 0, bytemuck::cast_slice(&params));
            buffer
        };
        let scale = uniform([0.0, 0.0, 0.0, 0.0, 1.0 / env.unit, 0.0, 0.0, 0.0]);
        pass.set_pipeline(&self.to_cube.1);
        pass.set_bind_group(0, &bind(&self.to_cube.0, &[(0, view(&picture_view)), (1, view(&sources[0])), (3, scale.as_entire_binding())]), &[]);
        pass.dispatch_workgroups(groups(SIDE), groups(SIDE), 6);
        for mip in 1..mips {
            pass.set_pipeline(&self.halve.1);
            pass.set_bind_group(0, &bind(&self.halve.0, &[(4, view(&sources[mip as usize - 1])), (1, view(&sources[mip as usize]))]), &[]);
            pass.dispatch_workgroups(groups(SIDE >> mip), groups(SIDE >> mip), 6);
        }
        // the levels: the GGX lobe's average of the source
        let source_cube = source.create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::Cube), ..Default::default() });
        for l in 0..LEVELS {
            let t = l as f32 / (LEVELS - 1) as f32;
            let perceptual = 1.0 - (1.0 - t).sqrt(); // l = (LEVELS - 1) r (2 - r)
            let samples: u32 = if l == 0 { 1 } else { SAMPLES };
            let buffer = uniform([perceptual * perceptual, samples as f32, (SIDE * SIDE) as f32, (SIDE / COARSEST).ilog2() as f32, 1.0, 0.0, 0.0, 0.0]);
            pass.set_pipeline(&self.prefilter.1);
            pass.set_bind_group(0, &bind(&self.prefilter.0, &[(5, view(&source_cube)), (1, view(&outs[l as usize])), (2, wgpu::BindingResource::Sampler(&self.sampler)), (3, buffer.as_entire_binding())]), &[]);
            pass.dispatch_workgroups(groups(SIDE >> l), groups(SIDE >> l), 6);
        }
        drop(pass);
        out.create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::Cube), ..Default::default() })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn malformed_radiance_shapes_fail_without_panicking_or_allocating_the_header() {
        for (width, height) in [(0, 1), (1, 0), (65536, 16384), (8, 1 << 29), (u32::MAX, u32::MAX)] {
            let header = format!("#?RADIANCE\n\n-Y {height} +X {width}\n");
            assert!(read_hdr(header.as_bytes()).is_err(), "{width} x {height}");
        }
    }

    #[test]
    fn radiance_flat_and_encoded_rows_preserve_their_pixels() {
        let pixels: Vec<u8> = (0..64).collect();
        let mut flat = b"#?RADIANCE\n\n-Y 1 +X 16\n".to_vec();
        flat.extend_from_slice(&pixels);
        assert_eq!(read_hdr(&flat).unwrap(), (16, 1, pixels.clone()));
        let mut encoded = b"#?RADIANCE\n\n-Y 1 +X 16\n".to_vec();
        let start = encoded.len();
        encoded.extend_from_slice(&[2, 2, 0, 16]);
        for c in 0..4 {
            encoded.push(16);
            encoded.extend(pixels.iter().skip(c).step_by(4));
        }
        assert_eq!(read_hdr(&encoded).unwrap(), (16, 1, pixels));
        for end in 0..encoded.len() {
            assert!(read_hdr(&encoded[..end]).is_err(), "truncated at {end}");
        }
        encoded[start + 3] = 15;
        assert!(read_hdr(&encoded).unwrap_err().contains("width"));
    }

    #[test]
    fn the_shortest_radiance_runs_meet_the_allocation_bound() {
        for width in [8u32, 127, 128, 129, 32767] {
            let mut file = format!("#?RADIANCE\n\n-Y 2 +X {width}\n").into_bytes();
            let header = file.len();
            for _ in 0..2 {
                file.extend([2, 2, (width >> 8) as u8, width as u8]);
                for value in [128, 64, 32, 129] {
                    let mut left = width;
                    while left > 0 {
                        let count = left.min(127);
                        file.extend([128 + count as u8, value]);
                        left -= count;
                    }
                }
            }
            assert_eq!(file.len() - header, (4 + 8 * width.div_ceil(127)) as usize * 2);
            assert_eq!(read_hdr(&file).unwrap(), (width, 2, [128, 64, 32, 129].repeat(width as usize * 2)));
        }
    }

    #[test]
    fn narrowing_preserves_a_single_row_and_the_pixels_of_odd_edges() {
        let pixels = [128, 64, 32, 129].repeat(8192);
        let (w, h, out) = narrowed(8192, 1, pixels);
        assert_eq!((w, h), (4096, 1));
        assert_eq!(out, [128, 64, 32, 129].repeat(4096));
        let mut pixels = vec![0; 4097 * 3 * 4];
        pixels[4097 * 3 * 4 - 4..].copy_from_slice(&[128, 0, 0, 133]);
        let (w, h, out) = narrowed(4097, 3, pixels);
        assert_eq!((w, h), (2049, 2));
        assert!(out[..out.len() - 4].iter().all(|&b| b == 0));
        assert_eq!(&out[out.len() - 4..], &[128, 0, 0, 133]);
    }

    #[cfg(feature = "render")]
    /// A uniform picture's diffuse light is its light alone, from every side: c0 is the light, the rest nothing.
    #[test]
    fn a_uniform_picture_lights_every_side_alike() {
        let (w, h) = (256, 128);
        let mut rgbe = Vec::with_capacity(w * h * 4);
        for _ in 0..w * h {
            rgbe.extend_from_slice(&[128, 128, 128, 129]); // 128 * 2^(129 - 136) = 1
        }
        let sh = harmonics(w as u32, h as u32, &rgbe);
        // the light a white matte surface shows: c0 (the rest vanish over the sphere)
        assert!((sh[0][0] - 1.0).abs() < 0.01, "{:?}", sh[0]);
        for k in 1..9 {
            assert!(sh[k][0].abs() < 0.01, "{k}: {:?}", sh[k]);
        }
    }

    /// A picture's centre is seen looking along +x, its top straight up, and across it to the right is turning right
    /// (from +x toward -y, as someone inside it turns, z up).
    #[cfg(feature = "render")]
    #[test]
    fn a_picture_lies_around_as_seen_from_inside() {
        let near = |a: [f64; 3], b: [f64; 3]| a.iter().zip(b).all(|(x, y)| (x - y).abs() < 1e-9);
        assert!(near(direction(0.5, 0.5), [1.0, 0.0, 0.0]));
        assert!(near(direction(0.75, 0.5), [0.0, -1.0, 0.0]));
        assert!(near(direction(0.25, 0.5), [0.0, 1.0, 0.0]));
        assert!(near(direction(0.3, 0.0), [0.0, 0.0, 1.0]));
    }

    /// An environment's cube as the GPU prefilters it: each level's six faces (+x, -x, +y, -y, +z, -z), rows from the
    /// top, RGBA f16 (its bytes), and how long the prefilter took (the picture's upload in it).
    #[cfg(feature = "render")]
    fn prefiltered(env: &Environment) -> (Vec<Vec<u8>>, std::time::Duration) {
        crate::render::with_gpu(|gpu| {
            let prefilter = Prefilter::new(&gpu.device);
            let mut encoder = gpu.device.create_command_encoder(&Default::default());
            let start = std::time::Instant::now();
            let cube = prefilter.run(&gpu.device, &gpu.queue, &mut encoder, env);
            gpu.queue.submit(Some(encoder.finish()));
            gpu.device.poll(wgpu::PollType::wait_indefinitely()).expect("poll");
            let took = start.elapsed();
            let levels = (0..LEVELS)
                .map(|level| {
                    let side = SIDE >> level;
                    let row = (8 * side).next_multiple_of(256);
                    let buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (row * side * 6) as u64, usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ, mapped_at_creation: false });
                    let mut encoder = gpu.device.create_command_encoder(&Default::default());
                    encoder.copy_texture_to_buffer(
                        wgpu::TexelCopyTextureInfo { texture: cube.texture(), mip_level: level, origin: wgpu::Origin3d::ZERO, aspect: wgpu::TextureAspect::All },
                        wgpu::TexelCopyBufferInfo { buffer: &buffer, layout: wgpu::TexelCopyBufferLayout { offset: 0, bytes_per_row: Some(row), rows_per_image: Some(side) } },
                        wgpu::Extent3d { width: side, height: side, depth_or_array_layers: 6 },
                    );
                    gpu.queue.submit(Some(encoder.finish()));
                    buffer.slice(..).map_async(wgpu::MapMode::Read, |r| r.expect("map"));
                    gpu.device.poll(wgpu::PollType::wait_indefinitely()).expect("poll");
                    let data = buffer.slice(..).get_mapped_range().expect("mapped");
                    (0..(side * 6) as usize).flat_map(|r| data[r * row as usize..][..8 * side as usize].to_vec()).collect()
                })
                .collect();
            (levels, took)
        })
        .expect("a GPU")
    }

    /// A half float's value (finite ones).
    #[cfg(feature = "render")]
    fn half(bits: u16) -> f32 {
        let (exponent, mantissa) = (((bits >> 10) & 0x1f) as i32, (bits & 0x3ff) as f32);
        let size = if exponent == 0 { mantissa * 2f32.powi(-24) } else { (1.0 + mantissa / 1024.0) * 2f32.powi(exponent - 15) };
        if bits >> 15 == 1 { -size } else { size }
    }

    /// Light from above alone (a picture bright in its upper half, black below): straight up every level shows the
    /// light, straight down none at any roughness (a lobe's tail read from too coarse a mip would bring the sky into
    /// the floor's reflection), and the horizon half.
    #[cfg(feature = "render")]
    #[test]
    fn a_dark_floor_reflects_no_sky_at_any_roughness() {
        let (width, height) = (256u32, 128u32);
        let rgbe: Vec<u8> = (0..width * height).flat_map(|i| if i < width * height / 2 { [128, 128, 128, 129] } else { [0; 4] }).collect();
        let (levels, _) = prefiltered(&Environment::new(width, height, rgbe));
        for (level, bytes) in levels.iter().enumerate() {
            let side = (SIDE >> level) as usize;
            // a texel's red, in a face's middle column: the centres of +z (face 4) and -z (5), and the horizon across
            // +y's (2, whose rows run from -z up to +z: the texels either side of its middle row)
            let red = |face: usize, row: usize| {
                let at = 8 * ((face * side + row) * side + side / 2);
                half(u16::from_le_bytes([bytes[at], bytes[at + 1]]))
            };
            let (up, down, horizon) = (red(4, side / 2), red(5, side / 2), (red(2, side / 2 - 1) + red(2, side / 2)) / 2.0);
            assert!(up > 0.99, "level {level}: up {up}");
            assert!(down < 0.003, "level {level}: down {down}");
            assert!((horizon - 0.5).abs() < 0.03, "level {level}: the horizon {horizon}");
        }
    }

    /// A picture of a grey sky (`sky` everywhere) and, toward `sun` (azimuth and elevation, degrees), a disc of
    /// angular radius `radius` (degrees) and light `glow` (each pixel's share of the disc found by 8 x 8 points), and
    /// the light the disc sends a surface facing it, over pi (what a white matte one shows).
    #[cfg(feature = "render")]
    fn sunny(width: u32, height: u32, sky: f64, sun: (f64, f64), radius: f64, glow: f64) -> (Vec<u8>, f64) {
        use std::f64::consts::PI;
        let (az, el) = (sun.0.to_radians(), sun.1.to_radians());
        let toward = [el.cos() * az.cos(), el.cos() * az.sin(), el.sin()];
        let (mut pixels, mut sent) = (Vec::new(), 0.0);
        for y in 0..height {
            let solid = 2.0 * PI / width as f64 * PI / height as f64 * ((y as f64 + 0.5) / height as f64 * PI).sin();
            for x in 0..width {
                let mut inside = 0.0;
                for k in 0..64 {
                    let d = direction((x as f64 + ((k % 8) as f64 + 0.5) / 8.0) / width as f64, (y as f64 + ((k / 8) as f64 + 0.5) / 8.0) / height as f64);
                    if d[0] * toward[0] + d[1] * toward[1] + d[2] * toward[2] > radius.to_radians().cos() {
                        inside += 1.0 / 64.0;
                    }
                }
                sent += inside * glow * solid;
                pixels.extend(rgbe([sky + inside * glow; 3]));
            }
        }
        (pixels, sent / PI)
    }

    /// A sun is lifted out of its picture: where it is and its light become a sun's, and the picture shows the sky
    /// where it was.
    #[cfg(feature = "render")]
    #[test]
    fn a_sun_is_lifted_out_of_its_picture() {
        let (pixels, shown) = sunny(1024, 512, 0.5, (-60.0, 35.0), 0.27, 40_000.0);
        let env = Environment::new(1024, 512, pixels);
        let sun = env.sun.expect("a sun");
        let (az, el) = ((-60f64).to_radians(), 35f64.to_radians());
        let truth = [el.cos() * az.cos(), el.cos() * az.sin(), el.sin()];
        let cos = (0..3).map(|k| sun.toward[k] as f64 * truth[k]).sum::<f64>();
        assert!(cos.acos().to_degrees() < 0.1, "{} degrees off", cos.acos().to_degrees());
        assert!((sun.light[0] as f64 / shown - 1.0).abs() < 0.01, "{:?} vs {shown}", sun.light);
        let brightest = env.rgbe.chunks_exact(4).map(|p| light(p)[0]).fold(0.0, f64::max);
        assert!(brightest < 0.51, "{brightest}");
    }

    /// A window (a bright patch wider than a sun can be) stays in its picture.
    #[cfg(feature = "render")]
    #[test]
    fn a_window_stays_in_its_picture() {
        let (pixels, _) = sunny(1024, 512, 0.5, (30.0, 20.0), 12.0, 20.0);
        let env = Environment::new(1024, 512, pixels.clone());
        assert!(env.sun.is_none());
        assert_eq!(env.rgbe, pixels);
        let (width, height, studio) = studio();
        assert!(Environment::new(width, height, studio).sun.is_none(), "the studio's softboxes are not suns");
    }

    /// A picture wider than an environment keeps is halved until it is not, its light kept.
    #[test]
    fn a_wide_picture_is_halved() {
        let (width, height) = (8200u32, 4u32);
        let pixels: Vec<u8> = (0..width * height).flat_map(|i| if i % 2 == 0 { [128, 128, 128, 130] } else { [0; 4] }).collect();
        let (w, h, out) = narrowed(width, height, pixels);
        assert_eq!((w, h), (2050, 1));
        assert!(out.chunks_exact(4).all(|p| (light(p)[0] - 1.0).abs() < 1e-6), "{:?}", &out[..8]); // half of 2, on average
    }

    /// A picture brighter than a half float can hold (an unclipped sun's light: here 2^17 everywhere) keeps its light:
    /// the cube holds it in the environment's unit.
    #[cfg(feature = "render")]
    #[test]
    fn light_past_a_half_floats_range_keeps_its_light() {
        let rgbe: Vec<u8> = (0..64 * 32).flat_map(|_| [128, 128, 128, 146]).collect(); // 128 * 2^(146 - 136) = 2^17
        let env = Environment::new(64, 32, rgbe);
        assert!(env.unit > 1.0);
        let (levels, _) = prefiltered(&env);
        for (level, bytes) in levels.iter().enumerate() {
            for texel in bytes.chunks_exact(8) {
                let shown = half(u16::from_le_bytes([texel[0], texel[1]])) * env.unit;
                assert!((shown / 131072.0 - 1.0).abs() < 0.002, "level {level}: {shown}");
            }
        }
    }

    /// A measurement, not a check (experiments/b4-ibl): the harmonics and prefiltered cube of the Radiance file at
    /// MANIMGX_HDR (its sun lifted out, unless MANIMGX_KEEP_SUN is set), written to MANIMGX_DUMP: 27 f32 (the
    /// harmonics' rgb), the cube's unit, its sun (toward, light: 6 f32, zeros if none), then each level as
    /// `prefiltered` reads it.
    #[cfg(feature = "render")]
    #[test]
    #[ignore]
    fn dump_prefiltered() {
        let (Ok(path), Ok(dump)) = (std::env::var("MANIMGX_HDR"), std::env::var("MANIMGX_DUMP")) else { return };
        let (width, height, rgbe) = read_hdr(&std::fs::read(path).expect("read")).expect("a Radiance file");
        // (MANIMGX_KEEP_SUN: the picture as it is, its sun in it)
        let start = std::time::Instant::now();
        let env = if std::env::var("MANIMGX_KEEP_SUN").is_ok() { Environment::of(width, height, rgbe, None) } else { Environment::new(width, height, rgbe) };
        eprintln!("made in {:.1} ms (its sun, harmonics and unit, on the CPU)", start.elapsed().as_secs_f64() * 1e3);
        let mut bytes: Vec<u8> = env.harmonics.iter().flat_map(|c| c[..3].iter().flat_map(|x| x.to_le_bytes())).collect();
        bytes.extend(env.unit.to_le_bytes());
        let sun = env.sun.map_or([0.0; 6], |s| [s.toward[0], s.toward[1], s.toward[2], s.light[0], s.light[1], s.light[2]]);
        bytes.extend(sun.iter().flat_map(|x| x.to_le_bytes()));
        let (_, cold) = prefiltered(&env);
        let (levels, warm) = prefiltered(&env);
        eprintln!("prefiltered {width}x{height} in {:.1} ms, again {:.1} ms (the picture's upload in each)", cold.as_secs_f64() * 1e3, warm.as_secs_f64() * 1e3);
        bytes.extend(levels.concat());
        std::fs::write(dump, bytes).expect("write");
    }

    /// A run-length encoded Radiance file reads back as the pixels written.
    #[test]
    fn a_radiance_file_reads_back() {
        let (w, h) = (16u32, 2u32);
        let mut file = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 2 +X 16\n".to_vec();
        for y in 0..h {
            file.extend_from_slice(&[2, 2, 0, w as u8]);
            for c in 0..4u8 {
                // a run of 16 of one value
                file.extend_from_slice(&[128 + 16, 10 * y as u8 + c]);
            }
        }
        let (width, height, rgbe) = read_hdr(&file).expect("read");
        assert_eq!((width, height), (w, h));
        assert_eq!(&rgbe[..4], &[0, 1, 2, 3]);
        assert_eq!(&rgbe[(16 * 4) as usize..(16 * 4 + 4) as usize], &[10, 11, 12, 13]);
    }
}
