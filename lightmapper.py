import bpy

bl_info = {
    "name": "Lightmapper",
    "author": "flipdp",
    "version": (1, 0),
    "blender": (3, 40, 0),
    "location": "Properties > Render",
    "description": "Bake lightmaps",
    "warning": "",
    "wiki_url": "",
    "category": "Render",
}

image = None
selectedObj = None

def nodeSetup(mat, imageName, lmProps, y_offset, connectToOutput=False):
    mat.use_nodes = True
    ntree = mat.node_tree
    
    imageNode = None
    uvNode = None
    if imageName not in ntree.nodes:
        imageNode = ntree.nodes.new('ShaderNodeTexImage')
        uvNode = ntree.nodes.new('ShaderNodeUVMap')
    else:
        imageNode = ntree.nodes[imageName]
        uvNode = ntree.nodes[imageName + 'UV']
    
    global image
    imageNode.image = image 
    imageNode.location = (0, y_offset)
    imageNode.name = imageName
    imageNode.image.colorspace_settings.name = lmProps.clrSpace
    uvNode.uv_map = 'Lightmap'
    uvNode.location = (-250, y_offset)
    uvNode.name = imageName + 'UV'
    ntree.links.new(imageNode.inputs[0], uvNode.outputs[0])
    
    if connectToOutput:
        if 'Principled BSDF' in ntree.nodes:
            node_to_delete = ntree.nodes['Principled BSDF']
            if node_to_delete:
                ntree.nodes.remove( node_to_delete )
        ntree.links.new(ntree.nodes['Material Output'].inputs[0], imageNode.outputs[0])
        
    
    imageNode.select = True
    ntree.nodes.active = imageNode

def main(context):
    global selectedObj
    selectedObj = bpy.context.view_layer.objects.active
    new_uvmap_name = 'Lightmap'
    imageName = selectedObj.name + '_Bake'
    
    scene = context.scene
    lmProps = scene.lightmapperProps

    if lmProps.unwrapUV:
        smartUnwrap = False
        new_uv = None
        if new_uvmap_name not in selectedObj.data.uv_layers:
            new_uv = selectedObj.data.uv_layers.new(name=new_uvmap_name)
            smartUnwrap = True
        else:
            new_uv = selectedObj.data.uv_layers[new_uvmap_name]

        new_uv.active = True
        new_uv.active_render = True
        
        if smartUnwrap:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=1.22173, island_margin=0)
            bpy.ops.object.mode_set(mode='OBJECT')

    global image
    if imageName not in bpy.data.images:
        image = bpy.data.images.new(imageName, width=lmProps.renderRes, height=lmProps.renderRes)
    else:
        image = bpy.data.images[imageName]

    mats = selectedObj.data.materials
    if mats != None:
        for mat in mats:
            nodeSetup(mat, imageName, lmProps, 1000)

    if lmProps.renderDevice != 'Keep':
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.feature_set = 'SUPPORTED'
        bpy.context.scene.cycles.device = lmProps.renderDevice

    bpy.context.scene.cycles.samples = lmProps.numSamples
    bpy.context.scene.cycles.use_adaptive_sampling = lmProps.useDenoiser
    bpy.context.scene.cycles.adaptive_threshold = lmProps.adaptiveThresh
    bpy.context.scene.cycles.use_denoising = lmProps.useDenoiser
    bpy.context.scene.cycles.denoising_input_passes = lmProps.denoisingPass
    
    if lmProps.bakeType != 'Keep':
        bpy.context.scene.cycles.bake_type = lmProps.bakeType
        bpy.context.scene.render.bake.use_pass_direct = True
        bpy.context.scene.render.bake.use_pass_indirect = True
        bpy.context.scene.render.bake.use_pass_diffuse = True
        bpy.context.scene.render.bake.use_pass_glossy = True
        bpy.context.scene.render.bake.use_pass_transmission = True
        bpy.context.scene.render.bake.use_pass_emit = True

    if not lmProps.onlySetup:
        res = bpy.ops.object.bake('INVOKE_DEFAULT', save_mode='EXTERNAL')
        if res != {'RUNNING_MODAL'}:
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

def createBake(context):
    global selectedObj
    imageName = selectedObj.name + '_Bake'

    scene = context.scene
    lmProps = scene.lightmapperProps

    print('Creating new object')

    print(imageName)

    new_obj = selectedObj.copy()
    new_obj.name = selectedObj.name + '(BAKE)'
    new_obj.data = selectedObj.data.copy()
    new_obj.data.materials.clear()

    print(new_obj)
    
    mat_name = selectedObj.name+'Bake'
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)        
    new_obj.data.materials.append(mat)
    
    nodeSetup(mat, imageName, lmProps, 0, True)
    
    context.collection.objects.link(new_obj)
    
    
    selectedObj.hide_viewport = True
    selectedObj.hide_render = True
    
    new_obj.select_set(True)


class LightmapperProps(bpy.types.PropertyGroup):
    renderRes : bpy.props.IntProperty(
        name="Bake Resolution",
        description="Resolution of the lightmap",
        min = 256, max=4096,
        default = 512)
    
    bakeType : bpy.props.EnumProperty(
        name="Bake Type",
        description="Information to bake into lightmap",
        items = [
            ('COMBINED', 'Combined', ""),
            ('SHADOW', 'Shadow', ""),
            ('DIFFUSE', 'Diffuse', ""),
            ('ROUGHNESS', 'Roughness', ""),
            ('Keep', 'Keep', ""),
        ],
        default = 'Keep'
    )
    
    clrSpace : bpy.props.EnumProperty(
        name="Color Space",
        description="Color space of lightmap",
        items = [
            ('Filmic Log', 'Filmic Log', ""),
            ('Linear', 'Linear', ""),
            ('Linear ACES', 'Linear ACES', ""),
            ('Non-Color', 'Non-Color', ""),
            ('Raw', 'Raw', ""),
            ('sRGB', 'sRGB', ""),
            ('XYZ', 'XYZ', ""),
        ],
        default = 'sRGB'
        )
    
    numSamples : bpy.props.IntProperty(
        name="Sample Count",
        description="Number of samples",
        min = 1, soft_max=4096,
        default=64
    )
    
    renderDevice : bpy.props.EnumProperty(
        name="Render Device",
        description="Which device will be used for rendering",
        items = [
            ('GPU', 'GPU', ""),
            ('CPU', 'CPU', ""),
            ('Keep', 'Keep', ""),
        ],
        default = 'Keep'
        )
    
    useDenoiser : bpy.props.BoolProperty(
        name="Use Denoiser",
        description="Bake lightmap with denoiser",
        default=True
    )

    onlySetup : bpy.props.BoolProperty(
        name="Only Setup",
        description="Dont start bake. Only setup nodes",
        default=False
    )
    
    denoisingPass : bpy.props.EnumProperty(
        name="Denoising Pass",
        description="Pass of denoiser",
        items = [
            ('RGB_ALBEDO', 'Albedo', ""),
            ('RBG', 'None', ""),
            ('RGB_ALBEDO_NORMAL', 'Albedo and Normal', ""),
        ],
        default = 'RGB_ALBEDO_NORMAL'
    )
    
    adaptiveThresh : bpy.props.FloatProperty(
        name="Noise Threshold",
        description="Threshold for starting the denoiser",
        min=0.0, default=0.01
    )

    unwrapUV : bpy.props.BoolProperty(
        name="Unwrap lightmap UV",
        description="Create new UV map for lightmap and unwrap it",
        default=True
    )

class LightmapOperator(bpy.types.Operator):
    bl_idname = "object.lightmapper"
    bl_label = "Bake"

    _timer = None

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        res = main(context)
        if res != {'RUNNING_MODAL'}:
            return {'FINISHED'}
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        global image
        if event.type == 'TIMER':
            if image.is_dirty:
                self.finish(context)
                return {'FINISHED'}

        return {'PASS_THROUGH'}
    
    def finish(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        createBake(context)
        print('Bake done')


def menu_func(self, context):
    self.layout.operator(LightmapOperator.bl_idname, text=LightmapOperator.bl_label)


class LightmapperPanel(bpy.types.Panel):
    bl_label = "Lightmapper"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        lmProps = scene.lightmapperProps

        selectedObj = bpy.context.view_layer.objects.active
        if selectedObj != None:
            layout.label(text="Selected Object: " + selectedObj.name)
        else:
            layout.label(text="Select Object")
            return
        
        layout.prop(lmProps, 'renderRes')
        layout.prop(lmProps, 'bakeType')
        layout.prop(lmProps, 'onlySetup')
        layout.prop(lmProps, 'unwrapUV')
        layout.prop(lmProps, 'clrSpace')
        layout.prop(lmProps, 'numSamples')
        layout.prop(lmProps, 'renderDevice')
        layout.prop(lmProps, 'useDenoiser')
        if lmProps.useDenoiser:
            layout.prop(lmProps, 'denoisingPass')
            layout.prop(lmProps, 'adaptiveThresh')
        
        row = layout.row()
        row.scale_y = 3.0
        row.operator("object.lightmapper")

def register():
    bpy.utils.register_class(LightmapperPanel)

    bpy.utils.register_class(LightmapOperator)
    bpy.types.VIEW3D_MT_object.append(menu_func)
    
    bpy.utils.register_class(LightmapperProps)
    
    bpy.types.Scene.lightmapperProps = bpy.props.PointerProperty(type = LightmapperProps)

def unregister():
    bpy.utils.unregister_class(LightmapperPanel)
    
    bpy.utils.unregister_class(LightmapOperator)
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    
    bpy.utils.unregister_class(LightmapperProps)
    
    del bpy.types.Scene.lightmapperProps


if __name__ == "__main__":
    register()