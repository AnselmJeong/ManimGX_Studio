// What `blend.wgsl` reads, from storage buffers.

@group(0) @binding(1) var<storage, read> vertices: array<vec4<f32>>;
@group(0) @binding(2) var<storage, read> links: array<vec2<u32>>;
@group(0) @binding(4) var<storage, read> instances: array<Instance>;
@group(0) @binding(5) var<storage, read> rows: array<vec4<f32>>;
@group(0) @binding(6) var<storage, read> extras: array<vec4<f32>>; // mesh vertex: normal xyz, u

fn row_at(i: u32) -> vec4<f32> {
    return rows[i];
}

// The body's loaders: an object's fields one at a time, then each array's element.
fn c1_0_of(i: u32) -> vec4<f32> { return instances[i].c1_0; }
fn c1_1_of(i: u32) -> vec4<f32> { return instances[i].c1_1; }
fn c1_2_of(i: u32) -> vec4<f32> { return instances[i].c1_2; }
fn c1_3_of(i: u32) -> vec4<f32> { return instances[i].c1_3; }
fn c2_0_of(i: u32) -> vec4<f32> { return instances[i].c2_0; }
fn c2_1_of(i: u32) -> vec4<f32> { return instances[i].c2_1; }
fn c2_2_of(i: u32) -> vec4<f32> { return instances[i].c2_2; }
fn c2_3_of(i: u32) -> vec4<f32> { return instances[i].c2_3; }
fn m1_0_of(i: u32) -> vec4<f32> { return instances[i].m1_0; }
fn m1_1_of(i: u32) -> vec4<f32> { return instances[i].m1_1; }
fn m1_2_of(i: u32) -> vec4<f32> { return instances[i].m1_2; }
fn m2_0_of(i: u32) -> vec4<f32> { return instances[i].m2_0; }
fn m2_1_of(i: u32) -> vec4<f32> { return instances[i].m2_1; }
fn m2_2_of(i: u32) -> vec4<f32> { return instances[i].m2_2; }
fn params_of(i: u32) -> vec4<f32> { return instances[i].params; }
fn extra_of(i: u32) -> vec4<f32> { return instances[i].extra; }
fn ids_of(i: u32) -> vec4<u32> { return instances[i].ids; }
fn fill_of(i: u32) -> vec4<f32> { return instances[i].fill; }
fn stroke_of(i: u32) -> vec4<f32> { return instances[i].stroke; }
fn background_of(i: u32) -> vec4<f32> { return instances[i].background; }
fn gradient_of(i: u32) -> vec4<f32> { return instances[i].gradient; }
fn brush_of(i: u32) -> vec4<u32> { return instances[i].brush; }
fn brush2_of(i: u32) -> vec4<u32> { return instances[i].brush2; }
fn material_of(i: u32) -> vec4<f32> { return instances[i].material; }

fn vertex(k: u32) -> vec4<f32> {
    return vertices[k];
}

fn link(k: u32) -> vec2<u32> {
    return links[k];
}

fn vertex_extra(k: u32) -> vec4<f32> {
    return extras[k];
}
