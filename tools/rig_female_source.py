"""Fit the female anatomical weight source and skeleton through the body shape field."""
import bpy
from female_reference_shape import fit_female_reference


def fit_weight_source(source,human,hi,rig):
    # Generate a cheap low-poly cage, without texture baking. Its edges define
    # the same measurements as the body fit. Loose vertices sample that field
    # for the dense weight source and bones without reshaping the game mesh.
    eyes=source.add_part(human,source.EYES_MHCLO,'Eyes')
    cage=source.make_low(human,eyes)
    cage_points=[cage.matrix_world@v.co for v in cage.data.vertices]
    n=len(cage_points)
    hi_points=[hi.matrix_world@v.co for v in hi.data.vertices]
    bones=list(rig.data.bones)
    bone_points=[rig.matrix_world@co for b in bones for co in (b.head_local,b.tail_local)]
    data=bpy.data.meshes.new('FemaleShapeProbes')
    data.from_pydata(cage_points+hi_points+bone_points,[],[tuple(p.vertices) for p in cage.data.polygons])
    probe=bpy.data.objects.new('FemaleShapeProbes',data);bpy.context.collection.objects.link(probe)
    fit_female_reference(probe,reference_vertex_count=n)
    inv=hi.matrix_world.inverted()
    for v,p in zip(hi.data.vertices,list(data.vertices)[n:n+len(hi_points)]):v.co=inv@p.co
    hi.data.update()
    start=n+len(hi_points);inv=rig.matrix_world.inverted()
    fitted={b.name:(inv@data.vertices[start+2*i].co,inv@data.vertices[start+2*i+1].co,b.matrix_local.col[2].to_3d().copy()) for i,b in enumerate(bones)}
    source.activate(rig);bpy.ops.object.mode_set(mode='EDIT')
    for b in rig.data.edit_bones:
        if b.name.lower()=='root':continue
        head,tail,z_axis=fitted[b.name]
        b.head=head;b.tail=tail;b.align_roll(z_axis)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    for o in (probe,cage,eyes):bpy.data.objects.remove(o,do_unlink=True)
