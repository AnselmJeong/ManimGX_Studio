// `vector.wgsl`'s compute passes: the flatten, a thread per slot, writing the
// records to storage; the composite, a thread per pixel, writing the view as a storage texture, and (a 3D view's)
// the pixels where depths cross, a thread each; and a 3D view's slab bounds, a thread per pixel.

@group(1) @binding(3) var view_out: texture_storage_2d<rgba8unorm, write>;
@group(1) @binding(19) var light_out: texture_storage_2d<rgba16float, write>; // (1x1 where the group shows its pixels)

// Pixel `gid` as the group leaves it: shown, or (a group of a view with lit content before its last, or its last where
// the view glows: `frame.counts.w` bit 2) its mix as it is, its paint and its light, for the next group to lay over or
// the glow to be spread from and shown with (`bloom.wgsl`).
fn store(gid: vec2<u32>, m: Mix) {
    if (lighting && (frame.counts.w & 2u) != 0u) {
        textureStore(view_out, gid, m[0]);
        textureStore(light_out, gid, m[1]);
        return;
    }
    textureStore(view_out, gid, seen(m));
}

@group(2) @binding(0) var<storage, read_write> fill_out: array<Seg>;
@group(2) @binding(1) var<storage, read_write> stroke_out: array<Seg>;

@compute @workgroup_size(64)
fn flatten_fill(@builtin(global_invocation_id) gid: vec3<u32>, @builtin(num_workgroups) groups: vec3<u32>) {
    let q = gid.x + gid.y * groups.x * 64u;
    if (q < frame.tiles.z) {
        fill_out[q] = fill_slot(q);
    }
}

@compute @workgroup_size(64)
fn flatten_stroke(@builtin(global_invocation_id) gid: vec3<u32>, @builtin(num_workgroups) groups: vec3<u32>) {
    let q = gid.x + gid.y * groups.x * 64u;
    if (q < frame.tiles.w) {
        stroke_out[q] = stroke_slot(q);
    }
}

// The pixels where depths cross, as the composite lists them for the second pass: how many, then each (x | y << 16);
// and the second pass's workgroups, as the count leaves them (an indirect dispatch's: a group of its own, which the
// second pass, reading it as its dispatch, does not bind).
struct Crossings {
    count: atomic<u32>,
    at: array<u32>,
};
@group(1) @binding(14) var<storage, read_write> crossings: Crossings;
@group(2) @binding(0) var<storage, read_write> crossing_groups: array<u32, 3>;

// Whether the group lays nothing of its own in pixel gid, only what lies under it: no path's layer in its tile, no
// see-through fragment in its row. Such pixels are `keep`'s, the rest the composite's.
fn bare(gid: vec2<u32>) -> bool {
    let tile = (gid.y / TILE) * frame.tiles.x + gid.x / TILE;
    let listed = lists && frame.lists.x == 1u && gid.y >= frame.lists.y && gid.y < frame.lists.z;
    return tile_entry(tile) == tile_entry(tile + 1u) && !listed;
}

// The composite: each pixel whose layers come in their order; the others listed (where depths cross: `crossed`, in
// a pass of their own, so that they keep no other pixel waiting).
@compute @workgroup_size(16, 16)
fn composite(@builtin(global_invocation_id) gid: vec3<u32>) {
    if (gid.x >= u32(frame.size.x) || gid.y >= u32(frame.size.y) || bare(gid.xy)) {
        return;
    }
    let b = begin(gid.xy);
    let l = laid(gid.xy, b);
    if (l.ordered) {
        store(gid.xy, l.mix);
    } else {
        crossings.at[atomicAdd(&crossings.count, 1u)] = gid.x | (gid.y << 16u);
    }
}

// The pixels where the group lays nothing of its own (`bare`): what lies under them, laid as the composite lays it (by
// the same functions, so to the same values), in a pass without the code of the paths' layers, whose registers it
// would pay for unused.
@compute @workgroup_size(16, 16)
fn keep(@builtin(global_invocation_id) gid: vec3<u32>) {
    if (gid.x >= u32(frame.size.x) || gid.y >= u32(frame.size.y) || !bare(gid.xy)) {
        return;
    }
    let b = begin(gid.xy);
    store(gid.xy, finish(b.fresh, b, gid.xy));
}

// A 3D view's slab bounds (`bound`), for its see-through points to find their slab by, before they are drawn.
@group(2) @binding(0) var bounds_out: texture_storage_2d<rgba32float, write>;

@compute @workgroup_size(16, 16)
fn bound_slabs(@builtin(global_invocation_id) gid: vec3<u32>) {
    if (gid.x >= u32(frame.size.x) || gid.y >= u32(frame.size.y)) {
        return;
    }
    textureStore(bounds_out, gid.xy, bound(gid.xy));
}

@compute @workgroup_size(1)
fn count_crossings() {
    let groups = (atomicLoad(&crossings.count) + 63u) / 64u;
    crossing_groups[0] = min(groups, 65535u);
    crossing_groups[1] = (groups + 65534u) / 65535u;
    crossing_groups[2] = 1u;
}

@compute @workgroup_size(64)
fn settle_crossings(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) groups: vec3<u32>) {
    let i = id.x + id.y * groups.x * 64u;
    if (i >= atomicLoad(&crossings.count)) {
        return;
    }
    let at = crossings.at[i];
    let gid = vec2<u32>(at & 0xffffu, at >> 16u);
    store(gid, crossed(gid, begin(gid)));
}
