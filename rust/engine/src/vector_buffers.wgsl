// What `vector.wgsl` reads, from storage buffers: the CPU's arrays, the see-through lists, a non-planar path's strokes'
// depths, the records the flatten writes, and a 3D view's raster base sample by sample.

@group(0) @binding(1) var<storage, read> ctrl: array<vec4<f32>>;     // 4 per curve; the first's w: its flatness
@group(0) @binding(2) var<storage, read> subs: array<vec4<u32>>;     // first curve, end curve, closed
@group(0) @binding(3) var<storage, read> objects: array<Object>;
@group(0) @binding(4) var<storage, read> rows: array<vec4<f32>>;
@group(0) @binding(5) var<storage, read> tiles: array<u32>;          // per tile, its first entry (and one past the end); the entries

@group(1) @binding(5) var<storage, read> heads: array<u32>;
@group(1) @binding(6) var<storage, read> nodes: array<Node>;

// where it has see-through fragments, its raster base sample by sample: color (premultiplied), depth
@group(1) @binding(7) var base_samples: SampleColor;
@group(1) @binding(18) var base_light_samples: SampleColor; // (its light: `base_at`)
@group(1) @binding(8) var base_sample_depths: SampleDepth;

// the depth of a non-planar path's strokes per pixel of their atlas (as `stroke_depths` keeps it)
@group(1) @binding(9) var<storage, read> stroke_depths_in: array<u32>;

@group(3) @binding(0) var<storage, read> fill_in: array<Seg>;
@group(3) @binding(1) var<storage, read> stroke_in: array<Seg>;

// per pixel of the atlas, the depth a non-planar path's stroke has there: that of the nearest of its pieces through
// the pixel's center, else of the nearest that covers it (a bit for "through the center", then the depth's bits
// inverted, without their last: 0 none), so that the largest is the one
@group(3) @binding(2) var<storage, read_write> stroke_depths: array<atomic<u32>>;

// The body's loaders: an object's fields one at a time (a whole object is more than a pass reads of it, and loading
// it whole costs time), then each array's element.
fn t1x_of(o: u32) -> vec4<f32> { return objects[o].t1x; }
fn t1y_of(o: u32) -> vec4<f32> { return objects[o].t1y; }
fn t2x_of(o: u32) -> vec4<f32> { return objects[o].t2x; }
fn t2y_of(o: u32) -> vec4<f32> { return objects[o].t2y; }
fn t1w_of(o: u32) -> vec4<f32> { return objects[o].t1w; }
fn t2w_of(o: u32) -> vec4<f32> { return objects[o].t2w; }
fn rect_of(o: u32) -> vec4<f32> { return objects[o].rect; }
fn atlas_of(o: u32) -> vec4<u32> { return objects[o].atlas; }
fn ids_of(o: u32) -> vec4<u32> { return objects[o].ids; }
fn params_of(o: u32) -> vec4<f32> { return objects[o].params; }
fn dash_of(o: u32) -> vec4<f32> { return objects[o].dash; }
fn scale_of(o: u32) -> vec4<f32> { return objects[o].scale; }
fn place_of(o: u32) -> vec4<f32> { return objects[o].place; }
fn flags_of(o: u32) -> vec4<u32> { return objects[o].flags; }
fn slots_of(o: u32) -> vec4<u32> { return objects[o].slots; }
fn pieces_of(o: u32) -> vec4<u32> { return objects[o].pieces; }
fn fill_of(o: u32) -> vec4<f32> { return objects[o].fill; }
fn stroke_of(o: u32) -> vec4<f32> { return objects[o].stroke; }
fn background_of(o: u32) -> vec4<f32> { return objects[o].background; }
fn gradient_of(o: u32) -> vec4<f32> { return objects[o].gradient; }
fn brush_of(o: u32) -> vec4<u32> { return objects[o].brush; }
fn brush2_of(o: u32) -> vec4<u32> { return objects[o].brush2; }
fn material_of(o: u32) -> vec4<f32> { return objects[o].material; }
fn normal_of(o: u32) -> vec4<f32> { return objects[o].normal; }
fn t1z_of(o: u32) -> vec4<f32> { return objects[o].t1z; }
fn t2z_of(o: u32) -> vec4<f32> { return objects[o].t2z; }
fn near_of(o: u32) -> vec4<f32> { return objects[o].near; }

fn control(i: u32) -> vec4<f32> {
    return ctrl[i];
}

fn subpath(i: u32) -> vec4<u32> {
    return subs[i];
}

fn row_at(i: u32) -> vec4<f32> {
    return rows[i];
}

fn tile_entry(i: u32) -> u32 {
    return tiles[i];
}

fn list_head(i: u32) -> u32 {
    return heads[i];
}

fn list_node(i: u32) -> Node {
    var n = nodes[i];
    n.depth = -n.depth; // from the far plane, as paths' depths (reversed Z)
    return n;
}

fn stroke_depth(i: u32) -> u32 {
    return stroke_depths_in[i];
}

fn fill_record(i: u32) -> Seg {
    return fill_in[i];
}

fn stroke_record(i: u32) -> Seg {
    return stroke_in[i];
}

fn base_sample(gid: vec2<u32>, s: u32) -> Mix {
    let p = textureLoad(base_samples, gid, i32(s));
    if ((frame.counts.w & 1u) == 0u) {
        return painted_mix(p);
    }
    return Mix(p, textureLoad(base_light_samples, gid, i32(s)));
}

fn base_sample_depth(gid: vec2<u32>, s: u32) -> f32 {
    return -textureLoad(base_sample_depths, gid, i32(s)); // its depth from the far plane (reversed Z)
}

fn keep_stroke_depth(i: u32, depth: u32) {
    atomicMax(&stroke_depths[i], depth);
}
